"""Utility functions for common operations."""
import io
import os
import re
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4
from fastapi import Request, HTTPException, status


UPLOAD_ROOT = Path(__file__).resolve().parent / "uploads"
TRACK_UPLOAD_DIR = UPLOAD_ROOT / "tracks"
PREVIEW_UPLOAD_DIR = UPLOAD_ROOT / "previews"
COVER_UPLOAD_DIR = UPLOAD_ROOT / "covers"

MAX_TRACK_UPLOAD_BYTES = int(os.getenv("MAX_TRACK_UPLOAD_BYTES", str(250 * 1024 * 1024)))
MAX_PREVIEW_UPLOAD_BYTES = int(os.getenv("MAX_PREVIEW_UPLOAD_BYTES", str(50 * 1024 * 1024)))
MAX_COVER_UPLOAD_BYTES = int(os.getenv("MAX_COVER_UPLOAD_BYTES", str(10 * 1024 * 1024)))

AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".flac", ".ogg", ".aac"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}

TRACK_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
PREVIEW_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
COVER_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

def build_storage_name(filename: str) -> str:
    """Generate unique filename for uploaded file."""
    safe_name = Path(filename).name
    suffix = Path(safe_name).suffix.lower()
    stem = Path(safe_name).stem or "upload"
    stem = re.sub(r"[^A-Za-z0-9._-]+", "-", stem).strip("._-") or "upload"
    return f"{stem}-{uuid4().hex}{suffix}"


def validate_upload_data(
    filename: str | None,
    size: int,
    allowed_extensions: set[str],
    max_bytes: int,
    label: str,
) -> None:
    """Validate an upload's filename and exact content size."""
    filename = (filename or "").strip()
    if not filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{label} filename is required",
        )

    extension = Path(filename).suffix.lower()
    if extension not in allowed_extensions:
        allowed = ", ".join(sorted(allowed_extensions))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{label} must use one of these file types: {allowed}",
        )

    if max_bytes <= 0:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{label} size limit is misconfigured",
        )

    if size > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"{label} exceeds the maximum size of {max_bytes} bytes",
        )


def validate_upload_file(
    upload_file, allowed_extensions: set[str], max_bytes: int, label: str
) -> None:
    """Validate an uploaded file's metadata before reading its contents."""
    upload_size = getattr(upload_file, "size", None)
    validate_upload_data(
        upload_file.filename,
        upload_size if isinstance(upload_size, int) else 0,
        allowed_extensions,
        max_bytes,
        label,
    )


def build_media_url(request: Request, folder: str, filename: str) -> str:
    """Build media path to avoid proxy scheme/domain mismatches."""
    return f"/media/{folder}/{filename}"


def get_r2_config() -> dict[str, str | None]:
    """Compatibility wrapper for R2 adapter configuration."""
    from .adapters.r2_storage import R2StorageService

    return R2StorageService.get_config()


def is_r2_object_key(value: str | None) -> bool:
    """Detect a Cloudflare R2 object key stored in the database."""
    if not value:
        return False
    normalized = value.strip().lstrip("/")
    if normalized.startswith("http://") or normalized.startswith("https://"):
        return False
    return bool(normalized) and "/" in normalized and not normalized.startswith("media/")


def get_r2_client():
    """Compatibility wrapper for the R2 storage adapter's boto3 client."""
    from .adapters.r2_storage import R2StorageService

    return R2StorageService._client()


def build_r2_public_url(folder: str, filename: str) -> str | None:
    """Compatibility wrapper for public R2 URLs."""
    from .adapters.r2_storage import R2StorageService

    return R2StorageService.build_public_url(folder, filename)


async def upload_file_to_r2(
    content: bytes | io.BytesIO, folder: str, filename: str
) -> str:
    """Compatibility wrapper delegating file persistence to the R2 adapter."""
    from .adapters.r2_storage import R2StorageService

    return await R2StorageService().upload_file(content, folder, filename)


def generate_r2_presigned_download_url(file_key: str, expires_in: int = 900) -> str:
    """Compatibility wrapper delegating signed URL creation to the R2 adapter."""
    from .adapters.r2_storage import R2StorageService

    return R2StorageService().generate_signed_url(file_key, expires_in)


def normalize_media_url(url: str | None) -> str | None:
    """Normalize media URLs to app-relative /media paths when possible."""
    if not url:
        return url

    if url.startswith("/media/"):
        return url

    parsed = urlparse(url)
    if parsed.path.startswith("/media/"):
        return parsed.path

    return url


def resolve_uploaded_file_path(url: str | None, folder: str) -> Path:
    """Resolve an app media URL to an existing local uploaded file path."""
    normalized = normalize_media_url(url)
    if not normalized:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File path is missing",
        )

    parsed = urlparse(normalized)
    media_path = parsed.path or normalized
    expected_prefix = f"/media/{folder}/"
    if not media_path.startswith(expected_prefix):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported media path",
        )

    filename = Path(media_path).name
    if not filename:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File name is missing",
        )

    target_dir = (UPLOAD_ROOT / folder).resolve()
    file_path = (target_dir / filename).resolve()
    if not str(file_path).startswith(str(target_dir)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file path",
        )
    if not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Uploaded file not found on server",
        )
    return file_path


async def save_upload_file(upload_file, destination: Path, max_bytes: int | None = None) -> None:
    """Save uploaded file to disk without buffering the whole payload in memory."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    written = 0

    try:
        with destination.open("wb") as output_file:
            while True:
                chunk = await upload_file.read(1024 * 1024)
                if not chunk:
                    break

                written += len(chunk)
                if max_bytes is not None and written > max_bytes:
                    raise HTTPException(
                        status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                        detail=f"{Path(upload_file.filename or 'upload').name} exceeds the allowed size",
                    )

                output_file.write(chunk)
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    finally:
        await upload_file.close()
