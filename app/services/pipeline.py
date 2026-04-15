"""
Pipeline-оркестратор: полный процесс обработки PDF -> скоринг.
Запускается как BackgroundTask в FastAPI.
"""
import json
import logging
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.job import update_job_status, get_job
from app.crud.transaction import bulk_insert_transactions
from app.crud.profile import create_profile
from app.crud.user import get_user_by_phone
from app.models.enums import JobStatus, SourceEnum, CurrencyEnum, TXNType
from app.services.pdf_parser import parse_pdf, detect_bank
from app.services.deduplication import deduplicate_transactions
from app.services.ai_aggregator import AIAggregator
from app.services.scoring import calculate_defter_score
from app.db.database import AsyncSessionLocal

logger = logging.getLogger("depter")


async def run_pipeline(
    job_id: UUID,
    files: List[bytes],
    phone: Optional[str] = None,
) -> None:
    """
    Полный флоу обработки. Вызывается как BackgroundTask.
    Создаёт собственную DB-сессию, т.к. работает вне HTTP-запроса.
    """
    async with AsyncSessionLocal() as db:
        try:
            # === Шаг 1: Начало парсинга ===
            await update_job_status(db, job_id, JobStatus.PARSING, step="Определение банков...", progress=5)

            # === Шаг 2: Определение банка и парсинг каждого PDF ===
            all_transactions = []
            sources = set()

            for i, pdf_bytes in enumerate(files):
                await update_job_status(
                    db, job_id, JobStatus.PARSING,
                    step=f"Парсинг PDF файла {i + 1}/{len(files)}...",
                    progress=10 + int(20 * (i / len(files))),
                )

                source, transactions = parse_pdf(pdf_bytes)
                if source:
                    sources.add(source)
                if transactions:
                    # Привязываем источник к каждой транзакции
                    for txn in transactions:
                        txn._source = source  # временное поле для сохранения в БД
                    all_transactions.extend(transactions)

                logger.info(f"PDF {i + 1}: source={source}, транзакций={len(transactions)}")

            if not all_transactions:
                await update_job_status(
                    db, job_id, JobStatus.FAILED,
                    step="Ошибка",
                    error_message="Не удалось извлечь транзакции из загруженных PDF",
                    progress=30,
                )
                return

            # === Шаг 3: Дедупликация ===
            await update_job_status(db, job_id, JobStatus.PARSING, step="Дедупликация транзакций...", progress=35)
            all_transactions = deduplicate_transactions(all_transactions)

            # === Шаг 4: Определяем user_id ===
            user_id = None
            if phone:
                user = await get_user_by_phone(db, phone)
                if user:
                    user_id = user.id

            # === Шаг 5: Сохраняем транзакции в БД ===
            await update_job_status(db, job_id, JobStatus.PARSING, step="Сохранение транзакций...", progress=40)

            txn_dicts = []
            for txn in all_transactions:
                source_val = getattr(txn, '_source', None)
                # Определяем enum-значение для source
                source_enum = source_val if source_val else SourceEnum.MBANK

                # Безопасное определение txn_type
                try:
                    txn_type_enum = TXNType(txn.txn_type)
                except ValueError:
                    txn_type_enum = TXNType.OTHER

                # Безопасное определение currency
                try:
                    currency_enum = CurrencyEnum(txn.currency)
                except ValueError:
                    currency_enum = CurrencyEnum.KGS

                txn_dicts.append({
                    "user_id": user_id or 1,  # fallback для MVP (без регистрации)
                    "source": source_enum,
                    "txn_date": datetime.combine(txn.txn_date, datetime.min.time()),
                    "amount": txn.amount,
                    "currency": currency_enum,
                    "amount_kgs": txn.amount,  # упрощённо: считаем что всё в KGS
                    "direction": txn.direction,
                    "txn_type": txn_type_enum,
                    "category": txn.category,
                    "description": txn.description[:255] if txn.description else None,
                    "is_duplicate": txn.is_duplicate,
                })

            if txn_dicts:
                await bulk_insert_transactions(db, txn_dicts)

            # === Шаг 6: AI-агрегация ===
            await update_job_status(
                db, job_id, JobStatus.AGGREGATING,
                step="AI-агрегация дохода...",
                progress=45,
            )

            aggregator = AIAggregator()
            agg_result = await aggregator.aggregate(all_transactions)

            await update_job_status(db, job_id, JobStatus.AGGREGATING, step="Агрегация завершена", progress=70)

            # === Шаг 7: Скоринг ===
            await update_job_status(
                db, job_id, JobStatus.SCORING,
                step="Расчёт скорингового балла...",
                progress=75,
            )

            # В MVP фрод-флагов нет, передаём пустой список
            fraud_flags = []
            scoring = calculate_defter_score(agg_result, fraud_flags, sources_count=len(sources))

            await update_job_status(db, job_id, JobStatus.SCORING, step="Скоринг завершён", progress=85)

            # === Шаг 8: Создание профиля ===
            await update_job_status(db, job_id, JobStatus.SCORING, step="Сохранение профиля...", progress=90)

            # Определяем период данных (количество месяцев)
            data_period = len(agg_result.income_by_month) if agg_result.income_by_month else 1

            profile_data = {
                "user_id": user_id or 1,
                "sources_count": len(sources),
                "data_period_months": data_period,
                "avg_monthly_income_kgs": agg_result.avg_income_6m,
                "income_stability_score": agg_result.stability_coefficient,
                "income_trend": agg_result.income_trend,
                "income_by_source": {s.value: 0 for s in sources},  # упрощённо
                "income_by_category": agg_result.income_by_category,
                "defter_score": scoring.defter_score,
                "recommended_limit": scoring.recommended_limit,
                "fraud_risk_score": scoring.fraud_risk_score,
                "score_components": scoring.score_components,
                "calculated_at": datetime.utcnow(),
            }

            # Заполняем income_by_source реальными данными
            if agg_result.income_by_month:
                total_income = sum(agg_result.income_by_month.values())
                for source in sources:
                    # Делим пропорционально количеству транзакций от источника
                    source_txns = [t for t in all_transactions
                                   if getattr(t, '_source', None) == source and t.direction == "credit"]
                    source_income = sum(t.amount for t in source_txns)
                    profile_data["income_by_source"][source.value] = round(source_income, 2)

            profile = await create_profile(db, profile_data)

            # === Шаг 9: Завершение ===
            await update_job_status(
                db, job_id, JobStatus.DONE,
                step="Готово",
                progress=100,
                result_profile_id=profile.id,
            )

            logger.info(
                f"Pipeline завершён: job_id={job_id}, profile_id={profile.id}, "
                f"defter_score={scoring.defter_score}"
            )

        except Exception as e:
            logger.error(f"Pipeline ошибка для job_id={job_id}: {e}", exc_info=True)
            try:
                await update_job_status(
                    db, job_id, JobStatus.FAILED,
                    step="Ошибка",
                    error_message=str(e),
                    progress=0,
                )
            except Exception as update_err:
                logger.error(f"Не удалось обновить статус job при ошибке: {update_err}")
