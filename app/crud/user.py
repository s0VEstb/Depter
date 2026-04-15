import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.enums import OccupationEnum
from app.schemas.user import UserCreate

logger = logging.getLogger("depter")


async def create_user(db: AsyncSession, data: UserCreate) -> User:
    """Создать нового пользователя."""
    user = User(
        full_name=data.full_name,
        phone=data.phone,
        email=data.email,
        inn=data.inn,
        passport_id=data.passport_id,
        birth_date=data.birth_date,
        city=data.city,
        business_type=data.business_type,
        occupation=OccupationEnum(data.occupation),
        consent_given_at=data.consent_given_at,
        consent_version=data.consent_version,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    logger.info(f"Создан пользователь id={user.id}, phone={user.phone}")
    return user


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    """Получить пользователя по ID."""
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_user_by_phone(db: AsyncSession, phone: str) -> Optional[User]:
    """Найти пользователя по номеру телефона."""
    result = await db.execute(select(User).where(User.phone == phone))
    return result.scalar_one_or_none()
