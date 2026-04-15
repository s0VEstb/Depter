from typing import Optional

from pydantic import BaseModel

from app.models.enums import JobStatus


class JobStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    step: Optional[str] = None
    progress: int = 0
    error: Optional[str] = None
    profile_id: Optional[int] = None


class UploadResponse(BaseModel):
    job_id: str
    status: str
    message: str
