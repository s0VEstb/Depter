from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class ParsedTransaction:
    source: str
    txn_date: datetime
    amount: float
    amount_kgs: float
    currency: str
    direction: str
    txn_type: str
    description: str
    category: Optional[str] = None
    recipient_phone: Optional[str] = None
    external_id: Optional[str] = None
    is_duplicate: bool = False


@dataclass
class ParsedStatement:
    """Результат парсинга одного PDF"""

    source: str
    client_name: str
    inn: Optional[str]
    account_number: Optional[str]
    period_start: Optional[datetime]
    period_end: Optional[datetime]
    opening_balance: float
    closing_balance: float
    total_income: float
    total_expense: float
    transactions: list[ParsedTransaction] = field(default_factory=list)
    parse_errors: list[str] = field(default_factory=list)
