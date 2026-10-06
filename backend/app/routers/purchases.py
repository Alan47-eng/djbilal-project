from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from .. import auth, schemas
from ..database import get_session
from ..dependencies import get_purchase_service, get_track_service
from ..models import User
from ..services import PurchaseService, TrackService

router = APIRouter(tags=["purchases"])


@router.post("/checkout/cart")
async def create_cart_checkout(
    payload: schemas.CartCheckoutRequest,
    current_user: User = Depends(auth.get_current_user),
    session: AsyncSession = Depends(get_session),
    track_service: TrackService = Depends(get_track_service),
) -> dict[str, list[int] | list[dict[str, int | str]]]:
    return await track_service.create_cart_checkout(session, payload.track_ids, current_user)


@router.get("/purchases", response_model=list[int])
async def list_purchases(
    current_user: User = Depends(auth.get_current_user),
    session: AsyncSession = Depends(get_session),
    purchase_service: PurchaseService = Depends(get_purchase_service),
) -> list[int]:
    return await purchase_service.get_user_purchases(session, current_user.id)


@router.get("/purchases/details", response_model=list[schemas.PurchaseDetail])
async def list_purchases_detailed(
    current_user: User = Depends(auth.get_current_user),
    session: AsyncSession = Depends(get_session),
    purchase_service: PurchaseService = Depends(get_purchase_service),
) -> list[schemas.PurchaseDetail]:
    details = await purchase_service.get_user_purchases_detailed(session, current_user.id)
    return [schemas.PurchaseDetail.model_validate(detail) for detail in details]


@router.get("/purchases/{purchase_id}/license-pdf")
async def download_purchase_license_pdf(
    purchase_id: int,
    current_user: User = Depends(auth.get_current_user),
    session: AsyncSession = Depends(get_session),
    purchase_service: PurchaseService = Depends(get_purchase_service),
) -> Response:
    pdf_bytes, filename = await purchase_service.generate_license_document(
        session, current_user, purchase_id
    )
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)
