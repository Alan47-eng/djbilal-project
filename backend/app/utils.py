"""Utility functions for common operations."""
import os
import hmac
import json
import hashlib
import re
from pathlib import Path
from urllib.parse import urlencode, urlparse, parse_qsl, urlunparse
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

ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()


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
    """Extract custom data from webhook payload."""
    for key in ("custom_data", "custom", "checkout_data"):
        nested = extract_nested_dict(payload, key)
        if nested:
            return {str(k): str(v) for k, v in nested.items() if v is not None}
    return {}


def is_successful_payment_event(payload: dict) -> bool:
    """Check if webhook payload represents successful payment."""
    event_name = (
        payload.get("meta", {}).get("event_name")
        or payload.get("meta", {}).get("name")
        or payload.get("event_name")
        or payload.get("type")
        or ""
    ).lower()

    status_value = (
        payload.get("data", {}).get("attributes", {}).get("status")
        or payload.get("data", {}).get("attributes", {}).get("status_formatted")
        or payload.get("meta", {}).get("status")
        or ""
    ).lower()

    if any(token in event_name for token in ("order", "payment", "license")):
        return "fail" not in event_name and status_value not in ("failed", "canceled", "cancelled", "unpaid")

    return status_value in ("paid", "succeeded", "successful", "completed")


def verify_webhook_signature(raw_body: bytes, signature: str | None) -> bool:
    """Verify webhook signature from Lemon Squeezy."""
    secret = os.getenv("LEMON_SQUEEZY_WEBHOOK_SECRET", "").strip()
    
    if not secret:
        return ENVIRONMENT != "production"
    
    if not signature:
        return False
    
    expected = hmac.new(
        secret.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected)
