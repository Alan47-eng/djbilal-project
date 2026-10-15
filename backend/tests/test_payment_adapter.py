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


def test_extract_checkout_data_reads_json_url_params():
    data = GumroadService.extract_checkout_data(
        {
            "url_params": '{"user_id":"12","track_ids":"3","signature":"signed"}',
            "custom_fields": '{"license_type":"Standard"}',
        }
    )

    assert data == {
        "user_id": "12",
        "track_ids": "3",
        "signature": "signed",
        "license_type": "Standard",
    }


@pytest.mark.parametrize(
    ("payload", "reason"),
    [
        ({}, "notification has no sale_id"),
        ({"sale_id": "sale-1", "test": "true"}, "test notification"),
        (
            {"sale_id": "sale-1", "refunded": "true"},
            "refund or dispute notification",
        ),
    ],
)
def test_ignored_ping_reason_for_non_sale_notifications(payload, reason):
    assert GumroadService.ignored_ping_reason(payload) == reason


def test_ignored_ping_reason_for_unconfigured_seller(monkeypatch):
    monkeypatch.setenv("GUMROAD_SELLER_ID", "seller-1")

    assert GumroadService.ignored_ping_reason(
        {"sale_id": "sale-1", "seller_id": "test-seller"}
    ) == "seller_id does not match configured Gumroad seller"


@pytest.mark.asyncio
async def test_verify_sale_checks_gumroad_api_record(monkeypatch):
    monkeypatch.setenv("GUMROAD_ACCESS_TOKEN", "api-token")
    monkeypatch.setenv("GUMROAD_SELLER_ID", "seller-1")
    request_arguments = {}

    class FakeResponse:
        status_code = 200

        def json(self):
            return {
                "success": True,
                "sale": {
                    "sale_id": "sale-1",
                    "product_permalink": "https://gumroad.com/l/product-1",
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
        }
    )

    assert result == {
        "sale_id": "sale-1",
        "price": "500",
        "product_permalink": "https://gumroad.com/l/product-1",
    }
    assert request_arguments["url"] == "https://api.gumroad.com/v2/sales/sale-1"
    assert request_arguments["params"] == {"access_token": "api-token"}


@pytest.mark.asyncio
async def test_verify_sale_rejects_wrong_seller_before_api_call(monkeypatch):
    monkeypatch.setenv("GUMROAD_ACCESS_TOKEN", "api-token")
    monkeypatch.setenv("GUMROAD_SELLER_ID", "seller-1")

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
            }
        )

    assert exc_info.value.status_code == 400
