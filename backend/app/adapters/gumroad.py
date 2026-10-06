import os
import hashlib
import hmac
import json
from collections.abc import Mapping
from urllib.parse import parse_qsl, quote, urlparse

import httpx
from fastapi import HTTPException, status


class GumroadService:
    """Verify Gumroad Ping notifications against Gumroad's sales API."""

    def __init__(self, *, timeout: float = 10.0) -> None:
        self.timeout = timeout

    @staticmethod
    def normalize_product_permalink(value: str) -> str | None:
        """Normalize an absolute Gumroad product URL or Gumroad permalink."""
        candidate = value.strip()
        parsed = urlparse(candidate if "://" in candidate else f"https://gumroad.com/l/{candidate.lstrip('/')}")
        hostname = (parsed.hostname or "").lower()
        if (
            parsed.scheme != "https"
            or not hostname
            or not (hostname == "gumroad.com" or hostname.endswith(".gumroad.com"))
            or parsed.query
            or parsed.fragment
        ):
            return None
        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) != 2 or parts[0] != "l":
            return None
        return parts[1].casefold()

    @staticmethod
    def checkout_signature(user_id: int, track_id: int, product_permalink: str) -> str:
        from ..auth import SECRET_KEY

        message = f"{user_id}:{track_id}:{product_permalink}".encode("utf-8")
        return hmac.new(SECRET_KEY.encode("utf-8"), message, hashlib.sha256).hexdigest()

    @classmethod
    def verify_checkout_signature(
        cls,
        *,
        user_id: int,
        track_id: int,
        product_permalink: str,
        signature: str,
    ) -> bool:
        expected = cls.checkout_signature(user_id, track_id, product_permalink)
        return hmac.compare_digest(signature, expected)

    @staticmethod
    def extract_checkout_data(form_data: Mapping[str, str]) -> dict[str, str]:
        """Read cart values from Gumroad URL parameters or custom fields."""
        checkout_data: dict[str, str] = {}
        accepted_keys = {"user_id", "track_ids", "signature", "license_type"}

        for key, value in form_data.items():
            normalized_key = key.strip().lower()
            if normalized_key in accepted_keys:
                checkout_data[normalized_key] = value
                continue

            if normalized_key in {"url_params", "custom_fields"}:
                try:
                    nested_values = json.loads(value)
                except json.JSONDecodeError:
                    nested_values = dict(parse_qsl(value, keep_blank_values=True))
                if isinstance(nested_values, dict):
                    for nested_key, nested_value in nested_values.items():
                        normalized_nested_key = str(nested_key).strip().lower()
                        if (
                            normalized_nested_key in accepted_keys
                            and isinstance(nested_value, (str, int))
                        ):
                            checkout_data[normalized_nested_key] = str(nested_value)
                continue

            for prefix in ("url_params[", "custom_fields["):
                if normalized_key.startswith(prefix) and normalized_key.endswith("]"):
                    field_name = normalized_key[len(prefix):-1].strip().replace(" ", "_")
                    if field_name in accepted_keys:
                        checkout_data[field_name] = value
                    break

        return checkout_data

    async def verify_sale(self, ping: Mapping[str, str]) -> dict[str, str]:
        """Verify the seller and sale identity with Gumroad's Sales API."""
        access_token = os.getenv("GUMROAD_ACCESS_TOKEN", "").strip()
        configured_seller_id = os.getenv("GUMROAD_SELLER_ID", "").strip()
        if not access_token or not configured_seller_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Gumroad verification is not configured",
            )

        sale_id = ping.get("sale_id", "").strip()
        reported_seller_id = ping.get("seller_id", "").strip()
        if (
            not sale_id
            or reported_seller_id != configured_seller_id
            or self._is_true(ping.get("refunded"))
            or self._is_true(ping.get("chargebacked"))
            or self._is_true(ping.get("test"))
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Gumroad Ping does not describe a valid paid sale",
            )

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"https://api.gumroad.com/v2/sales/{quote(sale_id, safe='')}",
                    params={"access_token": access_token},
                )
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Unable to verify the Gumroad sale",
            ) from exc

        if response.status_code != status.HTTP_200_OK:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Gumroad sale verification failed",
            )

        try:
            body = response.json()
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Gumroad returned an invalid sale response",
            ) from exc

        sale = body.get("sale") if isinstance(body, dict) else None
        if not isinstance(body, dict) or body.get("success") is not True or not isinstance(sale, dict):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Gumroad sale is not valid for this product or amount",
            )

        api_sale_id = self._identifier(sale.get("sale_id", sale.get("id", sale_id)))
        api_seller_id = sale.get("seller_id")
        permalink = sale.get("product_permalink")
        if (
            api_sale_id != sale_id
            or (
                api_seller_id is not None
                and self._identifier(api_seller_id) != configured_seller_id
            )
            or not isinstance(permalink, str)
            or self.normalize_product_permalink(permalink) is None
            or self._is_true(sale.get("refunded"))
            or self._is_true(sale.get("chargebacked"))
            or self._is_true(sale.get("disputed"))
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Gumroad sale is not valid for this product or amount",
            )

        return {
            "sale_id": sale_id,
            "product_permalink": permalink,
            "price": str(self._parse_cents(sale.get("price")) or 0),
        }

    @staticmethod
    def _parse_cents(value: object) -> int | None:
        if isinstance(value, bool):
            return None
        if isinstance(value, int):
            parsed = value
        elif isinstance(value, float) and value.is_integer():
            parsed = int(value)
        elif isinstance(value, str):
            try:
                parsed = int(value.strip())
            except ValueError:
                return None
        else:
            return None
        return parsed if parsed >= 0 else None

    @staticmethod
    def _is_true(value: object) -> bool:
        if isinstance(value, bool):
            return value
        return isinstance(value, str) and value.strip().lower() in {"1", "true", "yes"}

    @staticmethod
    def _identifier(value: object) -> str | None:
        if isinstance(value, bool):
            return None
        if isinstance(value, (str, int)):
            return str(value)
        return None
