from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional


@dataclass
class RawTransaction:
    """Распознанная транзакция из PDF."""
    txn_date: date
    amount: float
    currency: str          # "KGS", "USD", ...
    direction: str         # "credit" или "debit"
    description: str
    txn_type: str          # значение из TXNType enum
    category: Optional[str] = None
    is_duplicate: bool = False


class PDFParserBase(ABC):
    """Абстрактный класс для парсеров банковских PDF-выписок."""

    @abstractmethod
    def can_parse(self, text: str) -> bool:
        """Проверяет, подходит ли парсер для данного PDF (по заголовкам/маркерам)."""
        pass

    @abstractmethod
    def parse(self, pdf_bytes: bytes) -> List[RawTransaction]:
        """Парсит PDF и возвращает список транзакций."""
        pass

    def _extract_text(self, pdf_bytes: bytes) -> str:
        """Извлечь весь текст из PDF через pdfplumber."""
        import pdfplumber
        from io import BytesIO

        text_parts = []
        with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        return "\n".join(text_parts)

    def _extract_first_page_text(self, pdf_bytes: bytes) -> str:
        """Извлечь текст с первой страницы (для определения банка)."""
        import pdfplumber
        from io import BytesIO

        with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
            if pdf.pages:
                text = pdf.pages[0].extract_text()
                return text[:500] if text else ""
        return ""
