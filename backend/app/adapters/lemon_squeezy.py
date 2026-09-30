import asyncio
import hashlib
import hmac
import os

import httpx
from fastapi import HTTPException, status

from ..interfaces.payment import BasePaymentGateway, WebhookEvent
from ..json_types import JSONObject, JSONValue, normalize_json_value
from ..utils import build_checkout_url


class LemonSqueezyService(BasePaymentGateway):
    """Lemon Squeezy checkout and webhook adapter."""

    def __init__(self, *, max_attempts: int = 3, retry_delay: float = 0.1) -> None:
        self.max_attempts = max_attempts
        self.retry_delay = retry_delay

    async def create_checkout_session(
        self,
        *,
        variant_quantities: list[dict[str, int]],
        custom_data: dict[str, str],
        email: str | None = None,
        custom_price: int | None = None,
        fallback_url: str | None = None,
    ) -> str:
        api_key = os.getenv("LEMON_SQUEEZY_API_KEY", "").strip()
        store_id = os.getenv("LEMON_SQUEEZY_STORE_ID", "").strip()
        if not api_key or not store_id:
            if fallback_url:
                return build_checkout_url(fallback_url, custom_data, email)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Lemon Squeezy API credentials are missing",
            )

        if not variant_quantities:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="variant_quantities cannot be empty",
            )

        checkout_data: JSONObject = {"custom": custom_data}
        if email:
            checkout_data["email"] = email

        attributes: JSONObject = {"checkout_data": checkout_data}
        if custom_price is not None:
            attributes["custom_price"] = int(custom_price)

        relationships: JSONObject = {
            "store": {"data": {"type": "stores", "id": str(store_id)}},
            "variant": {
                "data": {
                    "type": "variants",
                    "id": str(variant_quantities[0]["variant_id"]),
                }
            },
        }
        headers = {
            "Accept": "application/vnd.api+json",
            "Content-Type": "application/vnd.api+json",
            "Authorization": f"Bearer {api_key}",
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            for attempt in range(self.max_attempts):
                payload = {
                    "data": {
                        "type": "checkouts",
                        "attributes": attributes,
                        "relationships": dict(relationships),
                    }
                }
                try:
                    response = await client.post(
                        "https://api.lemonsqueezy.com/v1/checkouts",
                        headers=headers,
                        json=payload,
                    )
                except httpx.HTTPError as exc:
                    if attempt + 1 < self.max_attempts:
                        await asyncio.sleep(self.retry_delay * (2 ** attempt))
                        continue
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail=f"Lemon Squeezy request failed: {exc}",
                    ) from exc

                if response.status_code >= 500 or response.status_code == 429:
                    if attempt + 1 < self.max_attempts:
                        await asyncio.sleep(self.retry_delay * (2 ** attempt))
                        continue

                if response.status_code >= 400:
                    error_detail = self._response_error(response)
                    if (
                        "variant" in relationships
                        and self._is_variant_relationship_error(error_detail)
                    ):
                        relationships.pop("variant")
                        continue
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail={
                            "message": "Lemon Squeezy checkout creation failed",
                            "provider_error": error_detail,
                        },
                    )

                body = self._response_json(response)
                data = body.get("data")
                attributes_value = data.get("attributes") if isinstance(data, dict) else None
                attributes_object = (
                    attributes_value if isinstance(attributes_value, dict) else {}
                )
                checkout_url = attributes_object.get("url") or attributes_object.get("checkout_url")
                if isinstance(checkout_url, str) and checkout_url:
                    return checkout_url
                if fallback_url:
                    return build_checkout_url(fallback_url, custom_data, email)
                if attempt + 1 < self.max_attempts:
                    await asyncio.sleep(self.retry_delay * (2 ** attempt))
                    continue
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Lemon Squeezy response did not include checkout URL",
                )

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Lemon Squeezy checkout could not be created",
        )

    def verify_webhook(self, raw_body: bytes, signature: str | None) -> bool:
        secret = os.getenv("LEMON_SQUEEZY_WEBHOOK_SECRET", "").strip()
        if not secret or not signature:
            return False
        expected = hmac.new(
            secret.encode("utf-8"),
            raw_body,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(signature, expected)

    def handle_webhook_event(self, payload: JSONObject) -> WebhookEvent:
        return {
            "successful": self.is_successful_payment_event(payload),
            "custom_data": self.extract_custom_data(payload),
        }

    @classmethod
    def extract_custom_data(cls, payload: JSONObject) -> dict[str, str]:
        for key in ("custom_data", "custom", "checkout_data"):
            nested = cls._extract_nested_dict(payload, key)
            if nested:
                return {str(k): str(v) for k, v in nested.items() if v is not None}
        return {}

    @classmethod
    def is_successful_payment_event(cls, payload: JSONObject) -> bool:
        meta = cls._object_value(payload.get("meta"))
        data = cls._object_value(payload.get("data"))
        attributes = cls._object_value(data.get("attributes")) if data else {}
        event_name = cls._first_string(
            meta.get("event_name") if meta else None,
            meta.get("name") if meta else None,
            payload.get("event_name"),
            payload.get("type"),
        ).lower()
        status_value = cls._first_string(
            attributes.get("status") if attributes else None,
            attributes.get("status_formatted") if attributes else None,
            meta.get("status") if meta else None,
        ).lower()

        if any(token in event_name for token in ("order", "payment", "license")):
            return "fail" not in event_name and status_value not in (
                "failed", "canceled", "cancelled", "unpaid"
            )
        return status_value in ("paid", "succeeded", "successful", "completed")

    @classmethod
    def _extract_nested_dict(cls, payload: JSONValue, target_key: str) -> JSONObject | None:
        if not isinstance(payload, dict):
            return None
        if target_key in payload and isinstance(payload[target_key], dict):
            return payload[target_key]
        for value in payload.values():
            if isinstance(value, dict):
                nested = cls._extract_nested_dict(value, target_key)
                if nested is not None:
                    return nested
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        nested = cls._extract_nested_dict(item, target_key)
                        if nested is not None:
                            return nested
        return None

    @staticmethod
    def _response_json(response: httpx.Response) -> JSONObject:
        value = normalize_json_value(response.json())
        if not isinstance(value, dict):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Lemon Squeezy returned an invalid JSON response",
            )
        return value

    @staticmethod
    def _response_error(response: httpx.Response) -> JSONValue | str:
        try:
            return normalize_json_value(response.json())
        except ValueError:
            return response.text

    @staticmethod
    def _is_variant_relationship_error(error_detail: JSONValue | str) -> bool:
        import json

        error_text = (
            error_detail
            if isinstance(error_detail, str)
            else json.dumps(error_detail).lower()
        )
        return "variant" in error_text.lower() and (
            "relationship" in error_text.lower()
            or "invalid" in error_text.lower()
        )

    @staticmethod
    def _object_value(value: JSONValue | None) -> JSONObject | None:
        return value if isinstance(value, dict) else None

    @staticmethod
    def _first_string(*values: JSONValue | None) -> str:
        for value in values:
            if isinstance(value, str) and value:
                return value
        return ""
