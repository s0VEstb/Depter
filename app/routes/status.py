"""GET /api/status/{job_id} — проверка статуса обработки."""
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_async_session
from app.crud.job import get_job
from app.schemas.job import JobStatusResponse

logger = logging.getLogger("depter")

router = APIRouter()


@router.get("/status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: UUID,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Получить текущий статус задачи обработки.
    Клиент должен поллить этот endpoint до status=done или status=failed.
    """
    job = await get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    return JobStatusResponse(
        job_id=str(job.id),
        status=job.status,
        step=job.step,
        progress=job.progress or 0,
        error=job.error_message,
        profile_id=job.result_profile_id,
    )
