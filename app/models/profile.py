from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship

from app.db.base import Base


class Profile(Base):
    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    sources_count = Column(Integer, nullable=False)
    data_period_months = Column(Integer, nullable=False)
    avg_monthly_income_kgs = Column(Float, nullable=False)
    income_stability_score = Column(Float, nullable=False)  # 0-1
    income_trend = Column(Float, nullable=False)  # e.g., 0.05 for 5% growth
    income_by_source = Column(Text, nullable=True)
    income_by_category = Column(Text, nullable=True)
    defter_score = Column(Integer, nullable=True)  # 0-1000
    recommended_limit = Column(Float, nullable=True)
    fraud_risk_score = Column(Integer, nullable=True)  # 0-100
    score_components = Column(Text, nullable=True)  # JSON breakdown

    # ── Новые финансовые метрики ──
    total_income = Column(Float, nullable=True)
    total_expense = Column(Float, nullable=True)
    avg_expense_monthly = Column(Float, nullable=True)
    expense_to_income_ratio = Column(Float, nullable=True)  # 0.0–2.0+
    net_cashflow_monthly = Column(Float, nullable=True)
    overdraft_count = Column(Integer, nullable=True, default=0)
    max_overdraft_amount = Column(Float, nullable=True, default=0.0)
    income_anomaly_detected = Column(Boolean, nullable=True, default=False)
    ai_verdict = Column(Text, nullable=True)  # JSON: {decision, risk_level, confidence, summary, risk_flags}

    calculated_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="profile")

