import logging
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import Transaction

logger = logging.getLogger("depter")


async def bulk_insert_transactions(db: AsyncSession, transactions: List[dict]) -> List[Transaction]:
    """Массовая вставка транзакций в БД."""
    objs = [Transaction(**t) for t in transactions]
    db.add_all(objs)
    await db.commit()
    for obj in objs:
        await db.refresh(obj)
    logger.info(f"Сохранено {len(objs)} транзакций")
    return objs


async def get_transactions_by_user(db: AsyncSession, user_id: int) -> List[Transaction]:
    """Получить все транзакции пользователя."""
    result = await db.execute(
        select(Transaction).where(Transaction.user_id == user_id).order_by(Transaction.txn_date.desc())
    )
    return list(result.scalars().all())


async def get_transactions_by_profile_user(db: AsyncSession, user_id: int, limit: int = 500) -> List[Transaction]:
    """Получить транзакции пользователя с лимитом."""
    result = await db.execute(
        select(Transaction)
        .where(Transaction.user_id == user_id)
        .order_by(Transaction.txn_date.desc())
        .limit(limit)
    )
    return list(result.scalars().all())
