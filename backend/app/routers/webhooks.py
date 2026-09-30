from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..dependencies import get_payment_gateway, get_purchase_service
from ..interfaces import BasePaymentGateway
from ..json_types import parse_json_object
from ..services import PurchaseService

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/lemonsqueezy")
async def lemonsqueezy_webhook(
    request: Request,
    session: AsyncSession = Depends(get_session),
    payment_gateway: BasePaymentGateway = Depends(get_payment_gateway),
    purchase_service: PurchaseService = Depends(get_purchase_service),
) -> dict[str, str | list[int]]:
    raw_body = await request.body()
    signature = request.headers.get("X-Signature") or request.headers.get(
        "X-Lemon-Squeezy-Signature"
    )

    if not payment_gateway.verify_webhook(raw_body, signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature",
        )

    payload = parse_json_object(raw_body)
    return await purchase_service.process_successful_payment_payload(session, payload)
