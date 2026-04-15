"""
Скоринг Depter: расчёт defter_score (0-1000) на основе доходов, стабильности, тренда и фрод-флагов.
"""
import logging
import math
from dataclasses import dataclass
from typing import Dict, List

from app.services.ai_aggregator import AggregationResult
from app.models.enums import FraudSeverity

logger = logging.getLogger("depter")


@dataclass
class ScoringResult:
    defter_score: int            # 0-1000
    recommended_limit: float     # рекомендуемый кредитный лимит
    score_components: Dict[str, int]  # разбивка по компонентам
    fraud_risk_score: int        # 0-100


def calculate_defter_score(
    result: AggregationResult,
    fraud_flags: List[dict],
    sources_count: int = 1,
) -> ScoringResult:
    """
    Формула скоринга Depter (0-1000 баллов):
    
    - income_score (0-400): логарифмическая шкала от avg_income_6m
    - stability_score (0-300): stability_coefficient * 300
    - trend_score (0-150): бонус за рост дохода
    - source_bonus (0-100): +50 за каждый доп. источник (max 2)
    - fraud_penalty (0 до -100): штраф за каждый фрод-флаг
    """
    # 1. Income score (0-400) — логарифмическая шкала
    income = result.avg_income_6m
    if income <= 0:
        income_score = 0
    elif income < 30_000:
        # 0 → 100 линейно
        income_score = int((income / 30_000) * 100)
    elif income < 80_000:
        # 100 → 250 линейно
        income_score = 100 + int(((income - 30_000) / 50_000) * 150)
    elif income < 150_000:
        # 250 → 350 линейно
        income_score = 250 + int(((income - 80_000) / 70_000) * 100)
    else:
        # 350 → 400, логарифмическое замедление
        bonus = min(50, int(math.log10(max(1, income / 150_000)) * 100))
        income_score = 350 + bonus

    income_score = min(400, income_score)

    # 2. Stability score (0-300)
    stability_score = int(result.stability_coefficient * 300)
    stability_score = max(0, min(300, stability_score))

    # 3. Trend score (0-150)
    trend = result.income_trend
    if trend > 0.1:
        trend_score = 150
    elif trend >= 0:
        # Линейно от 75 до 150
        trend_score = 75 + int((trend / 0.1) * 75)
    else:
        # Снижение: от 75 до 0
        trend_score = max(0, 75 + int((trend / 0.3) * 75))

    trend_score = max(0, min(150, trend_score))

    # 4. Source bonus (0-100)
    source_bonus = min(100, max(0, (sources_count - 1) * 50))

    # 5. Fraud penalty (0 до -100)
    fraud_penalty = 0
    severity_weights = {
        FraudSeverity.LOW.value: -10,
        FraudSeverity.MEDIUM.value: -25,
        FraudSeverity.HIGH.value: -50,
        "low": -10,
        "medium": -25,
        "high": -50,
    }
    for flag in fraud_flags:
        severity = flag.get("severity", "low")
        if isinstance(severity, FraudSeverity):
            severity = severity.value
        fraud_penalty += severity_weights.get(severity, -10)

    fraud_penalty = max(-100, fraud_penalty)

    # Итоговый балл
    raw_score = income_score + stability_score + trend_score + source_bonus + fraud_penalty
    defter_score = max(0, min(1000, raw_score))

    # Рекомендуемый лимит: avg_income_6m * 3
    recommended_limit = round(result.avg_income_6m * 3, 2)

    # Fraud risk score (0-100): обратная шкала от штрафа
    fraud_risk_score = min(100, abs(fraud_penalty))

    components = {
        "income_score": income_score,
        "stability_score": stability_score,
        "trend_score": trend_score,
        "source_bonus": source_bonus,
        "fraud_penalty": fraud_penalty,
    }

    logger.info(
        f"Скоринг: defter_score={defter_score}, recommended_limit={recommended_limit:,.0f}, "
        f"components={components}"
    )

    return ScoringResult(
        defter_score=defter_score,
        recommended_limit=recommended_limit,
        score_components=components,
        fraud_risk_score=fraud_risk_score,
    )
