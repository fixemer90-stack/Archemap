"""Legacy object storage boundary.

The report PDF path no longer uses object storage. Keep this module as a small
compatibility placeholder so old imports fail explicitly if someone tries to use
artifact storage again without adding a new storage contract.
"""

from __future__ import annotations


class StorageClient:
    """Disabled object-storage client placeholder."""

    async def upload(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        raise NotImplementedError("Object storage is not configured for this application runtime")

    async def download(self, key: str) -> bytes:
        raise NotImplementedError("Object storage is not configured for this application runtime")

    async def delete(self, key: str) -> None:
        raise NotImplementedError("Object storage is not configured for this application runtime")

    async def presigned_url(self, key: str, expires_in: int = 3600) -> str:
        raise NotImplementedError("Object storage is not configured for this application runtime")


def get_storage_client() -> StorageClient:
    return StorageClient()
