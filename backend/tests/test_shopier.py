import asyncio
import hashlib
import hmac
import json
from datetime import datetime, timezone

import httpx
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app import auth
from app.database import get_session
from app.main import app
from app.models import (
    Base,
    Order,
    Purchase,
    ShopierWebhookEvent,
    Track,
    User,
)
from app.shopier import _shopier_error_message


TEST_WEBHOOK_TOKEN = "shopier-test-webhook-token"
TEST_PRODUCT_IDS = ("shopier-product-1", "shopier-product-2")


def test_shopier_api_error_message_includes_validation_reason_and_redacts_token():
    response = httpx.Response(
        400,
        json={
            "message": "Invalid product payload",
            "errors": {"priceData": "Unsupported currency"},
        },
    )

    message = _shopier_error_message(response, "secret-access-token")

    assert "Invalid product payload" in message
    assert "Unsupported currency" in message
    assert "secret-access-token" not in message


@pytest.fixture
async def shopier_client(monkeypatch, tmp_path):
    previous_session_override = app.dependency_overrides.get(get_session)
    database_url = URL.create(
        "sqlite+aiosqlite", database=str(tmp_path / "shopier-test.db")
    )
    engine = create_async_engine(database_url)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_session():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    monkeypatch.setenv("SHOPIER_ACCESS_TOKEN", "shopier-test-access-token")
    monkeypatch.setenv("SHOPIER_WEBHOOK_TOKEN", TEST_WEBHOOK_TOKEN)
    monkeypatch.setenv(
        "SHOPIER_WEBHOOK_URL", "https://api.example.com/api/v1/webhooks/shopier"
    )

    async with session_factory() as session:
        user = User(
            email="shopier-test@example.com",
            full_name="Test Customer",
            hashed_password=auth.hash_password("Password123"),
            is_admin=True,
            created_at=datetime.now(timezone.utc),
        )
        session.add(user)
        await session.flush()
        session.add_all(
            [
                Track(
                    title="First Track",
                    artist="DJ Bilal",
                    price=4.25,
                    preview_url="https://example.com/preview-1.mp3",
                    full_file_path="tracks/first.mp3",
                    is_free=False,
                    category="edit",
                    shopier_product_id=TEST_PRODUCT_IDS[0],
                ),
                Track(
                    title="Second Track",
                    artist="DJ Bilal",
                    price=3.50,
                    preview_url="https://example.com/preview-2.mp3",
                    full_file_path="tracks/second.mp3",
                    is_free=False,
                    category="edit",
                    shopier_product_id=TEST_PRODUCT_IDS[1],
                ),
            ]
        )
        await session.commit()
        token = auth.create_access_token({"sub": user.email})

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        client.headers.update({"Authorization": f"Bearer {token}"})
        yield client, session_factory

    if previous_session_override is None:
        app.dependency_overrides.pop(get_session, None)
    else:
        app.dependency_overrides[get_session] = previous_session_override
    await engine.dispose()


def build_order_payload(**overrides):
    payload = {
        "id": "shopier-order-123",
        "status": "unfulfilled",
        "paymentStatus": "paid",
        "currency": "USD",
        "totals": {"subtotal": "7.75", "shipping": "0.00", "total": "7.75"},
        "shippingInfo": {"email": "shopier-test@example.com"},
        "lineItems": [
            {
                "productId": TEST_PRODUCT_IDS[0],
                "title": "First Track - DJ Bilal",
                "type": "digital",
            },
            {
                "productId": TEST_PRODUCT_IDS[1],
                "title": "Second Track - DJ Bilal",
                "type": "digital",
            },
        ],
    }
    payload.update(overrides)
    return payload


async def send_webhook(
    client: AsyncClient,
    payload: dict[str, object] | None = None,
    *,
    event_id: str = "webhook-event-123",
    signature: str | None = None,
):
    raw_body = json.dumps(
        payload or build_order_payload(), separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    expected_signature = hmac.new(
        TEST_WEBHOOK_TOKEN.encode("utf-8"), raw_body, hashlib.sha256
    ).hexdigest()
    return await client.post(
        "/api/v1/webhooks/shopier",
        content=raw_body,
        headers={
            "Content-Type": "application/json",
            "Shopier-Event": "order.created",
            "Shopier-Webhook-Id": event_id,
            "Shopier-Signature": signature or expected_signature,
        },
    )


@pytest.mark.asyncio
async def test_sync_creates_digital_usd_product_and_saves_shopier_url(
    shopier_client, monkeypatch
):
    client, session_factory = shopier_client
    api_calls = []
    async with session_factory() as session:
        track = await session.get(Track, 1)
        assert track is not None
        track.shopier_product_id = None
        await session.commit()

    async def fake_shopier_api_request(method, path, *, payload=None):
        api_calls.append((method, path, payload))
        return {
            "id": "shopier-product-created",
            "url": "https://www.shopier.com/123456",
        }

    monkeypatch.setattr(
        "app.routers.shopier.shopier_api_request", fake_shopier_api_request
    )
    response = await client.post("/api/v1/admin/shopier/tracks/1/sync")

    assert response.status_code == 200, response.text
    assert response.json() == {
        "product_id": "shopier-product-created",
        "product_url": "https://www.shopier.com/123456",
        "currency": "USD",
    }
    assert api_calls[0][0:2] == ("POST", "/products")
    assert api_calls[0][2]["type"] == "digital"
    assert api_calls[0][2]["priceData"] == {"currency": "USD", "price": "4.25"}
    assert api_calls[0][2]["media"] == []

    async with session_factory() as session:
        track = await session.get(Track, 1)
        assert track is not None
        assert track.shopier_product_id == "shopier-product-created"
        assert track.shopier_product_url == "https://www.shopier.com/123456"


@pytest.mark.asyncio
async def test_sync_updates_existing_product_and_rejects_bad_shopier_url(
    shopier_client, monkeypatch
):
    client, _ = shopier_client
    calls = []

    async def fake_shopier_api_request(method, path, *, payload=None):
        calls.append((method, path))
        return {"id": TEST_PRODUCT_IDS[0], "url": "https://attacker.example"}

    monkeypatch.setattr(
        "app.routers.shopier.shopier_api_request", fake_shopier_api_request
    )
    response = await client.post("/api/v1/admin/shopier/tracks/1/sync")

    assert calls == [("PUT", f"/products/{TEST_PRODUCT_IDS[0]}")]
    assert response.status_code == 502


@pytest.mark.asyncio
async def test_register_webhook_returns_token_for_server_configuration(
    shopier_client, monkeypatch
):
    client, _ = shopier_client
    calls = []

    async def fake_shopier_api_request(method, path, *, payload=None):
        calls.append((method, path, payload))
        return {"id": "hook-1", "token": "new-secret-token"}

    monkeypatch.setattr(
        "app.routers.shopier.shopier_api_request", fake_shopier_api_request
    )
    response = await client.post("/api/v1/admin/shopier/webhooks/order-created")

    assert response.status_code == 200
    assert calls == [
        (
            "POST",
            "/webhooks",
            {
                "event": "order.created",
                "url": "https://api.example.com/api/v1/webhooks/shopier",
            },
        )
    ]
    assert response.json()["webhook_token"] == "new-secret-token"


@pytest.mark.asyncio
async def test_signed_paid_order_delivers_all_tracks_once(shopier_client):
    client, session_factory = shopier_client
    first = await send_webhook(client)
    duplicate = await send_webhook(client)

    assert first.status_code == 200, first.text
    assert duplicate.status_code == 200, duplicate.text

    async with session_factory() as session:
        order = await session.scalar(
            select(Order).where(Order.platform_order_id == "shopier-order-123")
        )
        assert order is not None
        assert order.status == "success"
        assert order.total_amount_minor == 775
        assert order.currency == 1
        assert await session.scalar(select(func.count()).select_from(Purchase)) == 2
        assert (
            await session.scalar(
                select(func.count()).select_from(ShopierWebhookEvent)
            )
            == 1
        )


@pytest.mark.asyncio
async def test_invalid_signature_is_rejected_without_recording_order(shopier_client):
    client, session_factory = shopier_client
    response = await send_webhook(client, signature="invalid")

    assert response.status_code == 400
    async with session_factory() as session:
        assert await session.scalar(select(func.count()).select_from(Order)) == 0
        assert await session.scalar(select(func.count()).select_from(Purchase)) == 0


@pytest.mark.asyncio
async def test_unpaid_order_is_not_delivered(shopier_client):
    client, session_factory = shopier_client
    response = await send_webhook(
        client, build_order_payload(paymentStatus="unpaid")
    )

    assert response.status_code == 200
    async with session_factory() as session:
        assert await session.scalar(select(func.count()).select_from(Order)) == 0
        assert await session.scalar(select(func.count()).select_from(Purchase)) == 0


@pytest.mark.asyncio
async def test_non_usd_order_is_rejected(shopier_client):
    client, session_factory = shopier_client
    response = await send_webhook(client, build_order_payload(currency="TRY"))

    assert response.status_code == 400
    async with session_factory() as session:
        assert await session.scalar(select(func.count()).select_from(Order)) == 0


@pytest.mark.asyncio
async def test_unknown_buyer_email_is_retried_and_not_delivered(shopier_client):
    client, session_factory = shopier_client
    response = await send_webhook(
        client,
        build_order_payload(
            shippingInfo={"email": "not-registered@example.com"}
        ),
    )

    assert response.status_code == 503
    async with session_factory() as session:
        assert await session.scalar(select(func.count()).select_from(Order)) == 0
        assert await session.scalar(select(func.count()).select_from(Purchase)) == 0


@pytest.mark.asyncio
async def test_delivery_failure_keeps_paid_order_retryable(
    shopier_client, monkeypatch
):
    client, session_factory = shopier_client

    async def fail_delivery(_session, _order_id):
        raise RuntimeError("simulated purchase insert failure")

    with monkeypatch.context() as patch:
        patch.setattr("app.routers.shopier._deliver_order", fail_delivery)
        response = await send_webhook(client)
        assert response.status_code == 500

    async with session_factory() as session:
        order = await session.scalar(
            select(Order).where(Order.platform_order_id == "shopier-order-123")
        )
        assert order is not None
        assert order.status == "paid_pending_delivery"
        assert await session.scalar(select(func.count()).select_from(Purchase)) == 0

    retry = await client.post(
        "/api/v1/admin/shopier/orders/shopier-order-123/retry-delivery"
    )
    assert retry.status_code == 200
    async with session_factory() as session:
        order = await session.scalar(
            select(Order).where(Order.platform_order_id == "shopier-order-123")
        )
        assert order is not None
        assert order.status == "success"
        assert await session.scalar(select(func.count()).select_from(Purchase)) == 2


@pytest.mark.asyncio
async def test_concurrent_duplicate_webhooks_are_idempotent(shopier_client):
    client, session_factory = shopier_client
    responses = await asyncio.gather(
        send_webhook(client), send_webhook(client)
    )

    assert [response.status_code for response in responses] == [200, 200], [
        response.text for response in responses
    ]
    async with session_factory() as session:
        order = await session.scalar(
            select(Order).where(Order.platform_order_id == "shopier-order-123")
        )
        assert order is not None
        assert order.status == "success"
        assert await session.scalar(select(func.count()).select_from(Purchase)) == 2
