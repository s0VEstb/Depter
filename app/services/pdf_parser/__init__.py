"""
Фабрика парсеров PDF-выписок.
Автоматически определяет банк-источник и подбирает нужный парсер.
"""
import logging
from typing import List, Optional

from app.models.enums import SourceEnum
from .base import PDFParserBase, RawTransaction
from .mbank import MBankParser
from .elsom import ElsomParser
from .odengi import ODengiParser

logger = logging.getLogger("depter")

# Реестр парсеров (порядок важен — первый подходящий побеждает)
PARSERS: List[tuple] = [
    (SourceEnum.MBANK, MBankParser()),
    (SourceEnum.ELSOM, ElsomParser()),
    (SourceEnum.ODENGI, ODengiParser()),
]


def _get_first_page_text(pdf_bytes: bytes) -> str:
    """Извлечь текст первой страницы PDF для определения банка."""
    try:
        import pdfplumber
        from io import BytesIO
        with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
            if pdf.pages:
                text = pdf.pages[0].extract_text()
                return text[:1000] if text else ""
    except Exception as e:
        logger.warning(f"Не удалось прочитать PDF для определения банка: {e}")
    return ""


def detect_bank(pdf_bytes: bytes) -> Optional[SourceEnum]:
    """Определить банк-источник по содержимому PDF."""
    text = _get_first_page_text(pdf_bytes)
    if not text:
        return None

    for source, parser in PARSERS:
        if parser.can_parse(text):
            logger.info(f"Определён источник: {source.value}")
            return source

    logger.warning("Не удалось определить банк-источник PDF")
    return None


def get_parser(pdf_bytes: bytes) -> Optional[PDFParserBase]:
    """Автоматически подобрать парсер по содержимому PDF."""
    text = _get_first_page_text(pdf_bytes)
    if not text:
        return None

    for source, parser in PARSERS:
        if parser.can_parse(text):
            logger.info(f"Выбран парсер: {source.value}")
            return parser

    logger.warning("Не найден подходящий парсер для PDF")
    return None


def parse_pdf(pdf_bytes: bytes) -> tuple:
    """
    Парсит PDF — возвращает (source: SourceEnum, transactions: List[RawTransaction]).
    Если источник не определён, возвращает (None, []).
    """
    source = detect_bank(pdf_bytes)
    parser = get_parser(pdf_bytes)

    if not parser or not source:
        logger.error("Не удалось распознать PDF. Источник неизвестен.")
        return None, []

    transactions = parser.parse(pdf_bytes)
    return source, transactions
