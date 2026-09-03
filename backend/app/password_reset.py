from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
import os

from . import auth, schemas
from .services import UserService
from .database import get_session
from .emailer import send_password_reset_email

router = APIRouter(prefix="/password", tags=["password-reset"])

user_service = UserService()


@router.post("/request")
async def request_password_reset(
    payload: schemas.PasswordResetRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """Request a password reset. Always returns 200 to avoid user enumeration."""
    # Try to find user; if not found, silently return ok
    user = await user_service.get_by_email(session, payload.email)
    if not user:
        return {"status": "ok"}

    # Create a short-lived token (1 hour) with a pw_reset claim
    token = auth.create_access_token(
        data={"sub": user.email, "pw_reset": True},
        expires_delta=timedelta(hours=1),
    )

    # Send email (no await since send_password_reset_email is sync)
    try:
        send_password_reset_email(user.email, token)
    except Exception as exc:
        # Log the actual failure so it can be diagnosed in Railway logs.
        import logging
        logging.getLogger(__name__).warning("Password reset email failed for %s: %s", user.email, exc)

    return {"status": "ok"}


@router.post("/confirm")
async def confirm_password_reset(
    payload: schemas.PasswordResetConfirm,
    session: AsyncSession = Depends(get_session),
):
    """Confirm password reset using token and new password."""
    # Decode and validate token
    token_payload = auth.decode_token(payload.token)
    if not token_payload.get("pw_reset"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token")

    email = token_payload.get("sub")
    if not email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token payload")

    user = await user_service.get_by_email(session, email)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Validate new password strength similar to registration rules
    pwd = payload.new_password or ""
    if len(pwd) < 8 or not any(c.isalpha() for c in pwd) or not any(c.isdigit() for c in pwd):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password must be at least 8 characters long and contain letters and numbers",
        )

    user.hashed_password = auth.hash_password(pwd)
    await session.commit()
    await session.refresh(user)

    return {"status": "ok"}
