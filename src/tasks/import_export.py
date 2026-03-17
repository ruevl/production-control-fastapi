import asyncio
import tempfile
from datetime import datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.celery_app import celery_app
from src.core.config import settings
from src.db.session import engine
from src.models.batch import Batch
from src.models.work_center import WorkCenter
from src.storage.minio_service import MinIOService


@celery_app.task(bind=True, max_retries=1)
def import_batches_from_file(
        self,
        file_url: str,
        user_id: int
):
    """
    Импорт партий из Excel/CSV файла.
    """
    try:
        # Download file from MinIO
        minio_service = MinIOService()
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp_file:
            minio_service.download_file(
                bucket=settings.minio_bucket_imports,
                object_name=file_url.split("/")[-1],
                file_path=tmp_file.name
            )

            # Process file
            total_rows = 0
            created = 0
            skipped = 0
            errors = []

            async def _import():
                nonlocal total_rows, created, skipped, errors

                async with AsyncSession(engine) as db:
                    import pandas as pd

                    df = pd.read_excel(tmp_file.name)
                    total_rows = len(df)

                    for idx, row in df.iterrows():
                        try:
                            # Check for duplicate
                            existing = await db.execute(
                                select(Batch).where(
                                    Batch.batch_number == row["НомерПартии"],
                                    Batch.batch_date == row["ДатаПартии"]
                                )
                            )
                            if existing.scalar_one_or_none():
                                errors.append({
                                    "row": idx + 2,
                                    "error": "Duplicate batch number and date"
                                })
                                skipped += 1
                                continue

                            # Get or create work center
                            wc_result = await db.execute(
                                select(WorkCenter).where(
                                    WorkCenter.identifier == row["ИдентификаторРЦ"]
                                )
                            )
                            work_center = wc_result.scalar_one_or_none()

                            if not work_center:
                                errors.append({
                                    "row": idx + 2,
                                    "error": f"Work center '{row['ИдентификаторРЦ']}' not found"
                                })
                                skipped += 1
                                continue

                            # Create batch
                            batch = Batch(
                                task_description=row["ПредставлениеЗаданияНаСмену"],
                                work_center_id=work_center.id,
                                shift=row["Смена"],
                                team=row["Бригада"],
                                batch_number=row["НомерПартии"],
                                batch_date=row["ДатаПартии"],
                                nomenclature=row["Номенклатура"],
                                ekn_code=row["КодЕКН"],
                                shift_start=row["ДатаВремяНачалаСмены"],
                                shift_end=row["ДатаВремяОкончанияСмены"],
                            )
                            db.add(batch)
                            created += 1

                            # Update progress
                            self.update_state(
                                state="PROGRESS",
                                meta={
                                    "current": idx + 1,
                                    "total": total_rows,
                                    "created": created,
                                    "skipped": skipped
                                }
                            )

                        except Exception as e:
                            errors.append({
                                "row": idx + 2,
                                "error": str(e)
                            })
                            skipped += 1

                    await db.commit()

            asyncio.run(_import())

            # Clean up
            Path(tmp_file.name).unlink()

            return {
                "success": True,
                "total_rows": total_rows,
                "created": created,
                "skipped": skipped,
                "errors": errors
            }

    except Exception as exc:
        self.retry(exc=exc, countdown=300)


@celery_app.task
def export_batches_to_file(
        filters: dict,
        format: str = "excel"
):
    """
    Экспорт списка партий в файл.
    """
    import pandas as pd
    from sqlalchemy.ext.asyncio import AsyncSession

    async def _export():
        async with AsyncSession(engine) as db:
            query = select(Batch)

            if "is_closed" in filters:
                query = query.where(Batch.is_closed == filters["is_closed"])
            if "date_from" in filters:
                query = query.where(Batch.batch_date >= filters["date_from"])
            if "date_to" in filters:
                query = query.where(Batch.batch_date <= filters["date_to"])

            result = await db.execute(query)
            batches = result.scalars().all()

            # Convert to DataFrame
            data = []
            for batch in batches:
                data.append({
                    "ID": batch.id,
                    "НомерПартии": batch.batch_number,
                    "ДатаПартии": str(batch.batch_date),
                    "Номенклатура": batch.nomenclature,
                    "РабочийЦентр": batch.work_center.name if batch.work_center else "",
                    "Смена": batch.shift,
                    "Бригада": batch.team,
                    "Статус": "Закрыта" if batch.is_closed else "Открыта",
                })

            df = pd.DataFrame(data)

            # Save to file
            with tempfile.NamedTemporaryFile(
                    suffix=f".{format}",
                    delete=False
            ) as tmp_file:
                if format == "excel":
                    df.to_excel(tmp_file.name, index=False)
                elif format == "csv":
                    df.to_csv(tmp_file.name, index=False)

                # Upload to MinIO
                minio_service = MinIOService()
                object_name = f"batches_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.{format}"
                file_url = minio_service.upload_file(
                    bucket=settings.minio_bucket_exports,
                    file_path=tmp_file.name,
                    object_name=object_name,
                    expires_days=7
                )

                Path(tmp_file.name).unlink()

                return {
                    "success": True,
                    "file_url": file_url,
                    "total_batches": len(batches)
                }

    return asyncio.run(_export())
