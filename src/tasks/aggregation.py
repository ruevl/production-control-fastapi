from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.celery_app import celery_app
from src.db.session import sync_engine  # синхронный движок для Celery
from src.models.batch import Batch
from src.models.product import Product


@celery_app.task(bind=True, max_retries=3)
def aggregate_products_batch(
        self,
        batch_id: int,
        unique_codes: list[str],
        user_id: int | None = None
):
    """
    Массовая агрегация продукции.
    Используем синхронный SQLAlchemy — без asyncio.run() внутри Celery.
    """
    try:
        with Session(sync_engine) as db:
            batch = db.execute(
                select(Batch).where(Batch.id == batch_id)
            ).scalar_one_or_none()

            if not batch:
                raise ValueError(f"Batch {batch_id} not found")

            total = len(unique_codes)
            aggregated_count = 0
            failed_count = 0
            errors = []

            for i, code in enumerate(unique_codes):
                try:
                    product = db.execute(
                        select(Product).where(
                            Product.unique_code == code,
                            Product.batch_id == batch_id
                        )
                    ).scalar_one_or_none()

                    if not product:
                        errors.append({"code": code, "reason": "Product not found"})
                        failed_count += 1
                        continue

                    if product.is_aggregated:
                        errors.append({"code": code, "reason": "Already aggregated"})
                        failed_count += 1
                        continue

                    product.is_aggregated = True
                    product.aggregated_at = datetime.now(timezone.utc)  # fix #20
                    aggregated_count += 1

                    self.update_state(
                        state="PROGRESS",
                        meta={
                            "current": i + 1,
                            "total": total,
                            "progress": int((i + 1) / total * 100)
                        }
                    )

                except Exception as e:
                    errors.append({"code": code, "reason": str(e)})
                    failed_count += 1

            db.commit()

            return {
                "success": True,
                "total": total,
                "aggregated": aggregated_count,
                "failed": failed_count,
                "errors": errors
            }

    except Exception as exc:
        self.retry(exc=exc, countdown=60)