import logging
from .mbank_parser import parse_mbank
from .demir_parser import parse_demir
from .simbank_parser import parse_simbank
from .parser_utils import detect_bank
from .types import ParsedStatement, ParsedTransaction

logger = logging.getLogger(__name__)


PARSERS = {
    "mbank":   parse_mbank,
    "demir":   parse_demir,
    "simbank": parse_simbank,
}

 
def parse_statement(pdf_bytes: bytes, hint_source: str | None = None) -> ParsedStatement:
    """
    Основная функция парсинга. Принимает байты PDF.
    hint_source — если фронтенд уже знает источник (из UI выбора банка).
    Возвращает ParsedStatement.
 
    Использование:
        with open("mbank.pdf", "rb") as f:
            result = parse_statement(f.read())
        for tx in result.transactions:
            print(tx.txn_date, tx.direction, tx.amount, tx.description)
    """
    source = hint_source or detect_bank(pdf_bytes)
 
    parser_fn = PARSERS.get(source)
    if parser_fn is None:
        logger.error(f"Нет парсера для источника: {source}")
        return ParsedStatement(
            source=source,
            client_name="", inn=None, account_number=None,
            period_start=None, period_end=None,
            opening_balance=0, closing_balance=0,
            total_income=0, total_expense=0,
            parse_errors=[f"Unsupported bank: {source}"]
        )
 
    try:
        result = parser_fn(pdf_bytes)
        logger.info(
            f"[{source.upper()}] Спарсено {len(result.transactions)} транзакций | "
            f"Клиент: {result.client_name}"
        )
        return result
    except Exception as e:
        logger.exception(f"Ошибка парсинга {source}: {e}")
        return ParsedStatement(
            source=source,
            client_name="", inn=None, account_number=None,
            period_start=None, period_end=None,
            opening_balance=0, closing_balance=0,
            total_income=0, total_expense=0,
            parse_errors=[str(e)]
        )
 
 
# ──────────────────────────────────────────────
# Дедупликация (cross-source)
# ──────────────────────────────────────────────
 
def deduplicate(statements: list[ParsedStatement]) -> list[ParsedTransaction]:
    """
    Объединяет транзакции из нескольких выписок.
    Помечает дубликаты: одна дата + одна сумма + одно направление
    встречается в 2+ источниках.
 
    Пример: mBank списание 80 KGS → DemirBank пополнение 80 KGS
    — это один и тот же перевод, виден с обеих сторон.
    """
    all_txns: list[ParsedTransaction] = []
    for stmt in statements:
        all_txns.extend(stmt.transactions)
 
    # Ключ: (дата_без_времени, сумма, направление)
    # Если встречается дважды с разных источников — дубль
    from collections import defaultdict
    seen: dict[tuple, list[int]] = defaultdict(list)
 
    for idx, tx in enumerate(all_txns):
        key = (tx.txn_date.date(), round(tx.amount, 2), tx.direction)
        seen[key].append(idx)
 
    for key, indices in seen.items():
        sources = {all_txns[i].source for i in indices}
        if len(sources) > 1:
            # Оставляем первый, остальные помечаем дублями
            for i in indices[1:]:
                all_txns[i].is_duplicate = True
 
    return all_txns
