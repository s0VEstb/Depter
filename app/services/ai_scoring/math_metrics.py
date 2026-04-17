import json
import logging
import math
from collections import defaultdict
from datetime import datetime
from statistics import mean, pstdev
from typing import Any
from app.services.ai_scoring.ollama_client import ask as ollama_ask

logger = logging.getLogger(__name__)

def _month_key(dt: datetime) -> str:
    return dt.strftime("%Y-%m")


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _clamp(value: float, min_value: float, max_value: float) -> float:
    return max(min_value, min(value, max_value))


def _normalize_transactions(transactions: list[Any]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []

    for tx in transactions:
        txn_date = getattr(tx, "txn_date", None)
        if txn_date is None:
            continue

        normalized.append(
            {
                "source": getattr(tx, "source", "unknown"),
                "txn_date": txn_date,
                "amount_kgs": _safe_float(getattr(tx, "amount_kgs", 0.0)),
                "direction": getattr(tx, "direction", ""),
                "txn_type": getattr(tx, "txn_type", ""),
                "category": getattr(tx, "category", "other") or "other",
                "description": getattr(tx, "description", "") or "",
                "is_duplicate": bool(getattr(tx, "is_duplicate", False)),
            }
        )

    normalized.sort(key=lambda item: item["txn_date"])
    return normalized


def _filter_active_transactions(transactions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [tx for tx in transactions if not tx["is_duplicate"]]


def _income_transactions(transactions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [tx for tx in transactions if tx["direction"] == "in" and tx["amount_kgs"] > 0]


def _expense_transactions(transactions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [tx for tx in transactions if tx["direction"] == "out" and tx["amount_kgs"] > 0]


def _total_income(transactions: list[dict[str, Any]]) -> float:
    return round(sum(tx["amount_kgs"] for tx in _income_transactions(transactions)), 2)


def _total_expense(transactions: list[dict[str, Any]]) -> float:
    return round(sum(tx["amount_kgs"] for tx in _expense_transactions(transactions)), 2)


def _monthly_expense_map(transactions: list[dict[str, Any]]) -> dict[str, float]:
    monthly: dict[str, float] = defaultdict(float)
    for tx in _expense_transactions(transactions):
        monthly[_month_key(tx["txn_date"])] += tx["amount_kgs"]
    return dict(sorted(monthly.items()))


def _overdraft_analysis(transactions: list[dict[str, Any]]) -> tuple[int, float]:
    """Simulate running balance to find overdraft count and max overdraft.
    Returns (overdraft_count, max_overdraft_amount).
    """
    balance = 0.0
    overdraft_count = 0
    max_overdraft = 0.0
    was_negative = False

    for tx in transactions:  # already sorted by date
        if tx["direction"] == "in":
            balance += tx["amount_kgs"]
        else:
            balance -= tx["amount_kgs"]

        if balance < 0:
            if not was_negative:
                overdraft_count += 1
                was_negative = True
            if balance < max_overdraft:
                max_overdraft = balance
        else:
            was_negative = False

    return overdraft_count, round(abs(max_overdraft), 2)


def _income_anomaly_detected(monthly_income: dict[str, float]) -> bool:
    """True if any month deviates >80% from the average."""
    values = list(monthly_income.values())
    if len(values) < 2:
        return False
    avg = mean(values)
    if avg <= 0:
        return False
    for v in values:
        if abs(v - avg) / avg > 0.8:
            return True
    return False


def _monthly_income_map(transactions: list[dict[str, Any]]) -> dict[str, float]:
    monthly: dict[str, float] = defaultdict(float)

    for tx in _income_transactions(transactions):
        monthly[_month_key(tx["txn_date"])] += tx["amount_kgs"]

    return dict(sorted(monthly.items()))


def _income_by_source(transactions: list[dict[str, Any]]) -> dict[str, float]:
    result: dict[str, float] = defaultdict(float)

    for tx in _income_transactions(transactions):
        result[tx["source"]] += tx["amount_kgs"]

    return dict(sorted(result.items()))


def _income_by_category(transactions: list[dict[str, Any]]) -> dict[str, float]:
    result: dict[str, float] = defaultdict(float)

    for tx in _income_transactions(transactions):
        result[tx["category"]] += tx["amount_kgs"]

    return dict(sorted(result.items()))


def _data_period_months(transactions: list[dict[str, Any]]) -> int:
    if not transactions:
        return 0

    first_dt = transactions[0]["txn_date"]
    last_dt = transactions[-1]["txn_date"]

    return (last_dt.year - first_dt.year) * 12 + (last_dt.month - first_dt.month) + 1


def _average_for_last_n_months(monthly_income: dict[str, float], months: int) -> float:
    if not monthly_income:
        return 0.0

    values = list(monthly_income.values())[-months:]
    if not values:
        return 0.0

    return round(sum(values) / len(values), 2)


def _income_stability(monthly_income: dict[str, float]) -> float:
    values = list(monthly_income.values())
    if not values:
        return 0.0

    if len(values) == 1:
        return 1.0

    avg = mean(values)
    if avg <= 0:
        return 0.0

    deviation = pstdev(values)
    stability = 1 - (deviation / avg)
    return round(_clamp(stability, 0.0, 1.0), 4)


def _income_trend(monthly_income: dict[str, float]) -> float:
    values = list(monthly_income.values())
    if len(values) < 2:
        return 0.0

    midpoint = len(values) // 2
    first_half = values[:midpoint]
    second_half = values[midpoint:]

    if not first_half or not second_half:
        return 0.0

    first_avg = mean(first_half)
    second_avg = mean(second_half)

    if first_avg <= 0:
        return 0.0

    trend = (second_avg - first_avg) / first_avg
    return round(trend, 4)


def _fallback_defter_score(
    avg_income_3m: float,
    stability: float,
    data_period_months: int,
    sources_count: int,
) -> int:
    income_score = min(avg_income_3m / 1000, 100) * 5
    stability_score = stability * 350
    history_score = min(data_period_months, 12) / 12 * 100
    source_score = min(sources_count, 3) / 3 * 50

    total = income_score + stability_score + history_score + source_score
    return int(round(_clamp(total, 0, 1000)))


def calculate_fallback_metrics(transactions: list[Any]) -> dict[str, Any]:
    normalized = _normalize_transactions(transactions)
    active_transactions = _filter_active_transactions(normalized)
    monthly_income = _monthly_income_map(active_transactions)

    avg_income_3m = _average_for_last_n_months(monthly_income, 3)
    avg_income_6m = _average_for_last_n_months(monthly_income, 6)
    stability = _income_stability(monthly_income)
    trend = _income_trend(monthly_income)

    sources = {tx["source"] for tx in active_transactions}
    sources_count = len(sources)
    data_period_months = _data_period_months(active_transactions)

    recommended_limit = round(avg_income_3m * 3, 2)
    defter_score = _fallback_defter_score(
        avg_income_3m=avg_income_3m,
        stability=stability,
        data_period_months=data_period_months,
        sources_count=sources_count,
    )

    # ── Расчёт расходов и овердрафтов (детерминированный) ──
    total_in = _total_income(active_transactions)
    total_out = _total_expense(active_transactions)
    months = max(data_period_months, 1)
    avg_exp_monthly = round(total_out / months, 2)
    ei_ratio = round(total_out / total_in, 3) if total_in > 0 else 0.0
    net_cf = round((total_in - total_out) / months, 2)
    od_count, od_max = _overdraft_analysis(active_transactions)
    anomaly = _income_anomaly_detected(monthly_income)

    # Подкомпоненты скоринга (для отображения на фронте)
    income_score = min(avg_income_3m / 1000, 100) * 5
    stability_score = round(stability * 350, 1)
    history_score = round(min(data_period_months, 12) / 12 * 100, 1)
    source_score = round(min(sources_count, 3) / 3 * 50, 1)
    trend_score = round(_clamp(trend * 100, -50, 50), 1)
    fraud_penalty = 0

    result = {
        "avg_income_3m": avg_income_3m,
        "avg_income_6m": avg_income_6m,
        "stability": stability,
        "income_trend": trend,
        "defter_score": defter_score,
        "recommended_limit": recommended_limit,
        "sources_count": sources_count,
        "data_period_months": data_period_months,
        "fraud_risk_score": fraud_penalty,
        "income_by_source": _income_by_source(active_transactions),
        "income_by_category": _income_by_category(active_transactions),
        # Точные финансовые метрики (math, не LLM)
        "total_income": total_in,
        "total_expense": total_out,
        "avg_expense_monthly": avg_exp_monthly,
        "expense_to_income_ratio": ei_ratio,
        "net_cashflow_monthly": net_cf,
        "overdraft_count": od_count,
        "max_overdraft_amount": od_max,
        "income_anomaly_detected": anomaly,
        "score_components": {
            "fallback": True,
            "monthly_income": monthly_income,
            "stability_score": stability_score,
            "trend_score": trend_score,
            "fraud_penalty": fraud_penalty,
            "income_score": round(income_score, 1),
            "history_score": history_score,
            "source_score": source_score,
        },
    }

    return result