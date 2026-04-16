from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum as SAEnum
from sqlalchemy.orm import relationship

from app.db.base import Base
from .enums import OccupationEnum


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(100), nullable=False)
    email = Column(String(50), unique=True, index=True, nullable=False)
    phone = Column(String(20), unique=True, index=True, nullable=False)
    inn = Column(String(14), unique=True, index=True, nullable=False)
    passport_id = Column(String(9), unique=True, index=True, nullable=False)
    birth_date = Column(DateTime, nullable=False)
    city = Column(String(50), nullable=False)
    business_type = Column(String(50), nullable=False)
    occupation = Column(SAEnum(OccupationEnum), nullable=False)
    consent_given_at = Column(DateTime, nullable=False)
    consent_version = Column(String(20), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    transactions = relationship("Transaction", back_populates="user")
    profile = relationship("Profile", uselist=False, back_populates="user")
    fraud_flags = relationship("FraudFlag", back_populates="user")
