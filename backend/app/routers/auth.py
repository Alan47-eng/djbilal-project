from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from .. import auth, schemas
from ..database import get_session
from ..models import User
from ..rate_limit import limiter
from ..services import UserService
from .dependencies import require_admin

router = APIRouter(tags=["auth"])
user_service = UserService()


@router.post("/register", response_model=schemas.UserRead)
@limiter.limit("5/minute")
async def register(
    request: Request,
    user: schemas.UserCreate,
    session: AsyncSession = Depends(get_session),
) -> User:
    return await user_service.register(session, user)


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
    return await user_service.register(session, user)


@router.get("/users", response_model=list[schemas.UserRead])
async def list_users(
    current_user: User = Depends(auth.get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[User]:
    require_admin(current_user)
    return await user_service.get_all(session)


@router.post("/users/{email}/make-admin", response_model=schemas.UserRead)
async def promote_to_admin(
    email: str,
    current_user: User = Depends(auth.get_current_user),
    session: AsyncSession = Depends(get_session),
) -> User:
    return await user_service.make_admin(session, email, current_user)
