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


def _safe_parse_with_source(source: str, pdf_bytes: bytes) -> ParsedStatement:
    """Безопасный вызов парсера с единообразной обработкой исключений."""
    parser_fn = PARSERS[source]
    try:
        result = parser_fn(pdf_bytes)
        # На случай если конкретный парсер не проставил source.
        result.source = result.source or source
        return result
    except Exception as e:
        logger.exception("Ошибка парсинга %s: %s", source, e)
        return ParsedStatement(
            source=source,
            client_name="",
            inn=None,
            account_number=None,
            period_start=None,
            period_end=None,
            opening_balance=0,
            closing_balance=0,
            total_income=0,
            total_expense=0,
            parse_errors=[str(e)],
        )


def _pick_best_parse_result(pdf_bytes: bytes, preferred_source: str | None = None) -> ParsedStatement:
    """
    Пробует парсеры и выбирает лучший результат по количеству транзакций.
    Это спасает кейсы, когда auto-detect банка промахнулся.
    """
    candidates: list[str] = []
    if preferred_source in PARSERS:
        candidates.append(preferred_source)
    candidates.extend([src for src in PARSERS if src != preferred_source])

    best: ParsedStatement | None = None
    for src in candidates:
        result = _safe_parse_with_source(src, pdf_bytes)

        # Если приоритетный парсер успешно достал транзакции — берём сразу.
        if src == preferred_source and result.transactions:
            return result

        if best is None:
            best = result
            continue

        if len(result.transactions) > len(best.transactions):
            best = result

    return best if best is not None else ParsedStatement(
        source=preferred_source or "other",
        client_name="",
        inn=None,
        account_number=None,
        period_start=None,
        period_end=None,
        opening_balance=0,
        closing_balance=0,
        total_income=0,
        total_expense=0,
        parse_errors=["Не удалось распарсить выписку ни одним доступным парсером"],
    )

 
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

    if source not in PARSERS:
        logger.warning("Источник '%s' не распознан точно. Пробуем все доступные парсеры.", source)
        result = _pick_best_parse_result(pdf_bytes)
    else:
        result = _pick_best_parse_result(pdf_bytes, preferred_source=source)

    logger.info(
        "[%s] Спарсено %s транзакций | Клиент: %s | Ошибки: %s",
        (result.source or source or "other").upper(),
        len(result.transactions),
        result.client_name,
        len(result.parse_errors),
    )
    return result
 
 
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
