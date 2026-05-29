"""Object storage client (S3-compatible). Placeholder — implement with boto3/aiobotocore."""

from __future__ import annotations

from app.config import settings


class StorageClient:
    """Thin wrapper around an S3-compatible object store.

    TODO: implement using aiobotocore for async uploads/downloads.
    """

    def __init__(self) -> None:
        self.endpoint_url = settings.S3_ENDPOINT_URL
        self.bucket = settings.S3_BUCKET_NAME
        self.region = settings.S3_REGION

    async def upload(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        raise NotImplementedError

    async def download(self, key: str) -> bytes:
        raise NotImplementedError

    async def delete(self, key: str) -> None:
        raise NotImplementedError

    async def presigned_url(self, key: str, expires_in: int = 3600) -> str:
        raise NotImplementedError


def get_storage_client() -> StorageClient:
    return StorageClient()
