import asyncio
import json
import logging
import math
from collections import defaultdict
from datetime import datetime
from statistics import mean, pstdev
from typing import Any

from app.services.ai_scoring.llm_client import ask as llm_ask
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


def _serialize_transactions_for_llm(transactions: list[Any], limit: int = 80) -> list[dict[str, Any]]:
    """Compact transaction summary for LLM — only essential fields, capped."""
    normalized = _filter_active_transactions(_normalize_transactions(transactions))

    compact: list[dict[str, Any]] = []
    for tx in normalized[-limit:]:
        compact.append(
            {
                "d": tx["txn_date"].strftime("%Y-%m-%d"),
                "a": round(tx["amount_kgs"], 2),
                "dir": tx["direction"],
                "cat": tx["category"],
            }
        )

    return compact


def _build_llm_prompt(transactions: list[Any], fallback_metrics: dict[str, Any]) -> str:
    tx_payload = _serialize_transactions_for_llm(transactions)

    # Передаём уже посчитанные math-метрики в промпт для контекста
    return f"""Ты — финансовый аналитик. Оцени кредитоспособность клиента по данным ниже.
Верни ТОЛЬКО валидный JSON без пояснений, markdown и кавычек.

### ДАННЫЕ КЛИЕНТА (точные, посчитаны математически)
- avg_income_monthly: {fallback_metrics.get('avg_income_3m', 0):.2f} KGS
- stability: {fallback_metrics.get('stability', 0):.4f}
- income_trend: {fallback_metrics.get('income_trend', 0):.4f}
- total_income: {fallback_metrics.get('total_income', 0):.2f}
- total_expense: {fallback_metrics.get('total_expense', 0):.2f}
- expense_to_income_ratio: {fallback_metrics.get('expense_to_income_ratio', 0):.3f}
- net_cashflow_monthly: {fallback_metrics.get('net_cashflow_monthly', 0):.2f}
- overdraft_count: {fallback_metrics.get('overdraft_count', 0)}
- max_overdraft_amount: {fallback_metrics.get('max_overdraft_amount', 0):.2f}
- income_anomaly_detected: {fallback_metrics.get('income_anomaly_detected', False)}
- data_period_months: {fallback_metrics.get('data_period_months', 0)}
- sources_count: {fallback_metrics.get('sources_count', 0)}

### ТВОЯ ЗАДАЧА
1. Оцени defter_score (0-1000) на основе данных выше
2. Вынеси ai_verdict

### ПРАВИЛА для defter_score
- Базовый = 500
- stability > 0.7 → +100, < 0.3 → -150
- expense_to_income_ratio > 1.0 → -200, < 0.7 → +100
- overdraft_count > 3 → -100, = 0 → +50
- income_anomaly_detected=true → -50
- sources_count > 1 → +50
- Итого: clamp(0, 1000)

### ПРАВИЛА для ai_verdict
- decision: "ОДОБРЕНО" (score>=600, ratio<0.85) / "УСЛОВНОЕ_ОДОБРЕНИЕ" (score>=350) / "ОТКАЗ"
- risk_level: "НИЗКИЙ" / "СРЕДНИЙ" / "ВЫСОКИЙ"
- confidence: 0.0–1.0 (3 мес = max 0.75, 1 источник = -0.10)
- summary: 2–3 предложения на русском (доходы, расходы, риски)
- risk_flags: из списка ["Высокая волатильность дохода", "Расходы превышают доходы", "Повторяющиеся овердрафты", "Единственный источник дохода", "Недостаточно данных", "Аномальный всплеск дохода", "Низкий среднемесячный доход"]

### ФОРМАТ ОТВЕТА (строго JSON)
{{
  "defter_score": integer,
  "ai_verdict": {{
    "decision": string,
    "risk_level": string,
    "confidence": number,
    "summary": string,
    "risk_flags": [string]
  }}
}}

Последние транзакции (для контекста):
{json.dumps(tx_payload, ensure_ascii=False)}""".strip()


def _extract_json_object(raw_text: str) -> dict[str, Any] | None:
    if not raw_text:
        return None

    raw_text = raw_text.strip()

    # Remove markdown code block fences if present
    if raw_text.startswith("```"):
        lines = raw_text.split("\n")
        # Remove first line (```json or ```) and last line (```)
        lines = [l for l in lines if not l.strip().startswith("```")]
        raw_text = "\n".join(lines).strip()

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
    """Validate LLM output — now only requires defter_score and ai_verdict."""
    validated = {}

    # defter_score (optional — fallback will use math-based)
    if "defter_score" in data:
        validated["defter_score"] = int(_clamp(_safe_float(data["defter_score"]), 0, 1000))

    # ai_verdict (the main thing we want from LLM)
    if isinstance(data.get("ai_verdict"), dict):
        verdict = data["ai_verdict"]
        decision = str(verdict.get("decision", "УСЛОВНОЕ_ОДОБРЕНИЕ"))
        # Normalize decision values
        if decision not in ("ОДОБРЕНО", "УСЛОВНОЕ_ОДОБРЕНИЕ", "ОТКАЗ"):
            decision = "УСЛОВНОЕ_ОДОБРЕНИЕ"
        risk_level = str(verdict.get("risk_level", "СРЕДНИЙ"))
        if risk_level not in ("НИЗКИЙ", "СРЕДНИЙ", "ВЫСОКИЙ"):
            risk_level = "СРЕДНИЙ"

        validated["ai_verdict"] = {
            "decision": decision,
            "risk_level": risk_level,
            "confidence": round(_clamp(_safe_float(verdict.get("confidence", 0.5)), 0.0, 1.0), 2),
            "summary": str(verdict.get("summary", ""))[:500],
            "risk_flags": [str(f) for f in verdict.get("risk_flags", [])],
        }

    if not validated:
        return None

    return validated


async def ask_llm_for_scoring(transactions: list[Any], fallback_metrics: dict[str, Any]) -> dict[str, Any] | None:
    prompt = _build_llm_prompt(transactions, fallback_metrics)
    logger.info("LLM prompt length: %d chars", len(prompt))

    max_retries = 3
    for attempt in range(1, max_retries + 1):
        logger.info("LLM attempt %d/%d", attempt, max_retries)

        response = await llm_ask(
            prompt=prompt,
            timeout=180,
            options={"temperature": 0.3, "num_predict": 1024},
            response_format="json",
        )
        if not response:
            logger.warning("LLM attempt %d: no response (timeout/connection error)", attempt)
            if attempt < max_retries:
                await asyncio.sleep(2)
            continue

        raw_text = response.get("response", "")
        logger.info("LLM attempt %d: response %d chars", attempt, len(raw_text))

        parsed = _extract_json_object(raw_text)
        if not parsed:
            logger.warning("LLM attempt %d: no valid JSON. Raw: %.300s", attempt, raw_text)
            if attempt < max_retries:
                await asyncio.sleep(1)
            continue

        validated = _validate_llm_metrics(parsed)
        if not validated:
            logger.warning("LLM attempt %d: no usable fields. Parsed keys: %s", attempt, list(parsed.keys()))
            if attempt < max_retries:
                await asyncio.sleep(1)
            continue

        # Ensure ai_verdict exists — it's the most important field
        if "ai_verdict" not in validated:
            logger.warning("LLM attempt %d: no ai_verdict in response, retrying", attempt)
            if attempt < max_retries:
                await asyncio.sleep(1)
            continue

        logger.info("LLM scoring OK (attempt %d): defter_score=%s, verdict=%s",
                    attempt,
                    validated.get("defter_score", "N/A"),
                    validated.get("ai_verdict", {}).get("decision", "N/A"))
        return validated

    logger.error("LLM failed after %d attempts — using fallback", max_retries)
    return None


async def build_profile_metrics(transactions: list[Any]) -> dict[str, Any]:
    fallback_metrics = calculate_fallback_metrics(transactions)
    llm_metrics = await ask_llm_for_scoring(transactions, fallback_metrics)

    if not llm_metrics:
        return fallback_metrics

    merged = dict(fallback_metrics)

    # LLM может корректировать defter_score
    if "defter_score" in llm_metrics:
        merged["defter_score"] = llm_metrics["defter_score"]

    # ai_verdict — только от LLM
    if "ai_verdict" in llm_metrics:
        merged["ai_verdict"] = llm_metrics["ai_verdict"]

    # Финансовые метрики ВСЕГДА из fallback_metrics (math)

    merged["score_components"] = {
        **fallback_metrics.get("score_components", {}),
        "fallback": False,
        "llm_used": True,
    }

    return merged
