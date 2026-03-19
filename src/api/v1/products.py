from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_batch_repository, get_db, get_product_repository
from src.repositories.batch_repository import BatchRepository
from src.repositories.product_repository import ProductRepository
from src.schemas import ProductCreate, ProductResponse

router = APIRouter(prefix="/products", tags=["Products"])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ProductResponse)
async def create_product(
        product_data: ProductCreate,
        db: AsyncSession = Depends(get_db),
        product_repo: ProductRepository = Depends(get_product_repository),
        batch_repo: BatchRepository = Depends(get_batch_repository),
):
    batch = await batch_repo.get_by_id(product_data.batch_id)
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found")

    existing = await product_repo.get_by_unique_code(product_data.unique_code)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Product with this unique code already exists",
        )

    product = await product_repo.create(
        {
            "unique_code": product_data.unique_code,
            "batch_id": product_data.batch_id,
        }
    )
    await db.commit()

    return ProductResponse.model_validate(product)
