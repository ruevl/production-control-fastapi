from fastapi import APIRouter

from src.api.v1.batches import router as batches_router
from src.api.v1.products import router as products_router
from src.api.v1.storage import router as storage_router
from src.api.v1.webhooks import router as webhooks_router
from src.api.v1.work_centers import router as work_centers_router

api_router = APIRouter()

api_router.include_router(work_centers_router)
api_router.include_router(batches_router)
api_router.include_router(products_router)
api_router.include_router(webhooks_router)
api_router.include_router(storage_router)
