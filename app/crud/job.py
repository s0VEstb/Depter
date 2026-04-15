import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import ProcessingJob
from app.models.enums import JobStatus

logger = logging.getLogger("depter")


async def create_job(db: AsyncSession, files_count: int, user_id: Optional[int] = None) -> ProcessingJob:
    """Создать новую задачу обработки."""
    job = ProcessingJob(
        files_count=files_count,
        user_id=user_id,
        status=JobStatus.PENDING,
        step="Ожидание обработки",
        progress=0,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    logger.info(f"Создана задача job_id={job.id}, files_count={files_count}")
    return job


async def get_job(db: AsyncSession, job_id: UUID) -> Optional[ProcessingJob]:
    """Получить задачу по UUID."""
    result = await db.execute(select(ProcessingJob).where(ProcessingJob.id == job_id))
    return result.scalar_one_or_none()


async def update_job_status(
    db: AsyncSession,
    job_id: UUID,
    status: JobStatus,
    step: Optional[str] = None,
    progress: Optional[int] = None,
    error_message: Optional[str] = None,
    result_profile_id: Optional[int] = None,
) -> None:
    """Обновить статус задачи."""
    values: dict = {"status": status, "updated_at": datetime.utcnow()}
    if step is not None:
        values["step"] = step
    if progress is not None:
        values["progress"] = progress
    if error_message is not None:
        values["error_message"] = error_message
    if result_profile_id is not None:
        values["result_profile_id"] = result_profile_id

    await db.execute(
        update(ProcessingJob).where(ProcessingJob.id == job_id).values(**values)
    )
    await db.commit()
    logger.info(f"Job {job_id}: status={status.value}, progress={progress}")
