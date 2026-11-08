from __future__ import annotations

import logging
import os
import secrets
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from uuid import uuid4

from fastapi import APIRouter, Depends, Form, HTTPException, Response, status
from pydantic import Field
from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from .. import auth, schemas
from ..database import get_session
from ..models import Order, OrderItem, Purchase, Track, User
from ..shopier import checkout_signature, verify_callback_signature
from .dependencies import require_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["shopier"])
SHOPIER_FORM_URL = "https://www.shopier.com/ShowProduct/api_pay4.php"
SHOPIER_CURRENCY_NAMES = {0: "TRY", 1: "USD", 2: "EUR"}
CENT = Decimal("0.01")


class ShopierCheckoutRequest(schemas.DTO):
    track_ids: list[int] = Field(min_length=1, max_length=50)
    buyer_name: str = Field(min_length=1, max_length=100)
    buyer_surname: str = Field(min_length=1, max_length=100)
    buyer_id_nr: str = Field(min_length=1, max_length=32)
    buyer_phone: str = Field(min_length=5, max_length=32)
    billing_address: str = Field(min_length=1, max_length=500)
    billing_city: str = Field(min_length=1, max_length=100)
    billing_country: str = Field(min_length=2, max_length=100)
    billing_postcode: str = Field(min_length=1, max_length=20)
    shipping_address: str = Field(min_length=1, max_length=500)
    shipping_city: str = Field(min_length=1, max_length=100)
    shipping_country: str = Field(min_length=2, max_length=100)
    shipping_postcode: str = Field(min_length=1, max_length=20)
    current_language: str = Field(default="en", pattern="^(en|tr)$")


class ShopierCheckoutResponse(schemas.DTO):
    order_id: str
    action_url: str
    method: str
    fields: dict[str, str]


def _shopier_settings() -> tuple[str, str, int]:
    api_key = os.getenv("SHOPIER_API_KEY", "").strip()
    api_secret = os.getenv("SHOPIER_API_SECRET", "").strip()
    raw_currency = os.getenv("SHOPIER_CURRENCY", "")
    if not api_key or not api_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Shopier checkout is not configured",
        )
    try:
        currency = int(raw_currency)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SHOPIER_CURRENCY must be set to 0, 1, or 2",
        ) from exc
    if currency not in SHOPIER_CURRENCY_NAMES:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SHOPIER_CURRENCY must be set to 0, 1, or 2",
        )
    return api_key, api_secret, currency


def _price_to_minor_units(value: float) -> int:
    try:
        price = Decimal(str(value))
        rounded = price.quantize(CENT, rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A track has an invalid price",
        ) from exc
    if not price.is_finite() or price <= 0 or price != rounded:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Track prices must be positive and have at most two decimal places",
        )
    return int(rounded * 100)


def _money_string(amount_minor: int) -> str:
    return f"{Decimal(amount_minor) / 100:.2f}"


def _account_age_days(user: User) -> int:
    created_at = user.created_at or datetime.now(timezone.utc)
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    return max(0, (datetime.now(timezone.utc) - created_at).days)


@router.post(
    "/checkout/shopier/init",
    response_model=ShopierCheckoutResponse,
    status_code=status.HTTP_200_OK,
)
async def initiate_shopier_checkout(
    checkout: ShopierCheckoutRequest,
    current_user: User = Depends(auth.get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ShopierCheckoutResponse:
    api_key, api_secret, currency = _shopier_settings()
    if len(set(checkout.track_ids)) != len(checkout.track_ids):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A track may only appear once in an order",
        )

    track_result = await session.execute(
        select(Track).where(Track.id.in_(checkout.track_ids))
    )
    tracks_by_id = {track.id: track for track in track_result.scalars().all()}
    if set(tracks_by_id) != set(checkout.track_ids):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or more tracks were not found",
        )
    if any(track.is_free for track in tracks_by_id.values()):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Free tracks cannot be purchased",
        )

    owned_result = await session.execute(
        select(Purchase.track_id).where(
            Purchase.user_id == current_user.id,
            Purchase.track_id.in_(checkout.track_ids),
        )
    )
    if owned_result.scalars().first() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Your library already contains one or more selected tracks",
        )

    ordered_tracks = [tracks_by_id[track_id] for track_id in checkout.track_ids]
    items = [
        (track, _price_to_minor_units(track.price)) for track in ordered_tracks
    ]
    total_amount_minor = sum(price_minor for _, price_minor in items)
    total_order_value = _money_string(total_amount_minor)
    platform_order_id = str(uuid4())
    random_nr = str(100_000 + secrets.randbelow(900_000))

    order = Order(
        user_id=current_user.id,
        platform_order_id=platform_order_id,
        total_amount_minor=total_amount_minor,
        currency=currency,
        status="pending",
    )
    session.add(order)
    await session.flush()
    session.add_all(
        [
            OrderItem(
                order_id=order.id,
                track_id=track.id,
                track_title=track.title,
                price_minor=price_minor,
            )
            for track, price_minor in items
        ]
    )

    signature = checkout_signature(
        api_secret,
        random_nr,
        platform_order_id,
        total_order_value,
        currency,
    )
    fields = {
        "API_key": api_key,
        "website_index": "1",
        "platform_order_id": platform_order_id,
        "product_name": f"DJ Bilal - {len(items)} digital track(s)",
        "product_type": "2",
        "buyer_name": checkout.buyer_name.strip(),
        "buyer_surname": checkout.buyer_surname.strip(),
        "buyer_email": current_user.email,
        "buyer_account_age": str(_account_age_days(current_user)),
        "buyer_id_nr": checkout.buyer_id_nr.strip(),
        "buyer_phone": checkout.buyer_phone.strip(),
        "billing_address": checkout.billing_address.strip(),
        "billing_city": checkout.billing_city.strip(),
        "billing_country": checkout.billing_country.strip(),
        "billing_postcode": checkout.billing_postcode.strip(),
        "shipping_address": checkout.shipping_address.strip(),
        "shipping_city": checkout.shipping_city.strip(),
        "shipping_country": checkout.shipping_country.strip(),
        "shipping_postcode": checkout.shipping_postcode.strip(),
        "total_order_value": total_order_value,
        "currency": str(currency),
        "platform": "0",
        "is_in_frame": "0",
        "current_language": checkout.current_language,
        "modul_version": "1.0.4",
        "random_nr": random_nr,
        "signature": signature,
    }
    await session.commit()
    return ShopierCheckoutResponse(
        order_id=platform_order_id,
        action_url=SHOPIER_FORM_URL,
        method="POST",
        fields=fields,
    )


async def _deliver_order(session: AsyncSession, platform_order_id: str) -> None:
    async with session.begin():
        order_result = await session.execute(
            select(Order)
            .where(Order.platform_order_id == platform_order_id)
            .with_for_update()
        )
        order = order_result.scalar_one_or_none()
        if order is None or order.status == "success":
            return
        if order.status != "paid_pending_delivery":
            return

        item_result = await session.execute(
            select(OrderItem).where(OrderItem.order_id == order.id)
        )
        items = item_result.scalars().all()
        if not items:
            raise RuntimeError("A paid order has no order items")
        values = [
            {"user_id": order.user_id, "track_id": item.track_id}
            for item in items
        ]
        dialect_name = session.get_bind().dialect.name
        if dialect_name == "postgresql":
            insert_statement = postgresql_insert(Purchase).values(values)
        elif dialect_name == "sqlite":
            insert_statement = sqlite_insert(Purchase).values(values)
        else:
            raise RuntimeError(
                f"Idempotent purchase insertion is unsupported for {dialect_name}"
            )
        await session.execute(
            insert_statement.on_conflict_do_nothing(
                index_elements=[Purchase.user_id, Purchase.track_id]
            )
        )
        order.status = "success"
        order.delivered_at = func.now()


@router.post("/webhooks/shopier", response_class=Response)
async def shopier_webhook(
    status_value: str = Form(..., alias="status"),
    platform_order_id: str = Form(...),
    payment_id: str = Form(...),
    random_nr: str = Form(...),
    signature: str = Form(...),
    session: AsyncSession = Depends(get_session),
) -> Response:
    api_secret = os.getenv("SHOPIER_API_SECRET", "").strip()
    if not api_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Shopier webhook is not configured",
        )
    if not verify_callback_signature(
        api_secret, random_nr, platform_order_id, signature
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Shopier callback signature",
        )

    order_result = await session.execute(
        select(Order).where(Order.platform_order_id == platform_order_id)
    )
    order = order_result.scalar_one_or_none()
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shopier order not found",
        )
    if order.status == "success" or order.status == "failed":
        return Response(status_code=status.HTTP_200_OK)

    if status_value not in {"success", "fail", "failed"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Shopier callback status",
        )
    if not payment_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Shopier callback is missing its payment ID",
        )

    if status_value != "success":
        await session.execute(
            update(Order)
            .where(
                Order.id == order.id,
                Order.status == "pending",
            )
            .values(status="failed")
        )
        await session.commit()
        return Response(status_code=status.HTTP_200_OK)

    if order.status == "pending":
        await session.execute(
            update(Order)
            .where(Order.id == order.id, Order.status == "pending")
            .values(
                status="paid_pending_delivery",
                shopier_payment_id=payment_id,
                paid_at=func.now(),
            )
        )
        await session.commit()
        await session.refresh(order)

    if (
        order.status == "paid_pending_delivery"
        and order.shopier_payment_id
        and order.shopier_payment_id != payment_id
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The Shopier payment ID does not match this order",
        )

    await session.commit()
    try:
        await _deliver_order(session, platform_order_id)
    except Exception as exc:
        logger.exception(
            "Shopier delivery failed for order %s; it remains pending delivery",
            platform_order_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Payment was recorded; track delivery will be retried",
        ) from exc
    return Response(status_code=status.HTTP_200_OK)


@router.post("/admin/shopier/orders/{platform_order_id}/retry-delivery")
async def retry_shopier_delivery(
    platform_order_id: str,
    current_user: User = Depends(auth.get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    require_admin(current_user)
    order_result = await session.execute(
        select(Order).where(Order.platform_order_id == platform_order_id)
    )
    order = order_result.scalar_one_or_none()
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shopier order not found",
        )
    if order.status == "success":
        return {"order_id": platform_order_id, "status": "success"}
    if order.status != "paid_pending_delivery":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only paid orders awaiting delivery can be retried",
        )

    await session.commit()
    try:
        await _deliver_order(session, platform_order_id)
    except Exception as exc:
        logger.exception(
            "Manual Shopier delivery retry failed for order %s",
            platform_order_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Track delivery retry failed; the order remains pending delivery",
        ) from exc
    return {"order_id": platform_order_id, "status": "success"}
