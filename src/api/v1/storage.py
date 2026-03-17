import tempfile
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from src.core.config import settings
from src.storage.minio_service import minio_service

router = APIRouter(prefix="/storage", tags=["Storage"])


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_file(
        file: UploadFile = File(...),
        bucket: str = "imports",
        folder: Optional[str] = None
):

    valid_buckets = [
        settings.minio_bucket_imports,
        settings.minio_bucket_exports,
        settings.minio_bucket_reports
    ]
    if bucket not in valid_buckets:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid bucket. Must be one of: {valid_buckets}"
        )

    file_extension = Path(file.filename).suffix if file.filename else ".bin"
    object_name = f"{folder + '/' if folder else ''}{uuid.uuid4()}{file_extension}"

    with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp_file:
        content = await file.read()
        tmp_file.write(content)
        tmp_path = tmp_file.name

    try:

        file_url = minio_service.upload_file(
            bucket=bucket,
            file_path=tmp_path,
            object_name=object_name,
            content_type=file.content_type or "application/octet-stream"
        )

        Path(tmp_path).unlink()

        return {
            "success": True,
            "file_url": file_url,
            "object_name": object_name,
            "bucket": bucket,
            "size": len(content)
        }

    except Exception as e:
        Path(tmp_path).unlink()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/download/{object_name}")
async def download_file(
        object_name: str,
        bucket: str = "imports"
):

    try:

        url = minio_service.get_presigned_url(
            bucket=bucket,
            object_name=object_name,
            expires_days=1
        )

        return {
            "success": True,
            "download_url": url,
            "expires_in": "24 hours"
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found: {e}"
        )


@router.delete("/delete/{object_name}")
async def delete_file(
        object_name: str,
        bucket: str = "imports"
):

    try:
        minio_service.delete_file(bucket=bucket, object_name=object_name)
        return {"success": True, "message": "File deleted"}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found: {e}"
        )


@router.get("/list")
async def list_files(
        bucket: str = "imports",
        prefix: Optional[str] = ""
):
    try:
        files = minio_service.list_files(bucket=bucket, prefix=prefix or "")
        return {
            "success": True,
            "bucket": bucket,
            "files": files,
            "count": len(files)
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
