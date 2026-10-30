import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..dependencies import get_purchase_service
from ..services import PurchaseService

router = APIRouter(tags=["webhooks"])
logger = logging.getLogger(__name__)


def _ignored_response(reason: str) -> dict[str, str | list[int]]:
    logger.warning("Acknowledging Gumroad notification without purchase: %s", reason)
    return {"status": "ignored", "purchase_ids": []}


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
    try:
        return await purchase_service.process_gumroad_ping(session, payload)
    except HTTPException as exc:
        if exc.status_code != status.HTTP_400_BAD_REQUEST:
            raise
        return _ignored_response(str(exc.detail))
