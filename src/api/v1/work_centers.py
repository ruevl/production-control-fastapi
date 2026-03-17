from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db, get_work_center_repository
from src.repositories.work_center_repository import WorkCenterRepository
from src.schemas import WorkCenterCreate, WorkCenterResponse

router = APIRouter(prefix="/work-centers", tags=["Work Centers"])


@router.post(
    "", status_code=status.HTTP_201_CREATED, response_model=WorkCenterResponse
)
async def create_work_center(
    wc_data: WorkCenterCreate,
    db: AsyncSession = Depends(get_db),
    wc_repo: WorkCenterRepository = Depends(get_work_center_repository),
):
    existing = await wc_repo.get_by_identifier(wc_data.identifier)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Work center with this identifier already exists",
        )

    work_center = await wc_repo.create(
        {"identifier": wc_data.identifier, "name": wc_data.name}
    )
    await db.commit()

    return WorkCenterResponse.model_validate(work_center)


@router.get("/{wc_id}", response_model=WorkCenterResponse)
async def get_work_center(
    wc_id: int,
    wc_repo: WorkCenterRepository = Depends(get_work_center_repository),
):
    work_center = await wc_repo.get_by_id(wc_id)
    if not work_center:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Work center not found"
        )

    return WorkCenterResponse.model_validate(work_center)
