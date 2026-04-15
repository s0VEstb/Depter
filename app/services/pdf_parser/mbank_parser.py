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

MBANK_TABLE_HEADER_LINES = {
    "Дата операции",
    "Описание операции",
    "Сумма операции",
    "Дата операции Описание операции Сумма операции",
}


# ──────────────────────────────────────────────
# Парсер mBank
# ──────────────────────────────────────────────
# Формат: таблица 3 колонки — "Дата операции" | "Описание операции" | "Сумма операции"
# Дата: "01.01.2026 13:27"
# Сумма: "- 89,00" или "+ 1 000,00"
# Заголовок: "Выписка по счету №..."
def parse_mbank(pdf_bytes: bytes) -> ParsedStatement:
    stmt = ParsedStatement(
        source="mbank",
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
 
    date_pattern = re.compile(r"(\d{2}\.\d{2}\.\d{4})\s+(\d{2}:\d{2})")
    amount_pattern = re.compile(r"^([+\-])\s*([\d\s,]+)$")
 
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        full_text = ""
        for page in pdf.pages:
            full_text += (page.extract_text() or "") + "\n"
 
        # Мета-данные из шапки
        acc_match = re.search(r"Выписка по счету\s*№(\S+)", full_text)
        if acc_match:
            stmt.account_number = acc_match.group(1)
 
        period_match = re.search(
            r"За период с\s+(\d{2}\.\d{2}\.\d{4})\s+по\s+(\d{2}\.\d{2}\.\d{4})",
            full_text
        )
        if period_match:
            stmt.period_start = datetime.strptime(period_match.group(1), "%d.%m.%Y")
            stmt.period_end   = datetime.strptime(period_match.group(2), "%d.%m.%Y")
 
        client_match = re.search(
            r"Клиент\s+Баланс.+?\n([А-ЯЁA-Z][А-ЯЁA-Zа-яёa-z\s]+)\n",
            full_text
        )
        if client_match:
            stmt.client_name = client_match.group(1).strip()
 
        # Баланс
        balance_match = re.search(
            r"([\d\s]+,\d{2})\s+KGS\s+([\d\s]+,\d{2})\s+KGS",
            full_text
        )
        if balance_match:
            stmt.opening_balance = _clean_amount(balance_match.group(1))
            stmt.closing_balance = _clean_amount(balance_match.group(2))
 
        total_match = re.search(
            r"Всего списаний\s+([\d\s]+,\d{2})\s+KGS.*?Всего пополнений\s+([\d\s]+,\d{2})\s+KGS",
            full_text, re.DOTALL
        )
        if total_match:
            stmt.total_expense = abs(_clean_amount(total_match.group(1)))
            stmt.total_income  = abs(_clean_amount(total_match.group(2)))
 
        # Транзакции — парсим построчно
        # Строки с датой начинают новую транзакцию
        lines = full_text.split("\n")
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            dm = date_pattern.match(line)
            if not dm:
                i += 1
                continue
 
            # Дата + время
            try:
                txn_date = datetime.strptime(
                    f"{dm.group(1)} {dm.group(2)}", "%d.%m.%Y %H:%M"
                )
            except ValueError:
                i += 1
                continue
 
            # Остаток строки после даты — начало описания
            rest = line[dm.end():].strip()
 
            # Собираем описание до следующей даты или строки с суммой
            desc_lines = [rest] if rest else []
            i += 1
            amount_str = None
 
            while i < len(lines):
                nxt = lines[i].strip()
                # Строка суммы — только знак и цифры
                am = re.match(r"^([+\-])\s*([\d\s]+,\d{2})$", nxt)
                if am:
                    amount_str = nxt
                    i += 1
                    break
                # Следующая транзакция
                if date_pattern.match(nxt):
                    break
                if nxt in MBANK_TABLE_HEADER_LINES:
                    i += 1
                    continue
                if nxt:
                    desc_lines.append(nxt)
                i += 1
 
            if amount_str is None:
                # Сумма может быть в конце строки описания
                for dl in reversed(desc_lines):
                    am2 = re.search(r"([+\-])\s*([\d\s]+,\d{2})$", dl)
                    if am2:
                        amount_str = am2.group(0)
                        break
 
            if not amount_str:
                continue
 
            raw_amount = _clean_amount(amount_str)
            direction = "in" if raw_amount >= 0 else "out"
            description = " ".join(desc_lines).strip()
 
            txn_type = _classify_txn(description, direction, "mbank")
            category = _classify_category(description, txn_type)
 
            stmt.transactions.append(ParsedTransaction(
                source="mbank",
                txn_date=txn_date,
                amount=abs(raw_amount),
                amount_kgs=abs(raw_amount),
                currency="KGS",
                direction=direction,
                txn_type=txn_type,
                description=description,
                category=category,
                recipient_phone=_parse_phone(description),
                external_id=_parse_uuid(description),
            ))
 
    return stmt
