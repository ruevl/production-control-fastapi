from datetime import timedelta
from functools import lru_cache

from minio import Minio
from minio.error import S3Error

from src.core.config import Settings, get_settings


class MinIOService:
    def __init__(self, settings: Settings):
        self._settings = settings
        self._client: Minio | None = None

    @property
    def client(self) -> Minio:
        if self._client is None:
            self._client = Minio(
                self._settings.minio_endpoint,
                access_key=self._settings.minio_access_key,
                secret_key=self._settings.minio_secret_key,
                secure=self._settings.minio_secure,
            )
        return self._client

    def _ensure_bucket(self, bucket_name: str) -> None:
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
            return f"http://{self._settings.minio_endpoint}/{bucket}/{object_name}"
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


@lru_cache
def get_minio_service() -> MinIOService:
    return MinIOService(get_settings())