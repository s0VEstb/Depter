"""
Совместимый вход в актуальный PDF parser stack.
"""
from typing import Optional

from app.models.enums import SourceEnum

from .base import parse_statement
from .types import ParsedStatement, ParsedTransaction


def detect_bank(pdf_bytes: bytes) -> Optional[SourceEnum]:
    statement = parse_statement(pdf_bytes)
    if statement.parse_errors or not statement.source:
        return None

    try:
        return SourceEnum(statement.source)
    except ValueError:
        return None


def parse_pdf(pdf_bytes: bytes) -> tuple[Optional[SourceEnum], list[ParsedTransaction]]:
    statement = parse_statement(pdf_bytes)
    source = None
    if statement.source:
        try:
            source = SourceEnum(statement.source)
        except ValueError:
            source = None
    return source, statement.transactions


__all__ = [
    "ParsedStatement",
    "ParsedTransaction",
    "detect_bank",
    "parse_pdf",
    "parse_statement",
]
