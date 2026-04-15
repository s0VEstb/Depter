"""POST /api/upload — загрузка PDF-выписок и запуск обработки."""
import logging
from typing import List, Optional

from fastapi import APIRouter, File, Form, UploadFile, BackgroundTasks, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_async_session
from app.crud.job import create_job
from app.crud.user import get_user_by_phone
from app.schemas.job import UploadResponse
from app.utils.validators import validate_upload_files
from app.services.pipeline import run_pipeline

logger = logging.getLogger("depter")

router = APIRouter()


@router.post("/upload", response_model=UploadResponse, status_code=202)
async def upload_files(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(..., description="PDF-файлы банковских выписок (1-3 штуки)"),
    phone: Optional[str] = Form(None, description="Телефон для привязки к пользователю"),
    name: Optional[str] = Form(None, description="Имя пользователя (опционально)"),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Загрузка PDF-выписок для скоринга.
    
    - Принимает 1-3 PDF файла (до 20 MB каждый)
    - Создаёт задачу обработки
    - Запускает фоновую обработку (парсинг → агрегация → скоринг)
    - Немедленно возвращает job_id для отслеживания прогресса
    """
    # Валидация файлов
    is_valid, error_msg, files_bytes = await validate_upload_files(files)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)

    # Определяем user_id, если передан телефон
    user_id = None
    if phone:
        user = await get_user_by_phone(db, phone)
        if user:
            user_id = user.id

    # Создаём задачу обработки
    job = await create_job(db, files_count=len(files_bytes), user_id=user_id)

    # Запускаем фоновую обработку
    background_tasks.add_task(run_pipeline, job.id, files_bytes, phone)

    logger.info(f"Upload: job_id={job.id}, files={len(files_bytes)}, phone={phone}")

    return UploadResponse(
        job_id=str(job.id),
        status="pending",
        message="Files accepted, processing started",
    )
