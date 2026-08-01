"""Utility functions for common operations."""
import os
import hmac
import json
import hashlib
from pathlib import Path
from urllib.parse import urlencode, urlparse, parse_qsl, urlunparse
from uuid import uuid4
from fastapi import Request


UPLOAD_ROOT = Path(__file__).resolve().parent / "uploads"
TRACK_UPLOAD_DIR = UPLOAD_ROOT / "tracks"
PREVIEW_UPLOAD_DIR = UPLOAD_ROOT / "previews"
COVER_UPLOAD_DIR = UPLOAD_ROOT / "covers"

TRACK_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
PREVIEW_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
COVER_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def build_storage_name(filename: str) -> str:
    """Generate unique filename for uploaded file."""
    suffix = Path(filename).suffix
    stem = Path(filename).stem or "upload"
    return f"{stem}-{uuid4().hex}{suffix}"


def build_media_url(request: Request, folder: str, filename: str) -> str:
    """Build full URL to media file."""
    return f"{str(request.base_url).rstrip('/')}/media/{folder}/{filename}"


async def save_upload_file(upload_file, destination: Path) -> None:
    """Save uploaded file to disk."""
    contents = await upload_file.read()
    destination.write_bytes(contents)
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
        return True  # Skip verification if secret not configured
    
    if not signature:
        return False
    
    expected = hmac.new(
        secret.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected)
