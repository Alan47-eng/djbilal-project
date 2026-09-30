from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from .. import auth, schemas
from ..database import get_session
from ..emailer import send_password_reset_email
from ..rate_limit import limiter
from ..services import UserService

router = APIRouter(prefix="/password", tags=["password-reset"])
user_service = UserService()


@router.post("/request")
@limiter.limit("3/hour")
async def request_password_reset(
    request: Request,
    payload: schemas.PasswordResetRequest,
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    """Request a password reset. Always returns 200 to avoid user enumeration."""
    user = await user_service.get_by_email(session, payload.email)
    if not user:
        return {"status": "ok"}

    token = auth.create_access_token(
        data={"sub": user.email, "pw_reset": True},
        expires_delta=timedelta(hours=1),
    )

    try:
        send_password_reset_email(user.email, token)
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning(
            "Password reset email failed for %s: %s", user.email, exc
        )

    return {"status": "ok"}


@router.post("/confirm")
@limiter.limit("5/minute")
async def confirm_password_reset(
    request: Request,
    payload: schemas.PasswordResetConfirm,
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    token_payload = auth.decode_token(payload.token)
    if token_payload.get("pw_reset") is not True:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token")

    email = token_payload.get("sub")
    if not isinstance(email, str) or not email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token payload")

    user = await user_service.get_by_email(session, email)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    password = payload.new_password or ""
    if len(password) < 8 or not any(char.isalpha() for char in password) or not any(
        char.isdigit() for char in password
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password must be at least 8 characters long and contain letters and numbers",
        )

    user.hashed_password = auth.hash_password(password)
    await session.commit()
    await session.refresh(user)

    return {"status": "ok"}
