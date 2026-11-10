from __future__ import annotations

import hashlib
import hmac
import os
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from urllib.parse import urlparse

import httpx
from fastapi import HTTPException, status

SHOPIER_API_BASE_URL = "https://api.shopier.com/v1"
SHOPIER_CURRENCY = "USD"
CENT = Decimal("0.01")


class ShopierAPIError(RuntimeError):
    pass


def _shopier_error_message(response: httpx.Response, access_token: str) -> str:
    try:
        body = response.json()
    except ValueError:
        body = None

    details: list[str] = []
    if isinstance(body, dict):
        for key in ("message", "error", "errors", "detail"):
            value = body.get(key)
            if isinstance(value, str):
                details.append(value)
            elif isinstance(value, (dict, list)):
                details.append(str(value))

    message = "; ".join(details) or "No error details provided"
    message = message.replace(access_token, "[redacted]")
    return message[:500]


def shopier_access_token() -> str:
    token = os.getenv("SHOPIER_ACCESS_TOKEN", "").strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Shopier API access token is not configured",
        )
    return token


def shopier_webhook_token() -> str:
    token = os.getenv("SHOPIER_WEBHOOK_TOKEN", "").strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Shopier webhook token is not configured",
        )
    return token


def price_to_minor_units(value: float) -> int:
    try:
        price = Decimal(str(value))
        rounded = price.quantize(CENT, rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Track has an invalid price",
        ) from exc
    if not price.is_finite() or price <= 0 or price != rounded:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Track price must be positive and have at most two decimal places",
        )
    return int(rounded * 100)


def money_to_minor_units(value: str) -> int:
    try:
        amount = Decimal(value)
        rounded = amount.quantize(CENT, rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("Invalid Shopier order amount") from exc
    if not amount.is_finite() or amount <= 0 or amount != rounded:
        raise ValueError("Invalid Shopier order amount")
    return int(rounded * 100)


def money_string(amount_minor: int) -> str:
    return f"{Decimal(amount_minor) / 100:.2f}"


def shopier_product_url(value: object) -> str:
    if not isinstance(value, str):
        raise ShopierAPIError("Shopier did not return a product URL")
    parsed = urlparse(value)
    if parsed.scheme != "https" or parsed.hostname != "www.shopier.com":
        raise ShopierAPIError("Shopier returned an invalid product URL")
    return value


async def shopier_api_request(
    method: str,
    path: str,
    *,
    payload: dict[str, object] | None = None,
) -> dict[str, object] | list[object]:
    token = shopier_access_token()
    try:
        async with httpx.AsyncClient(
            base_url=SHOPIER_API_BASE_URL,
            timeout=httpx.Timeout(10.0, connect=5.0),
        ) as client:
            response = await client.request(
                method,
                path,
                json=payload,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json",
                },
            )
            response.raise_for_status()
            body = response.json()
    except httpx.HTTPStatusError as exc:
        raise ShopierAPIError(
            f"Shopier API returned HTTP {exc.response.status_code}: "
            f"{_shopier_error_message(exc.response, token)}"
        ) from exc
    except (httpx.RequestError, ValueError) as exc:
        raise ShopierAPIError("Shopier API request failed") from exc

    if not isinstance(body, (dict, list)):
        raise ShopierAPIError("Shopier API returned an invalid response")
    return body


def verify_webhook_signature(
    webhook_token: str, raw_body: bytes, provided_signature: str
) -> bool:
    if not provided_signature:
        return False
    expected = hmac.new(
        webhook_token.encode("utf-8"), raw_body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, provided_signature.strip().lower())
