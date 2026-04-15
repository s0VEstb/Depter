"""Валидация загружаемых PDF-файлов."""
import logging
from typing import List, Tuple

from fastapi import UploadFile

from config import settings

logger = logging.getLogger("depter")

# Магические байты PDF
PDF_MAGIC = b"%PDF"

# Допустимые MIME-типы
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/x-pdf",
}


async def validate_upload_files(files: List[UploadFile]) -> Tuple[bool, str, List[bytes]]:
    """
    Валидация загружаемых PDF-файлов.
    
    Проверяет:
    - Количество файлов (1-MAX_FILES_PER_UPLOAD)
    - Размер каждого файла (max MAX_UPLOAD_SIZE_MB)
    - MIME-тип (application/pdf)
    - Магические байты (%PDF)
    
    Возвращает: (is_valid, error_message, files_bytes)
    """
    max_files = settings.MAX_FILES_PER_UPLOAD
    max_size = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024  # в байтах

    # Проверка количества
    if not files or len(files) == 0:
        return False, "Необходимо загрузить хотя бы один PDF файл", []

    if len(files) > max_files:
        return False, f"Максимум {max_files} файлов за раз", []

    files_bytes = []

    for i, file in enumerate(files):
        # Проверка MIME-типа
        if file.content_type and file.content_type not in ALLOWED_MIME_TYPES:
            return False, f"Файл {file.filename}: неверный формат ({file.content_type}). Только PDF.", []

        # Читаем содержимое
        content = await file.read()

        # Проверка размера
        if len(content) > max_size:
            size_mb = len(content) / (1024 * 1024)
            return False, f"Файл {file.filename}: размер {size_mb:.1f} MB превышает лимит {settings.MAX_UPLOAD_SIZE_MB} MB", []

        # Проверка пустоты
        if len(content) == 0:
            return False, f"Файл {file.filename} пустой", []

        # Проверка магических байтов PDF
        if not content[:4].startswith(PDF_MAGIC):
            return False, f"Файл {file.filename}: не является валидным PDF", []

        files_bytes.append(content)
        logger.info(f"Файл {i + 1}/{len(files)}: {file.filename}, {len(content)} bytes — OK")

    return True, "", files_bytes
