from datetime import datetime
import re
import io
import logging

import pdfplumber

from app.services.pdf_parser.parser_utils import (
    _clean_amount,
    _classify_category,
    _classify_txn,
    _parse_phone,
    _parse_uuid,
)
from app.services.pdf_parser.types import ParsedStatement, ParsedTransaction

logger = logging.getLogger(__name__)

DEMIR_CONTINUATION_COLUMNS = {
    "col_date": 1,
    "col_type": 3,
    "col_payer": 4,
    "col_explain": 5,
    "col_amount": 6,
}


# ──────────────────────────────────────────────
# Парсер DemirBank
# ──────────────────────────────────────────────
# Формат: таблица — 
# № | ДАТА ПРОВЕДЕНИЯ | ДАТА ВАЛЮТ-ИЯ | ВИД ОПЕРАЦИИ | ПЛАТЕЛЬЩИК/ПОЛУЧАТЕЛЬ | ОБЪЯСНЕНИЕ | СУММА | БАЛАНС | ИНН
# Дата: "31-03-2026 10:38"
 
def parse_demir(pdf_bytes: bytes) -> ParsedStatement:
    stmt = ParsedStatement(
        source="demir",
        client_name="",
        inn=None,
        account_number=None,
        period_start=None,
        period_end=None,
        opening_balance=0.0,
        closing_balance=0.0,
        total_income=0.0,
        total_expense=0.0,
    )
 
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        full_text = ""
        all_tables = []
        first_page_text = ""
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            if not first_page_text:
                first_page_text = page_text
            full_text += page_text + "\n"
            tables = page.extract_tables()
            all_tables.extend(tables)

    # Мета-данные из текста
    inn_match = re.search(r"ИНН:\s+ИНТЕРВАЛ ДАТЫ:\s*\n(\d+)\s+(\d{2}-\d{2}-\d{4}\s*-\s*\d{2}-\d{2}-\d{4})", first_page_text)
    if inn_match:
        stmt.inn = inn_match.group(1)
        period_raw = inn_match.group(2)
        dm = re.search(r"(\d{2}-\d{2}-\d{4})\s*-\s*(\d{2}-\d{2}-\d{4})", period_raw)
        if dm:
            stmt.period_start = datetime.strptime(dm.group(1), "%d-%m-%Y")
            stmt.period_end = datetime.strptime(dm.group(2), "%d-%m-%Y")

    name_match = re.search(
        r"ИМЯ:\s+ДАТА СОЗДАНИЯ ДОКУМЕНТА:\s*\n(.+?)\s+\d{2}-\d{2}-\d{4}\s+\d{2}:\d{2}",
        first_page_text,
    )
    if name_match:
        stmt.client_name = name_match.group(1).strip()

    acc_match = re.search(
        r"ВНЕШНИЙ НОМЕР СЧЕТА:\s+ВСЕГО ЗАЧИСЛЕНО НА СЧЕТ:\s*\n(\d+)\s+([\d\s,.-]+)",
        first_page_text,
    )
    if acc_match:
        stmt.account_number = acc_match.group(1)
        stmt.total_income = abs(_clean_amount(acc_match.group(2)))

    opening_match = re.search(
        r"НОМЕР КЛИЕНТА:\s+ВХОДЯЩИЙ ОСТАТОК:\s*\n\d+\s+([\d\s,.-]+)",
        first_page_text,
    )
    closing_match = re.search(
        r"НОМЕР СЧЕТА:\s+ИСХОДЯЩИЙ ОСТАТОК:\s*\n\d+\s+([\d\s,.-]+)",
        first_page_text,
    )
    expense_match = re.search(
        r"КОД ВАЛЮТЫ:\s+ВСЕГО СНЯТО СО СЧЕТА:\s*\nKGS\s+(-?[\d\s,.-]+)",
        first_page_text,
    )

    if opening_match:
        stmt.opening_balance = abs(_clean_amount(opening_match.group(1)))
    if closing_match:
        stmt.closing_balance = abs(_clean_amount(closing_match.group(1)))
    if expense_match:
        stmt.total_expense = abs(_clean_amount(expense_match.group(1)))
 
    # Парсинг таблиц транзакций
    # Нужная таблица имеет заголовок с "ДАТА" и "СУММА"
    date_re = re.compile(r"(\d{2}-\d{2}-\d{4})\s+(\d{2}:\d{2})")
 
    for table in all_tables:
        if not table or len(table) < 2:
            continue
 
        # Определяем индексы колонок по заголовку
        header = [str(c or "").upper().replace("\n", " ").strip() for c in table[0]]
 
        # Ищем колонки по ключевым словам
        col_date = col_type = col_explain = col_amount = col_payer = -1
        for idx, h in enumerate(header):
            if "ДАТА ПРОВЕДЕНИЯ" in h or ("ДАТА" in h and col_date == -1):
                col_date = idx
            if "ВИД" in h and "ОПЕРАЦИИ" in h:
                col_type = idx
            if "ОБЪЯСНЕНИ" in h or "EXPLANATION" in h:
                col_explain = idx
            if "СУММА" in h or "AMOUNT" in h:
                col_amount = idx
            if "ПЛАТЕЛЬЩИК" in h or "ПОЛУЧАТЕЛ" in h:
                col_payer = idx
 
        row_start = 1
        if col_date == -1 or col_amount == -1:
            # На следующих страницах у Demir строки часто идут без заголовка.
            # Тогда используем зафиксированные индексы колонок.
            col_date = DEMIR_CONTINUATION_COLUMNS["col_date"]
            col_type = DEMIR_CONTINUATION_COLUMNS["col_type"]
            col_payer = DEMIR_CONTINUATION_COLUMNS["col_payer"]
            col_explain = DEMIR_CONTINUATION_COLUMNS["col_explain"]
            col_amount = DEMIR_CONTINUATION_COLUMNS["col_amount"]
            row_start = 0

        for row in table[row_start:]:
            if not row or len(row) <= max(col_date, col_amount):
                continue
 
            date_cell   = str(row[col_date] or "").strip()
            amount_cell = str(row[col_amount] or "").strip()
            explain     = str(row[col_explain] or "") if col_explain != -1 else ""
            op_type     = str(row[col_type] or "") if col_type != -1 else ""
            payer       = str(row[col_payer] or "") if col_payer != -1 else ""
 
            dm = date_re.search(date_cell)
            if not dm:
                continue
 
            try:
                txn_date = datetime.strptime(
                    f"{dm.group(1)} {dm.group(2)}", "%d-%m-%Y %H:%M"
                )
            except ValueError:
                continue
 
            if not amount_cell or amount_cell in ("-", ""):
                continue
 
            raw_amount = _clean_amount(amount_cell)
            direction = "in" if raw_amount >= 0 else "out"
            description = f"{op_type} | {explain} | {payer}".strip(" |")
 
            # Определяем валюту — DemirBank хранит EUR конвертации
            currency = "KGS"
            if "EUR" in description.upper():
                currency = "EUR"
            elif "USD" in description.upper():
                currency = "USD"
 
            txn_type = _classify_txn(description, direction, "demir")
            category = _classify_category(description, txn_type)
 
            stmt.transactions.append(ParsedTransaction(
                source="demir",
                txn_date=txn_date,
                amount=abs(raw_amount),
                amount_kgs=abs(raw_amount),  # конвертация при необходимости отдельно
                currency=currency,
                direction=direction,
                txn_type=txn_type,
                description=description[:250],
                category=category,
                recipient_phone=_parse_phone(description),
                external_id=_parse_uuid(description),
            ))
 
    # Сортируем по дате
    stmt.transactions.sort(key=lambda t: t.txn_date)
    return stmt
