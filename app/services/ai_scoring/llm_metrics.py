import json
import logging
import math
from collections import defaultdict
from datetime import datetime
from statistics import mean, pstdev
from typing import Any
from app.services.ai_scoring.ollama_client import ask as ollama_ask
from .math_metrics import (
    _month_key,
    _safe_float,
    _clamp,
    _normalize_transactions,
    _filter_active_transactions,
    _income_transactions,
    _monthly_income_map,
    calculate_fallback_metrics,
)

logger = logging.getLogger(__name__)


def _serialize_transactions_for_llm(transactions: list[Any], limit: int = 200) -> list[dict[str, Any]]:
    normalized = _filter_active_transactions(_normalize_transactions(transactions))

    compact: list[dict[str, Any]] = []
    for tx in normalized[-limit:]:
        compact.append(
            {
                "date": tx["txn_date"].isoformat(sep=" "),
                "source": tx["source"],
                "amount_kgs": tx["amount_kgs"],
                "direction": tx["direction"],
                "txn_type": tx["txn_type"],
                "category": tx["category"],
                "description": tx["description"][:120],
            }
        )

    return compact


def _build_llm_prompt(transactions: list[Any], fallback_metrics: dict[str, Any]) -> str:
    tx_payload = _serialize_transactions_for_llm(transactions)

    return f"""
Проанализируй финансовые транзакции клиента и верни только JSON без markdown и пояснений.

Формат ответа:
{{
  "avg_income_3m": number,
  "avg_income_6m": number,
  "stability": number,
  "income_trend": number,
  "defter_score": integer,
  "recommended_limit": number
}}

Правила:
- Все суммы в KGS
- stability от 0 до 1
- defter_score от 0 до 1000
- recommended_limit >= 0
- Не добавляй текст вне JSON

Fallback metrics:
{json.dumps(fallback_metrics, ensure_ascii=False)}

Transactions:
{json.dumps(tx_payload, ensure_ascii=False)}
""".strip()


def _extract_json_object(raw_text: str) -> dict[str, Any] | None:
    if not raw_text:
        return None

    raw_text = raw_text.strip()

    try:
        parsed = json.loads(raw_text)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        pass

    start = raw_text.find("{")
    end = raw_text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None

    try:
        parsed = json.loads(raw_text[start : end + 1])
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        return None


def _validate_llm_metrics(data: dict[str, Any]) -> dict[str, Any] | None:
    required = [
        "avg_income_3m",
        "avg_income_6m",
        "stability",
        "income_trend",
        "defter_score",
        "recommended_limit",
    ]
    if not all(key in data for key in required):
        return None

    validated = {
        "avg_income_3m": round(_safe_float(data["avg_income_3m"]), 2),
        "avg_income_6m": round(_safe_float(data["avg_income_6m"]), 2),
        "stability": round(_clamp(_safe_float(data["stability"]), 0.0, 1.0), 4),
        "income_trend": round(_safe_float(data["income_trend"]), 4),
        "defter_score": int(_clamp(_safe_float(data["defter_score"]), 0, 1000)),
        "recommended_limit": round(max(_safe_float(data["recommended_limit"]), 0.0), 2),
    }
    return validated


async def ask_llm_for_scoring(transactions: list[Any], fallback_metrics: dict[str, Any]) -> dict[str, Any] | None:
    prompt = _build_llm_prompt(transactions, fallback_metrics)

    response = await ollama_ask(
        model="gemma4:e4b",
        prompt=prompt,
        timeout=60,
    )
    if not response:
        return None

    raw_text = response.get("response", "")
    parsed = _extract_json_object(raw_text)
    if not parsed:
        logger.warning("Gemma returned no valid JSON")
        return None

    validated = _validate_llm_metrics(parsed)
    if not validated:
        logger.warning("Gemma JSON is missing required scoring fields")
        return None

    return validated


async def build_profile_metrics(transactions: list[Any]) -> dict[str, Any]:
    fallback_metrics = calculate_fallback_metrics(transactions)
    llm_metrics = await ask_llm_for_scoring(transactions, fallback_metrics)

    if not llm_metrics:
        return fallback_metrics

    merged = dict(fallback_metrics)
    merged.update(llm_metrics)
    merged["score_components"] = {
        **fallback_metrics.get("score_components", {}),
        "fallback": False,
        "llm_used": True,
    }
    return merged
