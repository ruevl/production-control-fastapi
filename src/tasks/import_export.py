import tempfile
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from src.celery_app import celery_app
from src.core.config import settings
from src.db.session import sync_engine
from src.models.batch import Batch
from src.models.work_center import WorkCenter
from src.storage.minio_service import get_minio_service


@celery_app.task(bind=True, max_retries=1)
def import_batches_from_file(self, file_url: str, user_id: int):
    try:
        minio_service = get_minio_service()

        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp_file:
            tmp_path = tmp_file.name

        try:
            minio_service.download_file(
                bucket=settings.minio_bucket_imports,
                object_name=file_url.split("/")[-1],
                file_path=tmp_path
            )

            import pandas as pd

            df = pd.read_excel(tmp_path)
            total_rows = len(df)
            created = 0
            skipped = 0
            errors = []

            with Session(sync_engine) as db:
                for idx, row in df.iterrows():
                    try:
                        existing = db.execute(
                            select(Batch).where(
                                Batch.batch_number == row["НомерПартии"],
                                Batch.batch_date == row["ДатаПартии"]
                            )
                        ).scalar_one_or_none()

                        if existing:
                            errors.append({"row": idx + 2, "error": "Duplicate batch"})
                            skipped += 1
                            continue

                        work_center = db.execute(
                            select(WorkCenter).where(
                                WorkCenter.identifier == row["ИдентификаторРЦ"]
                            )
                        ).scalar_one_or_none()

                        if not work_center:
                            errors.append({
                                "row": idx + 2,
                                "error": f"Work center '{row['ИдентификаторРЦ']}' not found"
                            })
                            skipped += 1
                            continue

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
                        errors.append({"row": idx + 2, "error": str(e)})
                        skipped += 1

                db.commit()

            return {
                "success": True,
                "total_rows": total_rows,
                "created": created,
                "skipped": skipped,
                "errors": errors
            }

        finally:
            Path(tmp_path).unlink(missing_ok=True)

    except Exception as exc:
        self.retry(exc=exc, countdown=300)


@celery_app.task
def export_batches_to_file(filters: dict, format: str = "excel"):
    import pandas as pd

    with Session(sync_engine) as db:
        query = select(Batch).options(selectinload(Batch.work_center))

        if "is_closed" in filters:
            query = query.where(Batch.is_closed == filters["is_closed"])
        if "date_from" in filters:
            query = query.where(Batch.batch_date >= filters["date_from"])
        if "date_to" in filters:
            query = query.where(Batch.batch_date <= filters["date_to"])

        batches = db.execute(query).scalars().all()

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

        suffix = ".xlsx" if format == "excel" else f".{format}"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp_file:
            tmp_path = tmp_file.name

        try:
            if format == "excel":
                df.to_excel(tmp_path, index=False)
            elif format == "csv":
                df.to_csv(tmp_path, index=False)

            minio_service = get_minio_service()
            object_name = f"batches_export_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.{format}"
            file_url = minio_service.upload_file(
                bucket=settings.minio_bucket_exports,
                file_path=tmp_path,
                object_name=object_name,
            )

            return {
                "success": True,
                "file_url": file_url,
                "total_batches": len(batches)
            }

        finally:
            Path(tmp_path).unlink(missing_ok=True)