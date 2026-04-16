from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class UserCreate(BaseModel):
    full_name: str = Field(..., max_length=100)
    phone: str = Field(..., max_length=20)
    email: str = Field(..., max_length=50)
    inn: str = Field(..., max_length=14)
    passport_id: str = Field(..., max_length=9)
    birth_date: datetime
    city: str = Field(..., max_length=50)
    business_type: str = Field(..., max_length=50)
    occupation: str  # значение из OccupationEnum
    consent_given_at: datetime
    consent_version: str = Field(..., max_length=20)

    @field_validator("birth_date", "consent_given_at", mode="after")
    @classmethod
    def normalize_to_naive_utc(cls, value: datetime) -> datetime:
        """Приводим aware datetime к UTC и убираем tzinfo для TIMESTAMP WITHOUT TIME ZONE."""
        if value.tzinfo is None:
            return value
        return value.astimezone(timezone.utc).replace(tzinfo=None)


class UserOut(BaseModel):
    id: int
    full_name: str
    phone: str
    email: str
    inn: str
    passport_id: str
    birth_date: datetime
    city: str
    business_type: str
    occupation: str
    consent_given_at: datetime
    consent_version: str
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
