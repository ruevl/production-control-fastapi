from datetime import timedelta

from minio import Minio
from minio.error import S3Error

from src.core.config import settings


class MinIOService:

    def __init__(self):
        self.client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure
        )

    def _ensure_bucket(self, bucket_name: str) -> None:
        """Создаёт бакет, если он не существует."""
        if not self.client.bucket_exists(bucket_name):
            self.client.make_bucket(bucket_name)

    def upload_file(
            self,
            bucket: str,
            file_path: str,
            object_name: str,
            content_type: str = "application/octet-stream"
    ) -> str:
        self._ensure_bucket(bucket)

        try:
            self.client.fput_object(
                bucket_name=bucket,
                object_name=object_name,
                file_path=file_path,
                content_type=content_type
            )
            return f"http://{settings.minio_endpoint}/{bucket}/{object_name}"
        except S3Error as e:
            raise Exception(f"Failed to upload file: {e}") from e

    def download_file(self, bucket: str, object_name: str, file_path: str) -> str:
        try:
            self.client.fget_object(
                bucket_name=bucket,
                object_name=object_name,
                file_path=file_path
            )
            return file_path
        except S3Error as e:
            raise Exception(f"Failed to download file: {e}") from e

    def get_presigned_url(self, bucket: str, object_name: str, expires_days: int = 7) -> str:
        try:
            url = self.client.presigned_get_object(
                bucket_name=bucket,
                object_name=object_name,
                expires=timedelta(days=expires_days)
            )
            return url
        except S3Error as e:
            raise Exception(f"Failed to generate presigned URL: {e}") from e

    def delete_file(self, bucket: str, object_name: str) -> bool:
        try:
            self.client.remove_object(bucket_name=bucket, object_name=object_name)
            return True
        except S3Error as e:
            raise Exception(f"Failed to delete file: {e}") from e

    def list_files(self, bucket: str, prefix: str = "") -> list[dict]:
        try:
            objects = self.client.list_objects(bucket, prefix=prefix)
            return [
                {
                    "object_name": obj.object_name,
                    "size": obj.size,
                    "last_modified": obj.last_modified,
                    "etag": obj.etag
                }
                for obj in objects
            ]
        except S3Error as e:
            raise Exception(f"Failed to list files: {e}") from e

    def file_exists(self, bucket: str, object_name: str) -> bool:
        try:
            self.client.stat_object(bucket_name=bucket, object_name=object_name)
            return True
        except S3Error:
            return False


minio_service = MinIOService()
