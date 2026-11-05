import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..adapters.gumroad import GumroadService
from ..dependencies import get_purchase_service
from ..services import PurchaseService

router = APIRouter(tags=["webhooks"])
logger = logging.getLogger(__name__)


@router.post("/api/v1/webhooks/gumroad")
@router.post("/api/webhooks/gumroad", include_in_schema=False)
async def gumroad_webhook(
    request: Request,
    session: AsyncSession = Depends(get_session),
    purchase_service: PurchaseService = Depends(get_purchase_service),
) -> dict[str, str | list[int]]:
    try:
        form = await request.form()
    except (ValueError, UnicodeDecodeError) as exc:
        logger.warning("Ignoring malformed Gumroad form notification: %s", exc)
        return {"status": "ignored", "purchase_ids": []}

    payload: dict[str, str] = {}
    for key, value in form.items():
        if isinstance(key, str) and isinstance(value, str):
            payload[key] = value
    checkout_data = GumroadService.extract_checkout_data(payload)
    logger.info(
        "Received Gumroad webhook: field_names=%s sale_id_present=%s "
        "seller_id_present=%s product_id_present=%s permalink_present=%s "
        "checkout_user_present=%s checkout_tracks_present=%s "
        "checkout_signature_present=%s",
        sorted(payload),
        bool(payload.get("sale_id")),
        bool(payload.get("seller_id")),
        bool(payload.get("product_id")),
        bool(payload.get("product_permalink")),
        bool(checkout_data.get("user_id")),
        bool(checkout_data.get("track_ids")),
        bool(checkout_data.get("signature")),
    )
    try:
        result = await purchase_service.process_gumroad_ping(session, payload)
    except HTTPException as exc:
        logger.warning(
            "Gumroad webhook processing failed: status=%s reason=%s",
            exc.status_code,
            exc.detail,
        )
        raise
    logger.info(
        "Gumroad webhook processed: status=%s purchase_count=%s",
        result.get("status"),
        len(result.get("purchase_ids", [])),
    )
    return result
