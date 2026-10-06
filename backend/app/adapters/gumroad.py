import os
from collections.abc import Mapping

import httpx
from fastapi import HTTPException, status


class GumroadService:
    """Verify Gumroad Ping notifications against Gumroad's sales API."""

    def __init__(self, *, timeout: float = 10.0) -> None:
        self.timeout = timeout

    @staticmethod
    def extract_checkout_data(form_data: Mapping[str, str]) -> dict[str, str]:
        """Read cart values from Gumroad URL parameters or custom fields."""
        checkout_data: dict[str, str] = {}
        accepted_keys = {"user_id", "track_ids", "track_id", "license_type"}

        for key, value in form_data.items():
            normalized_key = key.strip().lower()
            if normalized_key in accepted_keys:
                checkout_data[normalized_key] = value
                continue

            for prefix in ("url_params[", "custom_fields["):
                if normalized_key.startswith(prefix) and normalized_key.endswith("]"):
                    field_name = normalized_key[len(prefix):-1].strip().replace(" ", "_")
                    if field_name in accepted_keys:
                        checkout_data[field_name] = value
                    break

        return checkout_data

    async def verify_sale(self, ping: Mapping[str, str]) -> dict[str, str]:
        """Verify seller, product, paid amount, and sale state with Gumroad."""
        access_token = os.getenv("GUMROAD_ACCESS_TOKEN", "").strip()
        configured_seller_id = os.getenv("GUMROAD_SELLER_ID", "").strip()
        configured_product_id = os.getenv("GUMROAD_PRODUCT_ID", "").strip()
        expected_currency = os.getenv("GUMROAD_CURRENCY", "usd").strip().lower()
        if not access_token or not configured_seller_id or not configured_product_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Gumroad verification is not configured",
            )

        sale_id = ping.get("sale_id", "").strip()
        reported_seller_id = ping.get("seller_id", "").strip()
        reported_product_id = ping.get("product_id", "").strip()
        reported_price = self._parse_cents(ping.get("price"))
        reported_currency = ping.get("currency", "").strip().lower()

        if (
            not sale_id
            or reported_seller_id != configured_seller_id
            or reported_product_id != configured_product_id
            or reported_price is None
            or reported_currency != expected_currency
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
                    f"https://api.gumroad.com/v2/sales/{sale_id}",
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
        api_currency = sale.get("currency")
        if (
            api_sale_id != sale_id
            or (
                api_seller_id is not None
                and self._identifier(api_seller_id) != configured_seller_id
            )
            or self._identifier(sale.get("product_id")) != configured_product_id
            or self._parse_cents(sale.get("price")) != reported_price
            or (
                api_currency is not None
                and (
                    not isinstance(api_currency, str)
                    or api_currency.lower() != expected_currency
                )
            )
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
            "price": str(reported_price),
            "currency": expected_currency,
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
