from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..dependencies import get_purchase_service
from ..services import PurchaseService

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


@router.post("/gumroad")
async def gumroad_webhook(
    request: Request,
    session: AsyncSession = Depends(get_session),
    purchase_service: PurchaseService = Depends(get_purchase_service),
) -> dict[str, str | list[int]]:
    form = await request.form()
    payload: dict[str, str] = {}
    for key, value in form.items():
        if isinstance(key, str) and isinstance(value, str):
            payload[key] = value
    return await purchase_service.process_gumroad_ping(session, payload)
