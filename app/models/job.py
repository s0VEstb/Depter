import uuid
from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base
from .enums import JobStatus


class ProcessingJob(Base):
    __tablename__ = "processing_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # гость без регистрации
    status = Column(SAEnum(JobStatus), nullable=False, default=JobStatus.PENDING)
    step = Column(String(50), nullable=True)          # "parsing" | "ai_aggregation" | "scoring" | "done"
    progress = Column(Integer, nullable=False, default=0)  # 0-100
    error_message = Column(Text, nullable=True)
    files_count = Column(Integer, nullable=False, default=0)
    result_profile_id = Column(Integer, ForeignKey("profiles.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
