import os
import re
from urllib.parse import urlparse

from dotenv import load_dotenv

load_dotenv()


def parse_frontend_origins(raw_value: str | None) -> list[str]:
    if not raw_value:
        return [
            "http://localhost:3000",
            "http://localhost:5173",
            "http://localhost:4173",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:4173",
            "https://djbilal-frontend-production.up.railway.app",
        ]

    configured_value = raw_value.strip()
    if configured_value.startswith("[") and configured_value.endswith("]"):
        configured_value = configured_value[1:-1].strip()

    origins = [
        origin.strip().strip("\"'")
        for origin in configured_value.split(",")
        if origin.strip().strip("\"'")
    ]
    if not origins:
        raise RuntimeError("FRONTEND_ORIGINS is empty")

    markdown_link = re.compile(r"^\[(https?://[^\]]+)\]\((https?://[^)]+)\)$")
    normalized_origins: list[str] = []
    for origin in origins:
        match = markdown_link.fullmatch(origin)
        if match:
            label_url, target_url = match.groups()
            if label_url.rstrip("/") != target_url.rstrip("/"):
                raise RuntimeError(
                    "FRONTEND_ORIGINS Markdown links must have matching URL text "
                    "and destination"
                )
            origin = target_url
        normalized_origins.append(origin)

    if any("*" in origin for origin in normalized_origins):
        raise RuntimeError("FRONTEND_ORIGINS must not contain wildcard origins")

    exact_origins: list[str] = []
    for origin in normalized_origins:
        parsed = urlparse(origin)
        if (
            parsed.scheme
            and parsed.netloc
            and parsed.path in ("", "/")
            and not parsed.params
            and not parsed.query
            and not parsed.fragment
        ):
            origin = f"{parsed.scheme}://{parsed.netloc}"
        exact_origins.append(origin)

    if IS_PRODUCTION:
        for index, origin in enumerate(exact_origins, start=1):
            parsed = urlparse(origin)
            if (
                parsed.scheme != "https"
                or not parsed.netloc
                or parsed.path
                or parsed.params
                or parsed.query
                or parsed.fragment
            ):
                raise RuntimeError(
                    "Production FRONTEND_ORIGINS must be comma-separated exact "
                    "HTTPS origins (for example: https://djbilal.com), without "
                    "paths or wildcards. Check origin entry "
                    f"{index}; wrapper quotes, brackets, and Markdown links are "
                    "normalized automatically."
                )
    return exact_origins


IS_PRODUCTION = os.getenv("ENVIRONMENT", "development").lower() == "production"
_configured_frontend_origins = os.getenv("FRONTEND_ORIGINS")
if IS_PRODUCTION and not _configured_frontend_origins:
    raise RuntimeError("FRONTEND_ORIGINS must be configured in production")

FRONTEND_ORIGINS = parse_frontend_origins(_configured_frontend_origins)
LOCAL_DEV_ORIGIN_REGEX = (
    r"^https?://("
    r"(localhost|127\.0\.0\.1|0\.0\.0\.0)"
    r"|192\.168\.\d{1,3}\.\d{1,3}"
    r"|10\.\d{1,3}\.\d{1,3}\.\d{1,3}"
    r"|172\.(1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3}"
    r")(:\d+)?$"
)
