"""MinIO / S3-compatible storage client using boto3."""
import os
import boto3
from pathlib import Path
from loguru import logger


class MinIOClient:
    """S3-compatible storage abstraction. Change endpoint to switch providers."""

    def __init__(self, endpoint: str, access_key: str, secret_key: str, bucket: str, temp_dir: str = "/tmp/rag-service"):
        self.endpoint = endpoint
        self.bucket = bucket
        self.temp_dir = Path(temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        self.s3 = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )
        self._ensure_bucket()

    def _ensure_bucket(self):
        try:
            self.s3.head_bucket(Bucket=self.bucket)
        except Exception:
            self.s3.create_bucket(Bucket=self.bucket)
            logger.info(f"Created bucket: {self.bucket}")

    def download_file(self, object_key: str, local_path: str = None) -> str:
        """Download a file from MinIO to a local path. Returns the local path."""
        if local_path is None:
            local_path = str(self.temp_dir / Path(object_key).name)

        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        self.s3.download_file(self.bucket, object_key, local_path)
        logger.debug(f"Downloaded: {object_key} -> {local_path}")
        return local_path

    def upload_file(self, local_path: str, object_key: str):
        """Upload a file to MinIO."""
        self.s3.upload_file(local_path, self.bucket, object_key)
        logger.debug(f"Uploaded: {local_path} -> {object_key}")

    def delete_file(self, object_key: str):
        """Delete a file from MinIO."""
        self.s3.delete_object(Bucket=self.bucket, Key=object_key)
        logger.debug(f"Deleted: {object_key}")

    def file_exists(self, object_key: str) -> bool:
        """Check if file exists in MinIO."""
        try:
            self.s3.head_object(Bucket=self.bucket, Key=object_key)
            return True
        except Exception:
            return False
