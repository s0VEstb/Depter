import logging
import re
from datetime import datetime, date
from io import BytesIO
from typing import List

import pdfplumber

from .base import PDFParserBase, RawTransaction

logger = logging.getLogger("depter")

# Паттерны для mBank
DATE_PATTERN = re.compile(r"(\d{2})[./](\d{2})[./](\d{2,4})")
AMOUNT_PATTERN = re.compile(r"([\d\s]+[.,]\d{2})")

# Ключевые слова для определения типа транзакции
TRANSFER_KEYWORDS = ["перевод", "transfer", "p2p", "пополнение"]
QR_KEYWORDS = ["qr", "элсом", "elsom", "мбанк"]
CARD_KEYWORDS = ["pos", "карта", "card", "банкомат", "atm"]
TAX_KEYWORDS = ["налог", "tax", "гнс", "соцфонд"]
FEE_KEYWORDS = ["комис", "fee", "обслуж"]
LOAN_KEYWORDS = ["кредит", "займ", "loan", "погашен"]
CASH_KEYWORDS = ["наличн", "cash", "снятие", "внесение"]


class MBankParser(PDFParserBase):
    """Парсер PDF-выписок mBank Кыргызстан."""

    def can_parse(self, text: str) -> bool:
        """Проверяет наличие маркеров mBank в тексте."""
        text_lower = text.lower()
        return any(marker in text_lower for marker in ["mbank", "мбанк", "м-банк", "m-bank"])

    def parse(self, pdf_bytes: bytes) -> List[RawTransaction]:
        """Парсит mBank PDF с табличной структурой."""
        transactions = []

        try:
            with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    # Попробовать извлечь таблицу
                    table = page.extract_table()
                    if table:
                        transactions.extend(self._parse_table(table))
                    else:
                        # Если таблицы нет, парсим текст построчно
                        text = page.extract_text()
                        if text:
                            transactions.extend(self._parse_text(text))

            logger.info(f"mBank парсер: найдено {len(transactions)} транзакций")
        except Exception as e:
            logger.error(f"Ошибка парсинга mBank PDF: {e}")
            raise

        return transactions

    def _parse_table(self, table: list) -> List[RawTransaction]:
        """Парсинг табличных данных из PDF."""
        results = []
        if not table or len(table) < 2:
            return results

        # Определяем индексы колонок по заголовку
        header = [str(cell).lower().strip() if cell else "" for cell in table[0]]
        date_col = self._find_column(header, ["дата", "date"])
        desc_col = self._find_column(header, ["описание", "назначение", "description", "операция"])
        credit_col = self._find_column(header, ["приход", "зачисление", "credit", "поступление"])
        debit_col = self._find_column(header, ["расход", "списание", "debit", "сумма"])

        # Если не нашли колонки, пробуем по позиции
        if date_col is None:
            date_col = 0
        if desc_col is None:
            desc_col = min(1, len(header) - 1)

        for row in table[1:]:
            if not row or len(row) < 2:
                continue

            try:
                txn = self._parse_row(row, date_col, desc_col, credit_col, debit_col)
                if txn:
                    results.append(txn)
            except Exception as e:
                logger.debug(f"Пропуск строки таблицы: {e}")
                continue

        return results

    def _parse_row(self, row: list, date_col: int, desc_col: int,
                   credit_col: int = None, debit_col: int = None) -> RawTransaction:
        """Парсинг одной строки таблицы."""
        date_str = str(row[date_col]).strip() if row[date_col] else ""
        txn_date = self._parse_date(date_str)
        if not txn_date:
            return None

        description = str(row[desc_col]).strip() if desc_col is not None and row[desc_col] else ""

        # Определяем сумму и направление
        amount = 0.0
        direction = "debit"

        if credit_col is not None and row[credit_col]:
            credit_amount = self._parse_amount(str(row[credit_col]))
            if credit_amount and credit_amount > 0:
                amount = credit_amount
                direction = "credit"

        if amount == 0.0 and debit_col is not None and row[debit_col]:
            debit_amount = self._parse_amount(str(row[debit_col]))
            if debit_amount and debit_amount > 0:
                amount = debit_amount
                direction = "debit"

        # Если нет разделения на колонки, ищем сумму в описании
        if amount == 0.0:
            for cell in row:
                if cell:
                    parsed = self._parse_amount(str(cell))
                    if parsed and parsed > 0:
                        amount = parsed
                        break

        if amount == 0.0:
            return None

        txn_type = self._detect_txn_type(description)

        return RawTransaction(
            txn_date=txn_date,
            amount=amount,
            currency="KGS",
            direction=direction,
            description=description,
            txn_type=txn_type,
        )

    def _parse_text(self, text: str) -> List[RawTransaction]:
        """Парсинг текстовых данных (fallback если нет таблицы)."""
        results = []
        lines = text.split("\n")

        for line in lines:
            line = line.strip()
            if not line:
                continue

            date_match = DATE_PATTERN.search(line)
            if not date_match:
                continue

            txn_date = self._parse_date(date_match.group(0))
            if not txn_date:
                continue

            # Ищем сумму в строке (после даты)
            remaining = line[date_match.end():]
            amount_match = AMOUNT_PATTERN.search(remaining)
            if not amount_match:
                continue

            amount = self._parse_amount(amount_match.group(0))
            if not amount or amount <= 0:
                continue

            description = remaining.strip()
            # Определяем направление по ключевым словам
            direction = "credit" if any(kw in description.lower() for kw in ["приход", "зачисл", "поступ"]) else "debit"
            txn_type = self._detect_txn_type(description)

            results.append(RawTransaction(
                txn_date=txn_date,
                amount=amount,
                currency="KGS",
                direction=direction,
                description=description,
                txn_type=txn_type,
            ))

        return results

    @staticmethod
    def _find_column(header: list, keywords: list) -> int:
        """Найти индекс колонки по ключевым словам."""
        for i, cell in enumerate(header):
            for kw in keywords:
                if kw in cell:
                    return i
        return None

    @staticmethod
    def _parse_date(date_str: str) -> date:
        """Парсинг даты в формате DD.MM.YYYY или DD.MM.YY."""
        match = DATE_PATTERN.search(date_str)
        if not match:
            return None

        day, month, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
        if year < 100:
            year += 2000

        try:
            return date(year, month, day)
        except ValueError:
            return None

    @staticmethod
    def _parse_amount(amount_str: str) -> float:
        """Парсинг суммы: '1 234,56' -> 1234.56"""
        if not amount_str:
            return 0.0
        cleaned = amount_str.strip()
        cleaned = re.sub(r"\s+", "", cleaned)  # убрать пробелы-разделители тысяч
        cleaned = cleaned.replace(",", ".")     # запятая -> точка
        cleaned = re.sub(r"[^\d.]", "", cleaned)  # убрать всё кроме цифр и точки
        try:
            return float(cleaned)
        except ValueError:
            return 0.0

    @staticmethod
    def _detect_txn_type(description: str) -> str:
        """Определить тип транзакции по описанию."""
        desc_lower = description.lower()

        if any(kw in desc_lower for kw in QR_KEYWORDS):
            return "qr_payment"
        if any(kw in desc_lower for kw in CARD_KEYWORDS):
            return "card_payment"
        if any(kw in desc_lower for kw in TAX_KEYWORDS):
            return "tax"
        if any(kw in desc_lower for kw in FEE_KEYWORDS):
            return "fee"
        if any(kw in desc_lower for kw in LOAN_KEYWORDS):
            return "loan_repayment"
        if any(kw in desc_lower for kw in CASH_KEYWORDS):
            return "cash"
        if any(kw in desc_lower for kw in TRANSFER_KEYWORDS):
            # Определяем направление перевода
            if any(w in desc_lower for w in ["входящ", "получ", "от"]):
                return "transfer_in"
            return "transfer_out"

        return "other"
