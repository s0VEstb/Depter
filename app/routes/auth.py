"""POST /api/auth/login — аутентификация по email + password."""
import hashlib
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.db.database import get_async_session
from app.crud.user import get_user_by_email
from app.schemas.user import UserOut

logger = logging.getLogger("depter")

router = APIRouter()


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/auth/login", response_model=UserOut)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_async_session)):
    """Аутентификация по email и паролю."""
    user = await get_user_by_email(db, data.email)
    if not user:
        raise HTTPException(status_code=401, detail="Неверный email или пароль")

    password_hash = hashlib.sha256(data.password.encode()).hexdigest()
    if not user.password_hash or user.password_hash != password_hash:
        raise HTTPException(status_code=401, detail="Неверный email или пароль")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Аккаунт деактивирован")

    return user
