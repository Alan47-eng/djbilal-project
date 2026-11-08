import base64
import asyncio
import hashlib
import hmac
from datetime import datetime, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app import auth
from app.database import get_session
from app.main import app
from app.models import Base, Order, Purchase, Track, User
from app.routers.shopier import ShopierCheckoutResponse
from app.shopier import callback_signature, checkout_signature


TEST_SECRET = "shopier-test-secret"
CHECKOUT = {
    "track_ids": [1, 2],
    "current_language": "en",
}


@pytest.fixture
async def shopier_client(monkeypatch):
    previous_session_override = app.dependency_overrides.get(get_session)
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        engine, expire_on_commit=False
    )

    async def override_session():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    monkeypatch.setenv("SHOPIER_API_KEY", "shopier-test-key")
    monkeypatch.setenv("SHOPIER_API_SECRET", TEST_SECRET)

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
                ),
                Track(
                    title="Second Track",
                    artist="DJ Bilal",
                    price=3.50,
                    preview_url="https://example.com/preview-2.mp3",
                    full_file_path="tracks/second.mp3",
                    is_free=False,
                    category="edit",
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


async def create_order(client: AsyncClient) -> ShopierCheckoutResponse:
    response = await client.post("/api/v1/checkout/shopier/init", json=CHECKOUT)
    assert response.status_code == 200, response.text
    return ShopierCheckoutResponse.model_validate(response.json())


async def send_callback(
    client: AsyncClient,
    order_id: str,
    *,
    status_value: str = "success",
    payment_id: str = "payment-123",
    random_nr: str = "7654321",
    signature: str | None = None,
):
    return await client.post(
        "/api/v1/webhooks/shopier",
        data={
            "status": status_value,
            "platform_order_id": order_id,
            "payment_id": payment_id,
            "random_nr": random_nr,
            "signature": signature
            or callback_signature(TEST_SECRET, random_nr, order_id),
        },
    )


@pytest.mark.asyncio
async def test_checkout_creates_pending_order_and_signed_form(shopier_client, monkeypatch):
    client, session_factory = shopier_client
    monkeypatch.setenv("SHOPIER_CURRENCY", "0")
    checkout = await create_order(client)

    fields = checkout.fields
    assert checkout.action_url == "https://www.shopier.com/ShowProduct/api_pay4.php"
    assert checkout.method == "POST"
    assert fields["total_order_value"] == "7.75"
    assert fields["currency"] == "1"
    assert fields["buyer_email"] == "shopier-test@example.com"
    assert fields["buyer_name"] == "Test"
    assert fields["buyer_surname"] == "Customer"
    assert fields["buyer_id_nr"] == "11111111111"
    assert fields["buyer_phone"] == "0000000000"
    assert fields["billing_address"] == "Digital Delivery"
    assert fields["shipping_address"] == "Digital Delivery"
    assert fields["billing_city"] == "Istanbul"
    assert fields["billing_country"] == "Turkey"
    assert fields["billing_postcode"] == "34000"
    assert fields["signature"] == checkout_signature(
        TEST_SECRET,
        fields["random_nr"],
        checkout.order_id,
        "7.75",
        1,
    )

    async with session_factory() as session:
        order = await session.scalar(
            select(Order).where(Order.platform_order_id == checkout.order_id)
        )
        assert order is not None
        assert order.status == "pending"
        assert order.total_amount_minor == 775
        assert order.currency == 1


@pytest.mark.asyncio
async def test_successful_callback_delivers_tracks_once(shopier_client):
    client, session_factory = shopier_client
    checkout = await create_order(client)

    first = await send_callback(client, checkout.order_id)
    second = await send_callback(client, checkout.order_id)
    assert first.status_code == 200
    assert second.status_code == 200

    async with session_factory() as session:
        order = await session.scalar(
            select(Order).where(Order.platform_order_id == checkout.order_id)
        )
        purchase_count = await session.scalar(select(func.count()).select_from(Purchase))
        assert order is not None
        assert order.status == "success"
        assert order.shopier_payment_id == "payment-123"
        assert purchase_count == 2


@pytest.mark.asyncio
async def test_concurrent_duplicate_callbacks_are_idempotent(shopier_client):
    client, session_factory = shopier_client
    checkout = await create_order(client)

    responses = await asyncio.gather(
        send_callback(client, checkout.order_id),
        send_callback(client, checkout.order_id),
    )
    assert [response.status_code for response in responses] == [200, 200]

    async with session_factory() as session:
        order = await session.scalar(
            select(Order).where(Order.platform_order_id == checkout.order_id)
        )
        assert order is not None
        assert order.status == "success"
        assert await session.scalar(select(func.count()).select_from(Purchase)) == 2


@pytest.mark.asyncio
async def test_failed_callback_does_not_deliver_tracks(shopier_client):
    client, session_factory = shopier_client
    checkout = await create_order(client)

    response = await send_callback(
        client, checkout.order_id, status_value="fail"
    )
    assert response.status_code == 200

    async with session_factory() as session:
        order = await session.scalar(
            select(Order).where(Order.platform_order_id == checkout.order_id)
        )
        purchase_count = await session.scalar(select(func.count()).select_from(Purchase))
        assert order is not None
        assert order.status == "failed"
        assert purchase_count == 0


@pytest.mark.asyncio
async def test_invalid_callback_signature_is_rejected(shopier_client):
    client, session_factory = shopier_client
    checkout = await create_order(client)

    response = await send_callback(
        client, checkout.order_id, signature="invalid-signature"
    )
    assert response.status_code == 400

    async with session_factory() as session:
        order = await session.scalar(
            select(Order).where(Order.platform_order_id == checkout.order_id)
        )
        assert order is not None
        assert order.status == "pending"
        assert await session.scalar(select(func.count()).select_from(Purchase)) == 0


@pytest.mark.asyncio
async def test_delivery_failure_keeps_payment_pending_for_retry(
    shopier_client, monkeypatch
):
    client, session_factory = shopier_client
    checkout = await create_order(client)

    async def fail_delivery(_session, _order_id):
        raise RuntimeError("simulated purchase insert failure")

    with monkeypatch.context() as patch:
        patch.setattr("app.routers.shopier._deliver_order", fail_delivery)
        response = await send_callback(client, checkout.order_id)
        assert response.status_code == 500

    async with session_factory() as session:
        order = await session.scalar(
            select(Order).where(Order.platform_order_id == checkout.order_id)
        )
        assert order is not None
        assert order.status == "paid_pending_delivery"
        assert order.shopier_payment_id == "payment-123"
        assert await session.scalar(select(func.count()).select_from(Purchase)) == 0

    retry = await client.post(
        f"/api/v1/admin/shopier/orders/{checkout.order_id}/retry-delivery"
    )
    assert retry.status_code == 200
    assert retry.json()["status"] == "success"
    async with session_factory() as session:
        order = await session.scalar(
            select(Order).where(Order.platform_order_id == checkout.order_id)
        )
        assert order is not None
        assert order.status == "success"
        assert await session.scalar(select(func.count()).select_from(Purchase)) == 2


def test_shopier_signatures_match_php_hmac_base64_format():
    message = "7654321order-1237.751"
    expected = base64.b64encode(
        hmac.new(TEST_SECRET.encode(), message.encode(), hashlib.sha256).digest()
    ).decode()
    assert checkout_signature(
        TEST_SECRET, "7654321", "order-123", "7.75", 1
    ) == expected
