"""
Pipeline-оркестратор: загрузка PDF -> парсинг -> дедупликация -> AI scoring -> сохранение в БД.
"""
import hashlib
import logging
from typing import List, Optional
from uuid import UUID

from app.crud.job import update_job_status
from app.crud.profile import create_profile
from app.crud.transaction import bulk_insert_transactions
from app.crud.user import get_user_by_phone
from app.db.database import AsyncSessionLocal
from app.models.enums import CurrencyEnum, JobStatus, SourceEnum, TXNType
from app.services.ai_scoring.llm_metrics import build_profile_metrics
from app.services.pdf_parser.base import deduplicate, parse_statement

logger = logging.getLogger("depter")


def _to_source_enum(source: str) -> SourceEnum:
    try:
        return SourceEnum(source)
    except ValueError:
        return SourceEnum.MBANK


def _to_currency_enum(currency: str) -> CurrencyEnum:
    try:
        return CurrencyEnum(currency)
    except ValueError:
        return CurrencyEnum.KGS


def _to_txn_type_enum(txn_type: str) -> TXNType:
    try:
        return TXNType(txn_type)
    except ValueError:
        return TXNType.OTHER


def _avg_monthly_from_score_components(metrics: dict) -> float | None:
    """Вычисляет средний доход за месяц из score_components.monthly_income, если доступно."""
    score_components = metrics.get("score_components")
    if not isinstance(score_components, dict):
        return None

    monthly_income = score_components.get("monthly_income")
    if not isinstance(monthly_income, dict) or not monthly_income:
        return None

    values: list[float] = []
    for value in monthly_income.values():
        try:
            values.append(float(value))
        except (TypeError, ValueError):
            continue

    if not values:
        return None

    return round(sum(values) / len(values), 2)


def _build_profile_payload(user_id: int, metrics: dict) -> dict:
    avg_monthly_income = _avg_monthly_from_score_components(metrics)
    if avg_monthly_income is None:
        avg_monthly_income = float(metrics.get("avg_income_6m", 0.0))

    # В MVP лимит фиксируем как 3x среднего месячного дохода.
    recommended_limit = round(avg_monthly_income * 3, 2)

    return {
        "user_id": user_id,
        "sources_count": int(metrics.get("sources_count", 0)),
        "data_period_months": int(metrics.get("data_period_months", 0)),
        "avg_monthly_income_kgs": avg_monthly_income,
        "income_stability_score": float(metrics.get("stability", 0.0)),
        "income_trend": float(metrics.get("income_trend", 0.0)),
        "income_by_source": metrics.get("income_by_source", {}),
        "income_by_category": metrics.get("income_by_category", {}),
        "defter_score": int(metrics.get("defter_score", 0)),
        "recommended_limit": recommended_limit,
        "fraud_risk_score": int(metrics.get("fraud_risk_score", 0)),
        "score_components": metrics.get("score_components", {}),
        # Новые финансовые метрики
        "total_income": metrics.get("total_income"),
        "total_expense": metrics.get("total_expense"),
        "avg_expense_monthly": metrics.get("avg_expense_monthly"),
        "expense_to_income_ratio": metrics.get("expense_to_income_ratio"),
        "net_cashflow_monthly": metrics.get("net_cashflow_monthly"),
        "overdraft_count": metrics.get("overdraft_count"),
        "max_overdraft_amount": metrics.get("max_overdraft_amount"),
        "income_anomaly_detected": metrics.get("income_anomaly_detected"),
        "ai_verdict": metrics.get("ai_verdict"),
    }


async def run_pipeline(
    job_id: UUID,
    files: List[bytes],
    phone: Optional[str] = None,
) -> None:
    async with AsyncSessionLocal() as db:
        try:
            await update_job_status(db, job_id, JobStatus.PARSING, step="Парсинг PDF...", progress=5)

            if not phone:
                raise ValueError("phone is required for processing")

            user = await get_user_by_phone(db, phone)
            if not user:
                raise ValueError(f"User with phone {phone} not found")

            statements = []
            seen_file_hashes: set[str] = set()
            for i, pdf_bytes in enumerate(files):
                await update_job_status(
                    db,
                    job_id,
                    JobStatus.PARSING,
                    step=f"Парсинг PDF файла {i + 1}/{len(files)}...",
                    progress=10 + int(35 * ((i + 1) / len(files))),
                )

                file_hash = hashlib.sha256(pdf_bytes).hexdigest()
                if file_hash in seen_file_hashes:
                    logger.warning("Пропущен дубликат PDF (одинаковые байты), index=%s", i)
                    continue
                seen_file_hashes.add(file_hash)

                statement = parse_statement(pdf_bytes)
                if statement.parse_errors:
                    logger.warning("Ошибки парсинга %s: %s", statement.source, statement.parse_errors)
                if statement.transactions:
                    statements.append(statement)

            if not statements:
                await update_job_status(
                    db,
                    job_id,
                    JobStatus.FAILED,
                    step="Ошибка",
                    error_message="Не удалось извлечь транзакции из загруженных PDF",
                    progress=40,
                )
                return

            await update_job_status(db, job_id, JobStatus.PARSING, step="Дедупликация транзакций...", progress=50)
            all_transactions = deduplicate(statements)

            txn_dicts = []
            for tx in all_transactions:
                txn_dicts.append(
                    {
                        "user_id": user.id,
                        "source": _to_source_enum(tx.source),
                        "txn_date": tx.txn_date,
                        "amount": float(tx.amount),
                        "currency": _to_currency_enum(tx.currency),
                        "amount_kgs": float(tx.amount_kgs),
                        "direction": tx.direction,
                        "txn_type": _to_txn_type_enum(tx.txn_type),
                        "category": tx.category,
                        "description": tx.description[:255] if tx.description else None,
                        "is_duplicate": bool(tx.is_duplicate),
                        "recipient_phone": tx.recipient_phone,
                        "external_id": tx.external_id,
                    }
                )

            await update_job_status(db, job_id, JobStatus.PARSING, step="Сохранение транзакций...", progress=65)
            if txn_dicts:
                await bulk_insert_transactions(db, txn_dicts)

            await update_job_status(db, job_id, JobStatus.AGGREGATING, step="AI scoring...", progress=75)
            metrics = await build_profile_metrics(all_transactions)

            await update_job_status(db, job_id, JobStatus.SCORING, step="Сохранение профиля...", progress=90)
            profile = await create_profile(db, _build_profile_payload(user.id, metrics))

            await update_job_status(
                db,
                job_id,
                JobStatus.DONE,
                step="Готово",
                progress=100,
                result_profile_id=profile.id,
            )
            logger.info(
                "Pipeline done: job_id=%s profile_id=%s defter_score=%s",
                job_id,
                profile.id,
                metrics.get("defter_score"),
            )
        except Exception as e:
            logger.error("Pipeline error for job_id=%s: %s", job_id, e, exc_info=True)
            try:
                await update_job_status(
                    db,
                    job_id,
                    JobStatus.FAILED,
                    step="Ошибка",
                    error_message=str(e),
                    progress=0,
                )
            except Exception as update_err:
                logger.error("Не удалось обновить статус job при ошибке: %s", update_err)
