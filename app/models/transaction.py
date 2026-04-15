from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship

from app.db.base import Base
from .enums import SourceEnum, CurrencyEnum, TXNType


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    source = Column(SAEnum(SourceEnum), nullable=False)
    txn_date = Column(DateTime, nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(SAEnum(CurrencyEnum), nullable=False)
    amount_kgs = Column(Float, nullable=False)
    direction = Column(String(10), nullable=False)
    txn_type = Column(SAEnum(TXNType), nullable=False)
    category = Column(String(50), nullable=True)
    description = Column(String(255), nullable=True)
    is_duplicate = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="transactions")