import json
import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.profile import Profile

logger = logging.getLogger("depter")


async def create_profile(db: AsyncSession, data: dict) -> Profile:
    """Создать скоринговый профиль."""
    # JSON-поля сериализуем в строку для Text-колонок
    for json_field in ("income_by_source", "income_by_category", "score_components"):
        if json_field in data and isinstance(data[json_field], dict):
            data[json_field] = json.dumps(data[json_field], ensure_ascii=False)

    profile = Profile(**data)
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    logger.info(f"Создан профиль id={profile.id}, defter_score={profile.defter_score}")
    return profile


async def get_profile_by_id(db: AsyncSession, profile_id: int) -> Optional[Profile]:
    """Получить профиль по ID."""
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    return result.scalar_one_or_none()


async def get_profile_by_user(db: AsyncSession, user_id: int) -> Optional[Profile]:
    """Получить профиль пользователя (последний)."""
    result = await db.execute(
        select(Profile)
        .where(Profile.user_id == user_id)
        .order_by(Profile.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()
