from datetime import date
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.batch import Batch
from src.repositories.base_repository import BaseRepository


class BatchRepository(BaseRepository[Batch]):
    def __init__(self, db: AsyncSession):
        super().__init__(Batch, db)

    async def get_by_id_with_products(self, batch_id: int) -> Optional[Batch]:
        from sqlalchemy.orm import selectinload

        result = await self.db.execute(
            select(Batch)
            .options(selectinload(Batch.products))
            .where(Batch.id == batch_id)
        )
        return result.scalar_one_or_none()

    async def get_filtered(
        self,
        is_closed: Optional[bool] = None,
        batch_number: Optional[int] = None,
        batch_date: Optional[date] = None,
        work_center_id: Optional[int] = None,
        shift: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Batch], int]:
        query = select(Batch)

        if is_closed is not None:
            query = query.where(Batch.is_closed == is_closed)
        if batch_number is not None:
            query = query.where(Batch.batch_number == batch_number)
        if batch_date is not None:
            query = query.where(Batch.batch_date == batch_date)
        if shift is not None:
            query = query.where(Batch.shift == shift)
        if work_center_id is not None:
            query = query.where(Batch.work_center_id == work_center_id)

        count_query = select(func.count()).select_from(query.subquery())
        count_result = await self.db.execute(count_query)
        total = count_result.scalar_one()

        query = query.order_by(Batch.created_at.desc()).limit(limit).offset(offset)
        result = await self.db.execute(query)
        items = list(result.scalars().all())

        return items, total

    async def get_by_work_center_identifier(
        self, identifier: str
    ) -> Optional[Batch]:
        from src.models.work_center import WorkCenter

        result = await self.db.execute(
            select(Batch)
            .join(WorkCenter)
            .where(WorkCenter.identifier == identifier)
        )
        return result.scalar_one_or_none()
