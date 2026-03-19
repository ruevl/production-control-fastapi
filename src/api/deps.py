from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_db
from src.repositories.batch_repository import BatchRepository
from src.repositories.product_repository import ProductRepository
from src.repositories.work_center_repository import WorkCenterRepository


def get_batch_repository(
        db: AsyncSession = Depends(get_db),
) -> BatchRepository:
    return BatchRepository(db)


def get_product_repository(
        db: AsyncSession = Depends(get_db),
) -> ProductRepository:
    return ProductRepository(db)


def get_work_center_repository(
        db: AsyncSession = Depends(get_db),
) -> WorkCenterRepository:
    return WorkCenterRepository(db)
