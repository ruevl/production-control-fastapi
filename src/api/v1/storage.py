import contextlib
import logging
import tempfile
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from src.core.config import settings
from src.storage.minio_service import MinIOService, get_minio_service

router = APIRouter(prefix="/storage", tags=["Storage"])
logger = logging.getLogger(__name__)


def validate_bucket(bucket: str) -> str:
    valid_buckets = [
        settings.minio_bucket_imports,
        settings.minio_bucket_exports,
        settings.minio_bucket_reports,
    ]
    if bucket not in valid_buckets:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid bucket. Must be one of: {valid_buckets}",
        )
    return bucket


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_file(
        file: UploadFile = File(...),
        bucket: str = Depends(validate_bucket),
        folder: Optional[str] = None,
        minio_service: MinIOService = Depends(get_minio_service),
):
    file_extension = Path(file.filename).suffix if file.filename else ".bin"
    object_name = f"{folder + '/' if folder else ''}{uuid.uuid4()}{file_extension}"
    content = await file.read()

    with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp_file:
        tmp_file.write(content)
        tmp_path = tmp_file.name

    try:
        file_url = minio_service.upload_file(
            bucket=bucket,
            file_path=tmp_path,
            object_name=object_name,
            content_type=file.content_type or "application/octet-stream"
        )
        return {
            "success": True,
            "file_url": file_url,
            "object_name": object_name,
            "bucket": bucket,
            "size": len(content)
        }
    except Exception as e:
        logger.error("MinIO upload failed: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="File upload failed. Please try again later."
        )
    finally:
        with contextlib.suppress(FileNotFoundError):
            Path(tmp_path).unlink()


@router.get("/download/{object_name}")
async def download_file(
        object_name: str,
        bucket: str = Depends(validate_bucket),
        minio_service: MinIOService = Depends(get_minio_service),
):
    try:
        url = minio_service.get_presigned_url(
            bucket=bucket,
            object_name=object_name,
            expires_days=1
        )
        return {"success": True, "download_url": url, "expires_in": "24 hours"}
    except Exception as e:
        logger.error("MinIO download failed: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found."
        )


@router.delete("/delete/{object_name}")
async def delete_file(
        object_name: str,
        bucket: str = Depends(validate_bucket),
        minio_service: MinIOService = Depends(get_minio_service),
):
    try:
        minio_service.delete_file(bucket=bucket, object_name=object_name)
        return {"success": True, "message": "File deleted"}
    except Exception as e:
        logger.error("MinIO delete failed: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found."
        )


@router.get("/list")
async def list_files(
        bucket: str = Depends(validate_bucket),
        prefix: Optional[str] = "",
        minio_service: MinIOService = Depends(get_minio_service),
):
    try:
        files = minio_service.list_files(bucket=bucket, prefix=prefix or "")
        return {"success": True, "bucket": bucket, "files": files, "count": len(files)}
    except Exception as e:
        logger.error("MinIO list failed: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list files. Please try again later."
        )