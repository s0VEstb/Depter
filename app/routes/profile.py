"""GET /api/profile/{profile_id} — получение скорингового профиля."""
import json
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_async_session
from app.crud.profile import get_profile_by_id
from app.schemas.profile import ScoringProfileResponse

logger = logging.getLogger("depter")

router = APIRouter()


def _parse_json_field(value) -> dict:
    """Десериализуем JSON из Text-колонки."""
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return {}
    return {}


@router.get("/profile/{profile_id}", response_model=ScoringProfileResponse)
async def get_profile(
    profile_id: int,
    db: AsyncSession = Depends(get_async_session),
):
    """Получить полный скоринговый профиль по ID."""
    profile = await get_profile_by_id(db, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Профиль не найден")

    income_by_source = _parse_json_field(profile.income_by_source)
    income_by_category = _parse_json_field(profile.income_by_category)
    score_components = _parse_json_field(profile.score_components)
    ai_verdict = _parse_json_field(profile.ai_verdict)

    # Извлекаем список источников
    sources = list(income_by_source.keys()) if income_by_source else []

    # По бизнес-требованию отдаём средний доход в месяц напрямую из БД.
    avg_income_monthly = float(profile.avg_monthly_income_kgs or 0.0)
    avg_income_3m = avg_income_monthly
    avg_income_6m = avg_income_monthly

    return ScoringProfileResponse(
        profile_id=profile.id,
        user_id=profile.user_id,
        avg_income_monthly=avg_income_monthly,
        avg_income_3m=avg_income_3m,
        avg_income_6m=avg_income_6m,
        stability=profile.income_stability_score or 0.0,
        defter_score=profile.defter_score or 0,
        recommended_limit=profile.recommended_limit or 0.0,
        income_trend=profile.income_trend or 0.0,
        sources=sources,
        sources_count=profile.sources_count or 0,
        data_period_months=profile.data_period_months or 0,
        income_by_source=income_by_source,
        income_by_category=income_by_category,
        fraud_risk_score=profile.fraud_risk_score or 0,
        score_components=score_components,
        # Новые финансовые метрики
        total_income=profile.total_income,
        total_expense=profile.total_expense,
        avg_expense_monthly=profile.avg_expense_monthly,
        expense_to_income_ratio=profile.expense_to_income_ratio,
        net_cashflow_monthly=profile.net_cashflow_monthly,
        overdraft_count=profile.overdraft_count,
        max_overdraft_amount=profile.max_overdraft_amount,
        income_anomaly_detected=profile.income_anomaly_detected,
        ai_verdict=ai_verdict if ai_verdict else None,
        calculated_at=profile.calculated_at or datetime.utcnow(),
    )
