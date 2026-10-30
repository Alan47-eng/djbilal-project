from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import auth, schemas
from ..database import get_session
from ..emailer import send_email_verification_code
from ..models import PendingRegistration, User
from ..rate_limit import limiter
from ..services import UserService
from .dependencies import require_admin

router = APIRouter(tags=["auth"])
user_service = UserService()
VERIFICATION_CODE_TTL = timedelta(minutes=15)
MAX_VERIFICATION_ATTEMPTS = 5


def _verification_code_hash(code: str) -> str:
    return hmac.new(
        auth.SECRET_KEY.encode("utf-8"),
        code.encode("ascii"),
        hashlib.sha256,
    ).hexdigest()


def _new_verification_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def _set_verification_code(registration: PendingRegistration) -> str:
    code = _new_verification_code()
    registration.verification_code_hash = _verification_code_hash(code)
    registration.expires_at = datetime.now(timezone.utc) + VERIFICATION_CODE_TTL
    registration.attempts = 0
    return code


@router.post("/register")
@limiter.limit("5/minute")
async def register(
    request: Request,
    user: schemas.UserCreate,
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    if await user_service.repo.email_exists(session, user.email):
        raise HTTPException(
            status_code=400,
            detail="Email already registered",
        )

    result = await session.execute(
        select(PendingRegistration).where(PendingRegistration.email == user.email)
    )
    registration = result.scalar_one_or_none()
    if registration is None:
        registration = PendingRegistration(
            email=user.email,
            full_name=user.full_name,
            hashed_password=auth.hash_password(user.password),
            verification_code_hash="",
            expires_at=datetime.now(timezone.utc),
            attempts=0,
        )
        session.add(registration)
    else:
        registration.full_name = user.full_name
        registration.hashed_password = auth.hash_password(user.password)

    code = _set_verification_code(registration)
    await session.commit()
    try:
        send_email_verification_code(user.email, code, lang=user.lang)
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="The verification code could not be sent. Check the email service configuration and retry.",
        ) from exc
    return {"status": "verification_required"}


@router.post("/verify-email")
@limiter.limit("10/minute")
async def verify_email(
    request: Request,
    payload: schemas.EmailVerificationRequest,
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    result = await session.execute(
        select(PendingRegistration).where(
            PendingRegistration.email == payload.email
        )
    )
    registration = result.scalar_one_or_none()
    if registration is None:
        raise HTTPException(status_code=400, detail="Invalid email or verification code")
    if registration.attempts >= MAX_VERIFICATION_ATTEMPTS:
        raise HTTPException(status_code=429, detail="Too many attempts. Request a new code.")

    if registration.expires_at.tzinfo is None:
        expires_at = registration.expires_at.replace(tzinfo=timezone.utc)
    else:
        expires_at = registration.expires_at
    if expires_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Verification code expired. Request a new code.")

    if not hmac.compare_digest(
        registration.verification_code_hash,
        _verification_code_hash(payload.code),
    ):
        registration.attempts += 1
        await session.commit()
        raise HTTPException(status_code=400, detail="Invalid email or verification code")

    session.add(
        User(
            email=registration.email,
            full_name=registration.full_name,
            hashed_password=registration.hashed_password,
            email_verified=True,
        )
    )
    await session.delete(registration)
    await session.commit()
    return {"status": "verified"}


@router.post("/verification/resend")
@limiter.limit("3/hour")
async def resend_verification_email(
    request: Request,
    payload: schemas.EmailVerificationResendRequest,
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    result = await session.execute(
        select(PendingRegistration).where(
            PendingRegistration.email == payload.original_email
        )
    )
    registration = result.scalar_one_or_none()
    if registration is not None:
        if payload.email != registration.email:
            if await user_service.repo.email_exists(session, payload.email):
                raise HTTPException(status_code=400, detail="Email already registered")
            registration.email = payload.email
        code = _set_verification_code(registration)
        await session.commit()
        try:
            send_email_verification_code(registration.email, code, lang=payload.lang)
        except Exception as exc:
            raise HTTPException(
                status_code=503,
                detail="The verification code could not be sent. Please try again later.",
            ) from exc
    return {"status": "ok"}


@router.post("/login", response_model=schemas.TokenResponse)
@limiter.limit("5/minute")
async def login(
    request: Request,
    credentials: schemas.LoginRequest,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> schemas.TokenResponse:
    user = await user_service.authenticate(session, credentials)
    access_token = auth.create_access_token(data={"sub": user.email})
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=auth.ENVIRONMENT == "production",
        samesite="lax",
        max_age=auth.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    return schemas.TokenResponse(access_token=access_token, token_type="bearer")


@router.post("/logout")
async def logout(response: Response) -> dict[str, str]:
    response.delete_cookie("access_token")
    return {"status": "ok"}


@router.get("/me", response_model=schemas.UserRead)
async def get_profile(current_user: User = Depends(auth.get_current_user)) -> User:
    return current_user


@router.post("/users", response_model=schemas.UserRead)
async def create_user(
    user: schemas.UserCreate,
    current_user: User = Depends(auth.get_current_user),
    session: AsyncSession = Depends(get_session),
) -> User:
    require_admin(current_user)
    return await user_service.register(session, user, email_verified=True)


@router.get("/users", response_model=list[schemas.UserRead])
async def list_users(
    current_user: User = Depends(auth.get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[User]:
    require_admin(current_user)
    return await user_service.get_all(session)


@router.put("/api/v1/users/{user_id}/role", response_model=schemas.UserRead)
async def update_user_role(
    user_id: int,
    role_update: schemas.UserRoleUpdate,
    current_user: User = Depends(auth.get_current_user),
    session: AsyncSession = Depends(get_session),
) -> User:
    require_admin(current_user)
    return await user_service.update_role(
        session,
        user_id,
        role_update.role,
        current_user,
    )


@router.post("/users/{email}/make-admin", response_model=schemas.UserRead)
async def promote_to_admin(
    email: str,
    current_user: User = Depends(auth.get_current_user),
    session: AsyncSession = Depends(get_session),
) -> User:
    return await user_service.make_admin(session, email, current_user)
