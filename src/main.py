from fastapi import FastAPI

from src.api.router import api_router
from src.core.config import settings

app = FastAPI(
    title=settings.project_name,
    description="Система контроля заданий на выпуск продукции",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "production-control"}


@app.get("/")
def root():
    return {"message": "Production Control API v1"}
