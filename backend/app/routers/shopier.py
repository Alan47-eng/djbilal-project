from __future__ import annotations

import logging
import os
from decimal import Decimal
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from .. import auth
from ..database import get_session
from ..models import (
    Order,
    OrderItem,
    Purchase,
    ShopierWebhookEvent,
    Track,
    User,
)
from ..shopier import (
    SHOPIER_CURRENCY,
    ShopierAPIError,
    money_to_minor_units,
    price_to_minor_units,
    shopier_api_request,
    shopier_product_url,
    shopier_webhook_token,
    verify_webhook_signature,
)
from .dependencies import require_admin

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["shopier"])
SUPPORTED_SHOPIER_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp"}


def _product_media(track: Track) -> list[dict[str, object]]:
    image_url = track.cover_image_url
    if not image_url:
        return []
    parsed = urlparse(image_url)
    extension = os.path.splitext(parsed.path)[1].lower()
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or extension not in SUPPORTED_SHOPIER_IMAGE_EXTENSIONS
    ):
        return []
    return [{"type": "image", "url": image_url, "placement": 1}]


def _product_payload(track: Track) -> dict[str, object]:
    price_to_minor_units(track.price)
    return {
        "title": f"{track.title} - {track.artist}",
        "description": f"Digital music track by {track.artist}.",
        "type": "digital",
        "media": _product_media(track),
        "priceData": {
            "currency": SHOPIER_CURRENCY,
            "price": f"{Decimal(str(track.price)):.2f}",
        },
        "shippingPayer": "sellerPays",
    }


async def _publish_track(track: Track, session: AsyncSession) -> dict[str, str]:
    if track.is_free:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Free tracks cannot be listed as Shopier products",
        )

    payload = _product_payload(track)
    if track.shopier_product_id:
        result = await shopier_api_request(
            "PUT", f"/products/{track.shopier_product_id}", payload=payload
        )
    else:
        result = await shopier_api_request("POST", "/products", payload=payload)

    if not isinstance(result, dict):
        raise ShopierAPIError("Shopier returned an invalid product response")
    product_id = result.get("id")
    if not isinstance(product_id, str) or not product_id.strip():
        raise ShopierAPIError("Shopier did not return a product ID")
    product_url = shopier_product_url(
        result.get("url") or track.shopier_product_url
    )

    track.shopier_product_id = product_id
    track.shopier_product_url = product_url
    await session.commit()
    await session.refresh(track)
    return {
        "product_id": product_id,
        "product_url": product_url,
        "currency": SHOPIER_CURRENCY,
    }


@router.post("/admin/shopier/tracks/{track_id}/sync")
async def sync_shopier_track(
    track_id: int,
    current_user: User = Depends(auth.get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    require_admin(current_user)
    track = await session.get(Track, track_id)
    if track is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Track not found"
        )
    try:
        return await _publish_track(track, session)
    except ShopierAPIError as exc:
        await session.rollback()
        logger.exception("Shopier product sync failed for track %s", track_id)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@router.post("/admin/shopier/webhooks/order-created")
async def register_shopier_order_webhook(
    current_user: User = Depends(auth.get_current_user),
) -> dict[str, str]:
    require_admin(current_user)
    webhook_url = os.getenv("SHOPIER_WEBHOOK_URL", "").strip()
    parsed = urlparse(webhook_url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Set SHOPIER_WEBHOOK_URL to the public HTTPS webhook endpoint",
        )

    try:
        result = await shopier_api_request(
            "POST",
            "/webhooks",
            payload={"event": "order.created", "url": webhook_url},
        )
    except ShopierAPIError as exc:
        logger.exception("Shopier webhook registration failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc

    if not isinstance(result, dict):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Shopier returned an invalid webhook response",
        )
    webhook_token = result.get("token")
    if not isinstance(webhook_token, str) or not webhook_token:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Shopier did not return a webhook token",
        )
    return {
        "webhook_id": str(result.get("id", "")),
        "webhook_token": webhook_token,
        "instructions": "Save this token as SHOPIER_WEBHOOK_TOKEN on the backend, then restart it.",
    }


async def _deliver_order(session: AsyncSession, platform_order_id: str) -> None:
    async with session.begin():
        result = await session.execute(
            select(Order)
            .where(Order.platform_order_id == platform_order_id)
            .with_for_update()
        )
        order = result.scalar_one_or_none()
        if order is None or order.status == "success":
            return
        if order.status != "paid_pending_delivery":
            return

        items_result = await session.execute(
            select(OrderItem).where(OrderItem.order_id == order.id)
        )
        items = items_result.scalars().all()
        if not items:
            raise RuntimeError("A paid Shopier order has no mapped tracks")

        purchase_values = [
            {"user_id": order.user_id, "track_id": item.track_id}
            for item in items
        ]
        dialect_name = session.get_bind().dialect.name
        if dialect_name == "postgresql":
            insert_statement = postgresql_insert(Purchase).values(purchase_values)
        elif dialect_name == "sqlite":
            insert_statement = sqlite_insert(Purchase).values(purchase_values)
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


def _buyer_email(payload: dict[str, object]) -> str | None:
    for section_name in ("shippingInfo", "billingInfo"):
        section = payload.get(section_name)
        if isinstance(section, dict):
            email = section.get("email")
            if isinstance(email, str) and email.strip():
                return email.strip()
    return None


def _mapped_product_ids(payload: dict[str, object]) -> list[str]:
    line_items = payload.get("lineItems")
    if not isinstance(line_items, list):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Shopier order is missing line items",
        )
    product_ids = {
        item.get("productId")
        for item in line_items
        if isinstance(item, dict)
        and isinstance(item.get("productId"), str)
        and item.get("type") == "digital"
    }
    return sorted(product_ids)


@router.post("/webhooks/shopier", response_class=Response)
async def shopier_webhook(
    request: Request,
    session: AsyncSession = Depends(get_session),
    event_name: str | None = Header(default=None, alias="Shopier-Event"),
    event_id: str | None = Header(default=None, alias="Shopier-Webhook-Id"),
    signature: str | None = Header(default=None, alias="Shopier-Signature"),
) -> Response:
    webhook_token = shopier_webhook_token()
    raw_body = await request.body()
    if len(raw_body) > 1_000_000:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="Shopier webhook payload is too large",
        )
    if not verify_webhook_signature(webhook_token, raw_body, signature or ""):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Shopier webhook signature",
        )
    if not event_id or not event_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Shopier webhook ID is required",
        )
    if event_name != "order.created":
        return Response(status_code=status.HTTP_200_OK)

    try:
        payload = await request.json()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Shopier webhook JSON",
        ) from exc
    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Shopier order payload",
        )

    platform_order_id = payload.get("id")
    if not isinstance(platform_order_id, str) or not platform_order_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Shopier order ID is required",
        )
    if payload.get("paymentStatus") != "paid":
        return Response(status_code=status.HTTP_200_OK)
    if payload.get("currency") != SHOPIER_CURRENCY:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Shopier order currency does not match the store currency",
        )

    totals = payload.get("totals")
    total = totals.get("total") if isinstance(totals, dict) else None
    try:
        total_amount_minor = money_to_minor_units(total)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Shopier order total is invalid",
        ) from exc

    product_ids = _mapped_product_ids(payload)
    if not product_ids:
        return Response(status_code=status.HTTP_200_OK)
    tracks_result = await session.execute(
        select(Track).where(
            Track.shopier_product_id.in_(product_ids),
            Track.is_free.is_(False),
        )
    )
    tracks = tracks_result.scalars().all()
    if not tracks:
        return Response(status_code=status.HTTP_200_OK)

    email = _buyer_email(payload)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Shopier order has no buyer email; delivery is waiting for retry",
        )
    user_result = await session.execute(
        select(User).where(func.lower(User.email) == email.lower())
    )
    user = user_result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Create an account with the Shopier checkout email to receive tracks",
        )

    order_values = {
        "user_id": user.id,
        "platform_order_id": platform_order_id,
        "total_amount_minor": total_amount_minor,
        "currency": 1,
        "status": "paid_pending_delivery",
    }
    dialect_name = session.get_bind().dialect.name
    if dialect_name == "postgresql":
        order_insert = postgresql_insert(Order).values(**order_values)
    elif dialect_name == "sqlite":
        order_insert = sqlite_insert(Order).values(**order_values)
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Idempotent Shopier order insertion is unsupported for {dialect_name}",
        )
    insert_result = await session.execute(
        order_insert.on_conflict_do_nothing(
            index_elements=[Order.platform_order_id]
        )
    )
    order_was_created = insert_result.rowcount == 1
    order_result = await session.execute(
        select(Order).where(Order.platform_order_id == platform_order_id)
    )
    order = order_result.scalar_one_or_none()
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Shopier order could not be recorded",
        )

    if order_was_created:
        session.add_all(
            [
                OrderItem(
                    order_id=order.id,
                    track_id=track.id,
                    track_title=track.title,
                    price_minor=price_to_minor_units(track.price),
                )
                for track in tracks
            ]
        )
    else:
        existing_items_result = await session.execute(
            select(OrderItem.track_id).where(OrderItem.order_id == order.id)
        )
        existing_track_ids = set(existing_items_result.scalars().all())
        expected_track_ids = {track.id for track in tracks}
        if (
            order.user_id != user.id
            or order.total_amount_minor != total_amount_minor
            or order.currency != 1
            or (existing_track_ids and existing_track_ids != expected_track_ids)
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Shopier order payload does not match the recorded order",
            )
        if not existing_track_ids:
            order_item_values = [
                {
                    "order_id": order.id,
                    "track_id": track.id,
                    "track_title": track.title,
                    "price_minor": price_to_minor_units(track.price),
                }
                for track in tracks
            ]
            if dialect_name == "postgresql":
                item_insert = postgresql_insert(OrderItem).values(order_item_values)
            else:
                item_insert = sqlite_insert(OrderItem).values(order_item_values)
            await session.execute(
                item_insert.on_conflict_do_nothing(
                    index_elements=[OrderItem.order_id, OrderItem.track_id]
                )
            )

    existing_event = await session.get(ShopierWebhookEvent, event_id)
    if existing_event is not None:
        if existing_event.shopier_order_id != platform_order_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Shopier webhook ID is already associated with another order",
            )
    else:
        session.add(
            ShopierWebhookEvent(
                id=event_id,
                event=event_name,
                shopier_order_id=platform_order_id,
            )
        )

    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        order_result = await session.execute(
            select(Order).where(Order.platform_order_id == platform_order_id)
        )
        order = order_result.scalar_one_or_none()
        event = await session.get(ShopierWebhookEvent, event_id)
        if order is None or (
            event is not None and event.shopier_order_id != platform_order_id
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Shopier order could not be recorded",
            )

    if order.status == "success":
        return Response(status_code=status.HTTP_200_OK)

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
            status_code=status.HTTP_404_NOT_FOUND, detail="Shopier order not found"
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
            "Manual Shopier delivery retry failed for order %s", platform_order_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Track delivery retry failed; the order remains pending delivery",
        ) from exc
    return {"order_id": platform_order_id, "status": "success"}
