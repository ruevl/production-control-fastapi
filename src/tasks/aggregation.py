import asyncio
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.celery_app import celery_app
from src.db.session import engine
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
    Асинхронная массовая аггрегация продукции.
    """
    try:
        async def _aggregate():
            async with AsyncSession(engine) as db:
                batch_query = select(Batch).where(Batch.id == batch_id)
                result = await db.execute(batch_query)
                batch = result.scalar_one_or_none()

                if not batch:
                    raise ValueError(f"Batch {batch_id} not found")

                total = len(unique_codes)
                aggregated_count = 0
                failed_count = 0
                errors = []

                for i, code in enumerate(unique_codes):
                    try:
                        product_query = select(Product).where(
                            Product.unique_code == code,
                            Product.batch_id == batch_id
                        )
                        product_result = await db.execute(product_query)
                        product = product_result.scalar_one_or_none()

                        if not product:
                            errors.append({"code": code, "reason": "Product not found"})
                            failed_count += 1
                            continue

                        if product.is_aggregated:
                            errors.append({"code": code, "reason": "Already aggregated"})
                            failed_count += 1
                            continue

                        product.is_aggregated = True
                        product.aggregated_at = datetime.utcnow()
                        aggregated_count += 1

                        # Update progress
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

                await db.commit()

                return {
                    "success": True,
                    "total": total,
                    "aggregated": aggregated_count,
                    "failed": failed_count,
                    "errors": errors
                }

        return asyncio.run(_aggregate())

    except Exception as exc:
        self.retry(exc=exc, countdown=60)
