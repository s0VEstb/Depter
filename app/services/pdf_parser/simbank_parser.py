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


# ──────────────────────────────────────────────
# Парсер Simbank
# ──────────────────────────────────────────────
# Формат: таблица — Дата | Детали операции | Сумма | Плата за кредит | Баланс после
# Дата: "01-01-2026 17:22:56"
# Сумма: "+65,00" или "-64,00"
 
def parse_simbank(pdf_bytes: bytes) -> ParsedStatement:
    stmt = ParsedStatement(
        source="simbank",
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
        for page in pdf.pages:
            full_text += (page.extract_text() or "") + "\n"
            tables = page.extract_tables()
            all_tables.extend(tables)
 
    # Мета-данные
    name_match = re.search(r"Имя клиента:\s*(.+)", full_text)
    if name_match:
        stmt.client_name = name_match.group(1).strip()
 
    card_match = re.search(r"Номер карты клиента:\s*(\S+)", full_text)
    if card_match:
        stmt.account_number = card_match.group(1)
 
    period_match = re.search(
        r"Период:\s*(\d{2}-\d{2}-\d{4})\s*-\s*(\d{2}-\d{2}-\d{4})",
        full_text
    )
    if period_match:
        stmt.period_start = datetime.strptime(period_match.group(1), "%d-%m-%Y")
        stmt.period_end   = datetime.strptime(period_match.group(2), "%d-%m-%Y")
 
    opening_match = re.search(r"Остаток на начало периода:\s*([\d\s,]+)\s*KGS", full_text)
    closing_match = re.search(r"Остаток на конец периода:\s*([\d\s,]+)\s*KGS", full_text)
    income_match  = re.search(r"Сумма поступлений по карте:\s*([\d\s,]+)\s*KGS", full_text)
    expense_match = re.search(r"Сумма расходных операций по карте:\s*([\d\s,]+)\s*KGS", full_text)
 
    if opening_match: stmt.opening_balance = abs(_clean_amount(opening_match.group(1)))
    if closing_match: stmt.closing_balance = abs(_clean_amount(closing_match.group(1)))
    if income_match:  stmt.total_income    = abs(_clean_amount(income_match.group(1)))
    if expense_match: stmt.total_expense   = abs(_clean_amount(expense_match.group(1)))
 
    date_re = re.compile(r"(\d{2}-\d{2}-\d{4})\s+(\d{2}:\d{2}:\d{2})")
 
    for table in all_tables:
        if not table or len(table) < 2:
            continue
 
        header = [str(c or "").strip() for c in table[0]]
        col_date = col_detail = col_amount = -1
 
        for idx, h in enumerate(header):
            hl = h.lower()
            if "дата" in hl and col_date == -1:
                col_date = idx
            if "детал" in hl or "описани" in hl or "operation" in hl:
                col_detail = idx
            if "сумма" in hl and "баланс" not in hl and "плата" not in hl:
                col_amount = idx
 
        if col_date == -1 or col_amount == -1:
            continue
 
        for row in table[1:]:
            if not row or len(row) <= max(col_date, col_amount):
                continue
 
            date_cell   = str(row[col_date] or "").strip()
            amount_cell = str(row[col_amount] or "").strip()
            detail      = str(row[col_detail] or "") if col_detail != -1 else ""
 
            dm = date_re.search(date_cell)
            if not dm:
                continue
 
            try:
                txn_date = datetime.strptime(
                    f"{dm.group(1)} {dm.group(2)}", "%d-%m-%Y %H:%M:%S"
                )
            except ValueError:
                continue
 
            if not amount_cell or amount_cell in ("-", ""):
                continue
 
            raw_amount = _clean_amount(amount_cell)
            direction = "in" if raw_amount >= 0 else "out"
            description = detail.strip()
 
            txn_type = _classify_txn(description, direction, "simbank")
            category = _classify_category(description, txn_type)
 
            stmt.transactions.append(ParsedTransaction(
                source="simbank",
                txn_date=txn_date,
                amount=abs(raw_amount),
                amount_kgs=abs(raw_amount),
                currency="KGS",
                direction=direction,
                txn_type=txn_type,
                description=description[:250],
                category=category,
                recipient_phone=_parse_phone(description),
                external_id=None,
            ))
 
    stmt.transactions.sort(key=lambda t: t.txn_date)
    return stmt
