"""S3/MinIO storage client for report artifacts."""

from __future__ import annotations

import boto3
import structlog
from typing import cast
from botocore.config import Config
from botocore.exceptions import ClientError

from app.config import settings

logger = structlog.get_logger()


class S3Storage:
    """S3-compatible storage client (MinIO / AWS S3)."""

    def __init__(self) -> None:
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT_URL,
            aws_access_key_id=settings.S3_ACCESS_KEY_ID,
            aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
            region_name=settings.S3_REGION,
            config=Config(signature_version="s3v4"),
        )
        self.bucket = settings.S3_BUCKET_NAME

    async def upload(
        self,
        key: str,
        data: bytes,
        content_type: str = "application/pdf",
    ) -> str:
        """Upload file to S3 and return the key."""
        try:
            self.client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=data,
                ContentType=content_type,
            )
            logger.info("s3_upload_success", key=key, size=len(data))
            return key
        except ClientError as e:
            logger.error("s3_upload_failed", key=key, error=str(e))
            raise

    def get_signed_url(self, key: str, expires_in: int = 3600) -> str:
        """Generate a signed URL for downloading."""
        try:
            url = cast(
                str,
                self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": key},
                ExpiresIn=expires_in,
                ),
            )
            logger.info("s3_signed_url_generated", key=key, expires_in=expires_in)
            return url
        except ClientError as e:
            logger.error("s3_signed_url_failed", key=key, error=str(e))
            raise

    async def delete(self, key: str) -> None:
        """Delete file from S3."""
        try:
            self.client.delete_object(Bucket=self.bucket, Key=key)
            logger.info("s3_delete_success", key=key)
        except ClientError as e:
            logger.error("s3_delete_failed", key=key, error=str(e))
            raise

    def ensure_bucket(self) -> None:
        """Create bucket if it doesn't exist."""
        try:
            self.client.head_bucket(Bucket=self.bucket)
        except ClientError:
            try:
                self.client.create_bucket(Bucket=self.bucket)
                logger.info("s3_bucket_created", bucket=self.bucket)
            except ClientError as e:
                logger.error("s3_bucket_create_failed", bucket=self.bucket, error=str(e))
                raise


def build_report_key(user_id: str, report_id: str, version: int) -> str:
    """Build S3 key for a report PDF."""
    return f"reports/{user_id}/{report_id}/v{version}.pdf"


def get_signed_ttl(mode: str) -> int:
    """Get signed URL TTL based on report mode."""
    if mode == "full":
        return 86400  # 24 hours for paid
    return 3600  # 1 hour for free/preview
