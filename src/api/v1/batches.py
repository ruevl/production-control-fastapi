from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import (
    get_batch_repository,
    get_db,
    get_product_repository,
    get_work_center_repository,
)
from src.repositories.batch_repository import BatchRepository
from src.repositories.product_repository import ProductRepository
from src.repositories.work_center_repository import WorkCenterRepository
from src.schemas import (
    BatchCreate,
    BatchDetailResponse,
    BatchListResponse,
    BatchResponse,
    BatchUpdate,
    ProductResponse,
)

router = APIRouter(prefix="/batches", tags=["Batches"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_batches(
    batches_data: list[BatchCreate],
    db: AsyncSession = Depends(get_db),
    batch_repo: BatchRepository = Depends(get_batch_repository),
    work_center_repo: WorkCenterRepository = Depends(get_work_center_repository),
) -> list[BatchResponse]:
    created = []
    for batch_data in batches_data:
        work_center = await work_center_repo.get_by_identifier(
            batch_data.work_center_identifier
        )
        if not work_center:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Work center '{batch_data.work_center_identifier}' not found",
            )

        batch = await batch_repo.create(
            {
                "is_closed": batch_data.is_closed,
                "task_description": batch_data.task_description,
                "work_center_id": work_center.id,
                "shift": batch_data.shift,
                "team": batch_data.team,
                "batch_number": batch_data.batch_number,
                "batch_date": batch_data.batch_date,
                "nomenclature": batch_data.nomenclature,
                "ekn_code": batch_data.ekn_code,
                "shift_start": batch_data.shift_start,
                "shift_end": batch_data.shift_end,
            }
        )
        created.append(BatchResponse.model_validate(batch))

    await db.commit()
    return created


@router.get("", response_model=BatchListResponse)
async def list_batches(
    db: AsyncSession = Depends(get_db),
    batch_repo: BatchRepository = Depends(get_batch_repository),
    is_closed: Optional[bool] = Query(None),
    batch_number: Optional[int] = Query(None),
    batch_date: Optional[date] = Query(None),
    work_center_id: Optional[str] = Query(None),
    shift: Optional[str] = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    work_center_id_int = None
    if work_center_id:
        from src.repositories.work_center_repository import WorkCenterRepository

        wc_repo = WorkCenterRepository(db)
        wc = await wc_repo.get_by_identifier(work_center_id)
        if wc:
            work_center_id_int = wc.id

    items, total = await batch_repo.get_filtered(
        is_closed=is_closed,
        batch_number=batch_number,
        batch_date=batch_date,
        work_center_id=work_center_id_int,
        shift=shift,
        limit=limit,
        offset=offset,
    )

    return BatchListResponse(
        items=[BatchResponse.model_validate(item) for item in items],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/{batch_id}", response_model=BatchDetailResponse)
async def get_batch(
    batch_id: int,
    db: AsyncSession = Depends(get_db),
    batch_repo: BatchRepository = Depends(get_batch_repository),
):
    batch = await batch_repo.get_by_id_with_products(batch_id)
    if not batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found"
        )

    return BatchDetailResponse.model_validate(
        {
            **batch.__dict__,
            "products": [ProductResponse.model_validate(p) for p in batch.products],
        }
    )


@router.patch("/{batch_id}", response_model=BatchResponse)
async def update_batch(
    batch_id: int,
    batch_update: BatchUpdate,
    db: AsyncSession = Depends(get_db),
    batch_repo: BatchRepository = Depends(get_batch_repository),
):
    batch = await batch_repo.get_by_id(batch_id)
    if not batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found"
        )

    from datetime import datetime

    update_data = batch_update.model_dump(exclude_unset=True)

    if "is_closed" in update_data:
        if update_data["is_closed"] and not batch.is_closed:
            update_data["closed_at"] = datetime.utcnow()
        elif not update_data["is_closed"] and batch.is_closed:
            update_data["closed_at"] = None

    await batch_repo.update(batch, update_data)
    await db.commit()
    await db.refresh(batch)

    return BatchResponse.model_validate(batch)


@router.post("/{batch_id}/aggregate", response_model=dict)
async def aggregate_batch(
    batch_id: int,
    db: AsyncSession = Depends(get_db),
    product_repo: ProductRepository = Depends(get_product_repository),
):
    batch_repo = BatchRepository(db)
    batch = await batch_repo.get_by_id(batch_id)
    if not batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found"
        )

    stats = await product_repo.get_aggregation_stats(batch_id)
    return {"success": True, "batch_id": batch_id, "statistics": stats}
