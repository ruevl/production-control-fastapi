
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.work_center import WorkCenter
from src.repositories.base_repository import BaseRepository


class WorkCenterRepository(BaseRepository[WorkCenter]):
    def __init__(self, db: AsyncSession):
        super().__init__(WorkCenter, db)

    async def get_by_identifier(self, identifier: str) -> Optional[WorkCenter]:
        result = await self.db.execute(
            select(WorkCenter).where(WorkCenter.identifier == identifier)
        )
        return result.scalar_one_or_none()
