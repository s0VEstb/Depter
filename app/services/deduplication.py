"""
Дедупликация транзакций из нескольких источников.
Транзакция считается дублем, если совпадают: дата + сумма + направление + описание (первые 20 символов).
"""
import logging
from typing import List

from app.services.pdf_parser.base import RawTransaction

logger = logging.getLogger("depter")


def deduplicate_transactions(transactions: List[RawTransaction]) -> List[RawTransaction]:
    """
    Базовая дедупликация транзакций.
    Возвращает список с уникальными транзакциями, дубли помечаются is_duplicate=True.
    """
    seen = set()
    result = []
    duplicates_count = 0

    for txn in transactions:
        # Ключ дедупликации: дата + сумма (округлённая) + направление + начало описания
        key = (
            txn.txn_date.isoformat(),
            round(txn.amount, 2),
            txn.direction,
            txn.description[:20].strip().lower() if txn.description else "",
        )

        if key in seen:
            # Помечаем как дубль, но всё равно добавляем в результат
            txn.is_duplicate = True
            duplicates_count += 1
        else:
            seen.add(key)

        result.append(txn)

    if duplicates_count > 0:
        logger.info(f"Дедупликация: найдено {duplicates_count} дублей из {len(transactions)} транзакций")
    else:
        logger.info(f"Дедупликация: дублей не найдено ({len(transactions)} транзакций)")

    return result
