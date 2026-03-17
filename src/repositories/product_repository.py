from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.product import Product
from src.repositories.base_repository import BaseRepository


class ProductRepository(BaseRepository[Product]):
    def __init__(self, db: AsyncSession):
        super().__init__(Product, db)

    async def get_by_unique_code(self, unique_code: str) -> Optional[Product]:
        result = await self.db.execute(
            select(Product).where(Product.unique_code == unique_code)
        )
        return result.scalar_one_or_none()

    async def get_by_batch_id(self, batch_id: int) -> list[Product]:
        result = await self.db.execute(
            select(Product).where(Product.batch_id == batch_id)
        )
        return list(result.scalars().all())

    async def aggregate_product(
        self, unique_code: str, batch_id: int
    ) -> Optional[Product]:
        from datetime import datetime

        product = await self.get_by_unique_code(unique_code)
        if product and product.batch_id == batch_id and not product.is_aggregated:
            product.is_aggregated = True
            product.aggregated_at = datetime.utcnow()
            await self.db.flush()
            await self.db.refresh(product)
            return product
        return None

    async def get_aggregation_stats(self, batch_id: int) -> dict:
        total_query = select(func.count()).where(Product.batch_id == batch_id)
        total_result = await self.db.execute(total_query)
        total = total_result.scalar_one()

        aggregated_query = select(func.count()).where(
            Product.batch_id == batch_id, Product.is_aggregated == True
        )
        aggregated_result = await self.db.execute(aggregated_query)
        aggregated = aggregated_result.scalar_one()

        return {
            "total_products": total,
            "aggregated": aggregated,
            "remaining": total - aggregated,
            "aggregation_rate": round((aggregated / total * 100), 2) if total > 0 else 0,
        }
