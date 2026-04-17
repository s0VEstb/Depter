from datetime import datetime
from typing import Optional, List, Dict, Any

from pydantic import BaseModel


class ProfileOut(BaseModel):
    id: int
    user_id: Optional[int] = None
    sources_count: int
    data_period_months: int
    avg_monthly_income_kgs: float
    income_stability_score: float
    income_trend: float
    income_by_source: Optional[Dict[str, Any]] = None
    income_by_category: Optional[Dict[str, Any]] = None
    defter_score: Optional[int] = None
    recommended_limit: Optional[float] = None
    fraud_risk_score: Optional[int] = None
    score_components: Optional[Dict[str, Any]] = None
    total_income: Optional[float] = None
    total_expense: Optional[float] = None
    avg_expense_monthly: Optional[float] = None
    expense_to_income_ratio: Optional[float] = None
    net_cashflow_monthly: Optional[float] = None
    overdraft_count: Optional[int] = None
    max_overdraft_amount: Optional[float] = None
    income_anomaly_detected: Optional[bool] = None
    ai_verdict: Optional[Dict[str, Any]] = None
    calculated_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ScoringProfileResponse(BaseModel):
    """Полный скоринговый профиль для API-ответа."""
    profile_id: int
    user_id: Optional[int] = None
    avg_income_monthly: float
    avg_income_3m: float
    avg_income_6m: float
    stability: float
    defter_score: int
    recommended_limit: float
    income_trend: float
    sources: List[str]
    sources_count: int
    data_period_months: int
    income_by_source: Dict[str, Any]
    income_by_category: Dict[str, Any]
    fraud_risk_score: int
    score_components: Dict[str, Any]
    # Новые финансовые метрики
    total_income: Optional[float] = None
    total_expense: Optional[float] = None
    avg_expense_monthly: Optional[float] = None
    expense_to_income_ratio: Optional[float] = None
    net_cashflow_monthly: Optional[float] = None
    overdraft_count: Optional[int] = None
    max_overdraft_amount: Optional[float] = None
    income_anomaly_detected: Optional[bool] = None
    ai_verdict: Optional[Dict[str, Any]] = None
    calculated_at: datetime
