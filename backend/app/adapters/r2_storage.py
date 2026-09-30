import os
from pathlib import Path
from typing import BinaryIO, Mapping, Protocol, cast

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import HTTPException, UploadFile, status

from ..interfaces.storage import BaseStorageService
from ..utils import UPLOAD_ROOT


class S3Client(Protocol):
    def upload_fileobj(self, file_obj: BinaryIO, bucket: str, key: str) -> None: ...

    def generate_presigned_url(
        self,
        client_method: str,
        params: Mapping[str, str],
        expires_in: int,
    ) -> str: ...

    def delete_object(self, **kwargs: str) -> object: ...


class R2StorageService(BaseStorageService):
    """Cloudflare R2 adapter with local-disk fallback for development."""

    @staticmethod
    def get_config() -> dict[str, str | None]:
        return {
            "account_id": os.getenv("R2_ACCOUNT_ID", "").strip() or None,
            "access_key_id": os.getenv("R2_ACCESS_KEY_ID", "").strip() or None,
            "secret_access_key": os.getenv("R2_SECRET_ACCESS_KEY", "").strip() or None,
            "bucket_name": os.getenv("R2_BUCKET_NAME", "").strip() or None,
            "public_url": os.getenv("R2_PUBLIC_URL", "").strip() or None,
        }

    @classmethod
    def build_public_url(cls, folder: str, filename: str) -> str | None:
        public_url = cls.get_config()["public_url"]
        if not public_url:
            return None
        return f"{public_url.rstrip('/')}/{folder.strip('/')}/{filename.lstrip('/')}"

    @staticmethod
    def _client() -> S3Client | None:
        config = R2StorageService.get_config()
        if not all(
            config.get(key)
            for key in ("account_id", "access_key_id", "secret_access_key", "bucket_name")
        ):
            return None

        account_id = config["account_id"]
        access_key_id = config["access_key_id"]
        secret_access_key = config["secret_access_key"]
        if not account_id or not access_key_id or not secret_access_key:
            return None

        return cast(
            S3Client,
            boto3.client(
                "s3",
                endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
                aws_access_key_id=access_key_id,
                aws_secret_access_key=secret_access_key,
                region_name="auto",
            ),
        )

    def upload_file(self, upload_file: UploadFile | BinaryIO, folder: str, filename: str) -> str:
        config = self.get_config()
        file_obj = upload_file.file if isinstance(upload_file, UploadFile) else upload_file
        safe_filename = Path(filename).name
        folder_name = folder.strip("/")
        client = self._client()

        if client is None:
            destination = (UPLOAD_ROOT / folder_name / safe_filename).resolve()
            destination.parent.mkdir(parents=True, exist_ok=True)
            file_obj.seek(0)
            with destination.open("wb") as output_file:
                while True:
                    chunk = file_obj.read(1024 * 1024)
                    if not chunk:
                        break
                    output_file.write(chunk)
            file_obj.seek(0)
            return f"/media/{folder_name}/{safe_filename}"

        bucket_name = config["bucket_name"]
        if not bucket_name:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="R2 bucket is not configured",
            )

        object_key = f"{folder_name}/{safe_filename}"
        try:
            file_obj.seek(0)
            client.upload_fileobj(file_obj, bucket_name, object_key)
        except (BotoCoreError, ClientError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload file to Cloudflare R2: {exc}",
            ) from exc

        if folder_name == "tracks":
            return object_key

        public_url = config.get("public_url")
        if public_url:
            return f"{public_url.rstrip('/')}/{object_key}"
        account_id = config["account_id"]
        if not account_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="R2 account is not configured",
            )
        return f"https://{account_id}.r2.cloudflarestorage.com/{bucket_name}/{object_key}"

    def generate_signed_url(self, object_key: str, expires_in: int = 900) -> str:
        config = self.get_config()
        client = self._client()
        if client is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Cloudflare R2 is not configured",
            )

        bucket_name = config["bucket_name"]
        if not bucket_name:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="R2 bucket is not configured",
            )

        try:
            return client.generate_presigned_url(
                "get_object",
                {"Bucket": bucket_name, "Key": object_key.lstrip("/")},
                expires_in,
            )
        except (BotoCoreError, ClientError) as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate presigned download URL: {exc}",
            ) from exc

    def delete_file(self, object_key: str) -> None:
        config = self.get_config()
        client = self._client()
        if client is None:
            normalized = object_key.strip()
            if normalized.startswith("/media/"):
                normalized = normalized[len("/media/"):]
            local_path = (UPLOAD_ROOT / normalized.lstrip("/")).resolve()
            upload_root = UPLOAD_ROOT.resolve()
            if not local_path.is_relative_to(upload_root):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid file path",
                )
            local_path.unlink(missing_ok=True)
            return

        bucket_name = config["bucket_name"]
        if not bucket_name:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="R2 bucket is not configured",
            )
        try:
            client.delete_object(Bucket=bucket_name, Key=object_key.lstrip("/"))
        except (BotoCoreError, ClientError) as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete file from Cloudflare R2: {exc}",
            ) from exc
