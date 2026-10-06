import pytest
from fastapi import HTTPException

from app.adapters.gumroad import GumroadService


def test_extract_checkout_data_reads_ping_form_field_groups():
    data = GumroadService.extract_checkout_data(
        {
            "url_params[user_id]": "12",
            "url_params[track_ids]": "3,4",
            "custom_fields[license_type]": "Standard",
            "sale_id": "sale-1",
        }
    )

    assert data == {
        "user_id": "12",
        "track_ids": "3,4",
        "license_type": "Standard",
    }


@pytest.mark.asyncio
async def test_verify_sale_checks_gumroad_api_record(monkeypatch):
    monkeypatch.setenv("GUMROAD_ACCESS_TOKEN", "api-token")
    monkeypatch.setenv("GUMROAD_SELLER_ID", "seller-1")
    monkeypatch.setenv("GUMROAD_PRODUCT_ID", "product-1")
    request_arguments = {}

    class FakeResponse:
        status_code = 200

        def json(self):
            return {
                "success": True,
                "sale": {
                    "sale_id": "sale-1",
                    "product_id": "product-1",
                    "price": 500,
                    "refunded": False,
                },
            }

    class FakeAsyncClient:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url, params):
            request_arguments.update(url=url, params=params)
            return FakeResponse()

    monkeypatch.setattr("app.adapters.gumroad.httpx.AsyncClient", FakeAsyncClient)

    result = await GumroadService().verify_sale(
        {
            "sale_id": "sale-1",
            "seller_id": "seller-1",
            "product_id": "product-1",
            "price": "500",
            "currency": "usd",
        }
    )

    assert result == {"sale_id": "sale-1", "price": "500", "currency": "usd"}
    assert request_arguments["url"] == "https://api.gumroad.com/v2/sales/sale-1"
    assert request_arguments["params"] == {"access_token": "api-token"}


@pytest.mark.asyncio
async def test_verify_sale_rejects_wrong_seller_before_api_call(monkeypatch):
    monkeypatch.setenv("GUMROAD_ACCESS_TOKEN", "api-token")
    monkeypatch.setenv("GUMROAD_SELLER_ID", "seller-1")
    monkeypatch.setenv("GUMROAD_PRODUCT_ID", "product-1")

    async def unexpected_request(*args, **kwargs):
        raise AssertionError("Gumroad API must not be called for another seller")

    monkeypatch.setattr(
        "app.adapters.gumroad.httpx.AsyncClient.get",
        unexpected_request,
    )

    with pytest.raises(HTTPException) as exc_info:
        await GumroadService().verify_sale(
            {
                "sale_id": "sale-1",
                "seller_id": "attacker",
                "product_id": "product-1",
                "price": "500",
                "currency": "usd",
            }
        )

    assert exc_info.value.status_code == 400
