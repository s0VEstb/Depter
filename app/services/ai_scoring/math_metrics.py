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

    result = {
        "avg_income_3m": avg_income_3m,
        "avg_income_6m": avg_income_6m,
        "stability": stability,
        "income_trend": trend,
        "defter_score": defter_score,
        "recommended_limit": recommended_limit,
        "sources_count": sources_count,
        "data_period_months": data_period_months,
        "income_by_source": _income_by_source(active_transactions),
        "income_by_category": _income_by_category(active_transactions),
        "score_components": {
            "fallback": True,
            "monthly_income": monthly_income,
        },
    }

    return result