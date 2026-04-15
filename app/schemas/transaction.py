from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


class TransactionOut(BaseModel):
    id: int
    source: str
    txn_date: datetime
    amount: float
    currency: str
    amount_kgs: float
    direction: str
    txn_type: str
    category: Optional[str] = None
    description: Optional[str] = None
    is_duplicate: bool = False

    model_config = {"from_attributes": True}
