"""Utility functions for common operations."""
import os
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode, urlparse, parse_qsl, urlunparse
from uuid import uuid4
import httpx
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


def validate_upload_file(upload_file, allowed_extensions: set[str], max_bytes: int, label: str) -> None:
    """Validate an uploaded file before persisting it."""
    filename = (upload_file.filename or "").strip()
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


def upload_file_to_r2(upload_file, folder: str, filename: str) -> str:
    """Compatibility wrapper delegating file persistence to the R2 adapter."""
    from .adapters.r2_storage import R2StorageService

    return R2StorageService().upload_file(upload_file, folder, filename)


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


def build_checkout_url(base_url: str, custom_data: dict[str, str], email: str | None = None) -> str:
    """Build checkout URL with custom data."""
    parsed_url = urlparse(base_url)
    query_items = dict(parse_qsl(parsed_url.query, keep_blank_values=True))

    if email:
        query_items["checkout[email]"] = email

    for key, value in custom_data.items():
        query_items[f"checkout[custom][{key}]"] = value

    return urlunparse(parsed_url._replace(query=urlencode(query_items)))


def extract_nested_dict(payload: dict, target_key: str) -> dict | None:
    """Recursively extract nested dictionary from payload."""
    if not isinstance(payload, dict):
        return None

    if target_key in payload and isinstance(payload[target_key], dict):
        return payload[target_key]

    for value in payload.values():
        if isinstance(value, dict):
            nested = extract_nested_dict(value, target_key)
            if nested is not None:
                return nested
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    nested = extract_nested_dict(item, target_key)
                    if nested is not None:
                        return nested

    return None


def extract_custom_data(payload: dict) -> dict[str, str]:
    """Compatibility wrapper for webhook custom data extraction."""
    from .adapters.lemon_squeezy import LemonSqueezyService

    return LemonSqueezyService.extract_custom_data(payload)


def is_successful_payment_event(payload: dict) -> bool:
    """Compatibility wrapper for Lemon Squeezy event classification."""
    from .adapters.lemon_squeezy import LemonSqueezyService

    return LemonSqueezyService.is_successful_payment_event(payload)


def verify_webhook_signature(raw_body: bytes, signature: str | None) -> bool:
    """Compatibility wrapper for Lemon Squeezy webhook verification."""
    from .adapters.lemon_squeezy import LemonSqueezyService

    return LemonSqueezyService().verify_webhook(raw_body, signature)


async def create_lemonsqueezy_checkout(
    *,
    variant_quantities: list[dict[str, int]],
    custom_data: dict[str, str],
    email: str | None = None,
    custom_price: int | None = None,
) -> str:
    """Compatibility wrapper delegating checkout creation to the payment adapter."""
    from .adapters.lemon_squeezy import LemonSqueezyService

    return await LemonSqueezyService().create_checkout_session(
        variant_quantities=variant_quantities,
        custom_data=custom_data,
        email=email,
        custom_price=custom_price,
    )


def _pdf_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def generate_license_pdf(
    *,
    purchase_id: int,
    buyer_name: str,
    buyer_email: str,
    track_title: str,
    track_artist: str,
    license_type: str,
    purchased_at: datetime,
) -> bytes:
    """Generate a simple one-page PDF license document."""
    purchased_at_str = purchased_at.strftime("%Y-%m-%d %H:%M:%S UTC")
    lines = [
        "DJ Bilal Music Store - Lisans Belgesi",
        "",
        f"Belge No: LIC-{purchase_id}",
        f"Musteri: {buyer_name}",
        f"E-posta: {buyer_email}",
        f"Eser: {track_title}",
        f"Sanatci: {track_artist}",
        f"Lisans Turu: {license_type}",
        f"Satin Alma Tarihi: {purchased_at_str}",
        "",
        "Bu belge satin alma kaydina bagli dijital lisans kanitidir.",
    ]

    content_lines = ["BT", "/F1 12 Tf", "50 780 Td"]
    first_text = _pdf_escape(lines[0])
    content_lines.append(f"({first_text}) Tj")
    for line in lines[1:]:
        content_lines.append("0 -18 Td")
        content_lines.append(f"({_pdf_escape(line)}) Tj")
    content_lines.append("ET")
    content_stream = "\n".join(content_lines).encode("latin-1", errors="replace")

    objects = [
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n",
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>\nendobj\n",
        b"4 0 obj\n<< /Length " + str(len(content_stream)).encode("ascii") + b" >>\nstream\n" + content_stream + b"\nendstream\nendobj\n",
        b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n",
    ]

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objects:
        offsets.append(len(pdf))
        pdf.extend(obj)

    xref_start = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        (
            "trailer\n"
            f"<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            "startxref\n"
            f"{xref_start}\n"
            "%%EOF\n"
        ).encode("ascii")
    )
    return bytes(pdf)