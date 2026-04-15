"""POST /api/users — регистрация пользователя."""
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_async_session
from app.crud.user import create_user, get_user_by_phone
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
