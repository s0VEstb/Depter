"""POST /api/users — регистрация пользователя."""
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_async_session
from app.crud.user import create_user, get_user_by_phone
from app.crud.profile import get_profiles_by_user
from app.schemas.user import UserCreate, UserOut

logger = logging.getLogger("depter")

router = APIRouter()


@router.post("/users", response_model=UserOut, status_code=201)
async def register_user(
    data: UserCreate,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Регистрация нового пользователя.
    Проверяет уникальность телефона.
    """
    existing = await get_user_by_phone(db, data.phone)
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Пользователь с телефоном {data.phone} уже зарегистрирован",
        )

    try:
        user = await create_user(db, data)
        logger.info(f"Зарегистрирован пользователь: {user.full_name} ({user.phone})")
        return user
    except Exception as e:
        logger.error(f"Ошибка регистрации: {e}")
        raise HTTPException(status_code=400, detail=f"Ошибка создания пользователя: {str(e)}")


@router.get("/users/{user_id}/profiles")
async def get_user_profiles(
    user_id: int,
    db: AsyncSession = Depends(get_async_session),
):
    """
    История скоринговых профилей пользователя.
    Возвращает список: profile_id, defter_score, recommended_limit, calculated_at.
    """
    profiles = await get_profiles_by_user(db, user_id)
    return [
        {
            "profile_id": p.id,
            "defter_score": p.defter_score or 0,
            "recommended_limit": p.recommended_limit or 0.0,
            "avg_monthly_income_kgs": p.avg_monthly_income_kgs or 0.0,
            "sources_count": p.sources_count or 0,
            "data_period_months": p.data_period_months or 0,
            "calculated_at": p.calculated_at.isoformat() if p.calculated_at else None,
        }
        for p in profiles
    ]
