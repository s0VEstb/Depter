import logging
import re
from datetime import date
from io import BytesIO
from typing import List

import pdfplumber

from .base import PDFParserBase, RawTransaction

logger = logging.getLogger("depter")

DATE_PATTERN = re.compile(r"(\d{2})[./](\d{2})[./](\d{2,4})")
AMOUNT_PATTERN = re.compile(r"([\d\s]+[.,]\d{2})")


class ODengiParser(PDFParserBase):
    """Парсер PDF-выписок O!Dengi."""

    def can_parse(self, text: str) -> bool:
        """Проверяет наличие маркеров O!Dengi в тексте."""
        text_lower = text.lower()
        return any(marker in text_lower for marker in ["o!dengi", "о!деньги", "odengi", "о!денги"])

    def parse(self, pdf_bytes: bytes) -> List[RawTransaction]:
        """Парсит O!Dengi PDF."""
        transactions = []

        try:
            with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
                for page in pdf.pages:
                    table = page.extract_table()
                    if table:
                        transactions.extend(self._parse_table(table))
                    else:
                        text = page.extract_text()
                        if text:
                            transactions.extend(self._parse_text_lines(text))

            logger.info(f"O!Dengi парсер: найдено {len(transactions)} транзакций")
        except Exception as e:
            logger.error(f"Ошибка парсинга O!Dengi PDF: {e}")
            raise

        return transactions

    def _parse_table(self, table: list) -> List[RawTransaction]:
        """Парсинг табличных данных O!Dengi."""
        results = []
        if not table or len(table) < 2:
            return results

        for row in table[1:]:
            if not row or len(row) < 3:
                continue

            try:
                date_str = str(row[0]).strip() if row[0] else ""
                txn_date = self._parse_date(date_str)
                if not txn_date:
                    continue

                description = str(row[1]).strip() if len(row) > 1 and row[1] else ""
                amount_str = str(row[2]).strip() if len(row) > 2 and row[2] else ""
                amount = self._parse_amount(amount_str)
                if not amount or amount <= 0:
                    continue

                direction = "credit"
                desc_lower = description.lower()
                if any(kw in desc_lower for kw in ["оплата", "списание", "расход", "перевод на", "вывод"]):
                    direction = "debit"

                txn_type = self._detect_txn_type(description)

                results.append(RawTransaction(
                    txn_date=txn_date,
                    amount=amount,
                    currency="KGS",
                    direction=direction,
                    description=description,
                    txn_type=txn_type,
                ))
            except Exception as e:
                logger.debug(f"O!Dengi: пропуск строки: {e}")
                continue

        return results

    def _parse_text_lines(self, text: str) -> List[RawTransaction]:
        """Парсинг текстовых данных O!Dengi."""
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

            remaining = line[date_match.end():]
            amount_match = AMOUNT_PATTERN.search(remaining)
            if not amount_match:
                continue

            amount = self._parse_amount(amount_match.group(0))
            if not amount or amount <= 0:
                continue

            description = remaining.strip()
            direction = "credit" if any(
                kw in description.lower() for kw in ["приход", "зачисл", "поступ", "получен"]
            ) else "debit"

            results.append(RawTransaction(
                txn_date=txn_date,
                amount=amount,
                currency="KGS",
                direction=direction,
                description=description,
                txn_type=self._detect_txn_type(description),
            ))

        return results

    @staticmethod
    def _parse_date(date_str: str) -> date:
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
        if not amount_str:
            return 0.0
        cleaned = re.sub(r"\s+", "", amount_str.strip())
        cleaned = cleaned.replace(",", ".")
        cleaned = re.sub(r"[^\d.]", "", cleaned)
        try:
            return float(cleaned)
        except ValueError:
            return 0.0

    @staticmethod
    def _detect_txn_type(description: str) -> str:
        desc_lower = description.lower()
        if any(kw in desc_lower for kw in ["qr"]):
            return "qr_payment"
        if any(kw in desc_lower for kw in ["pos", "карта", "card"]):
            return "card_payment"
        if any(kw in desc_lower for kw in ["налог", "гнс", "соцфонд"]):
            return "tax"
        if any(kw in desc_lower for kw in ["комис", "fee"]):
            return "fee"
        if any(kw in desc_lower for kw in ["кредит", "займ", "погашен"]):
            return "loan_repayment"
        if any(kw in desc_lower for kw in ["наличн", "cash", "снятие"]):
            return "cash"
        if any(kw in desc_lower for kw in ["перевод", "transfer", "p2p"]):
            return "transfer_out"
        return "other"
