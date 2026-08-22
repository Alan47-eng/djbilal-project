import os
import json

from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from .database import test_connection, engine, get_session, async_session
from .models import Base, User, Track
from . import schemas, auth
from .services import UserService, TrackService, PurchaseService
from .utils import (
    UPLOAD_ROOT,
    resolve_uploaded_file_path,
    normalize_media_url,
    verify_webhook_signature,
)

app = FastAPI()

def parse_frontend_origins(raw_value: str | None) -> list[str]:
    if not raw_value:
        return [
            "http://localhost:3000",
            "http://localhost:5173",
            "http://localhost:4173",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:4173",
            "https://djbilal-frontend-production.up.railway.app",
        ]

    origins = [origin.strip() for origin in raw_value.split(",") if origin.strip()]
    if not origins:
        raise RuntimeError("FRONTEND_ORIGINS is empty")
    return origins


FRONTEND_ORIGINS = parse_frontend_origins(os.getenv("FRONTEND_ORIGINS"))
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@djbilal.com")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
IS_PRODUCTION = os.getenv("ENVIRONMENT", "development").lower() == "production"
LOCAL_DEV_ORIGIN_REGEX = (
    r"^https?://("
    r"(localhost|127\.0\.0\.1|0\.0\.0\.0)"
    r"|192\.168\.\d{1,3}\.\d{1,3}"
    r"|10\.\d{1,3}\.\d{1,3}\.\d{1,3}"
    r"|172\.(1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3}"
    r")(:\d+)?$"
)
PRODUCTION_ORIGIN_REGEX = (
    r"^https://("
    r"([a-z0-9-]+\.)?dj-bilal\.com"
    r"|djbilal-frontend-production\.up\.railway\.app"
    r")$"
)

# CORS middleware MUST be first (before mount)
app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_origin_regex=PRODUCTION_ORIGIN_REGEX if IS_PRODUCTION else LOCAL_DEV_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/media", StaticFiles(directory=str(UPLOAD_ROOT)), name="media")

user_service = UserService()
track_service = TrackService()
purchase_service = PurchaseService()


def require_admin(current_user: User) -> None:
    """Dependency to ensure user is admin."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

@app.on_event("startup")
async def startup():
    # Create tables automatically in local dev for convenience
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        if conn.dialect.name == "postgresql":
            await conn.execute(text(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN NOT NULL DEFAULT FALSE"
            ))
            await conn.execute(text(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS full_name VARCHAR(255)"
            ))
            await conn.execute(text(
                "ALTER TABLE tracks ADD COLUMN IF NOT EXISTS cover_image_url VARCHAR(1024)"
            ))
            await conn.execute(text(
                "ALTER TABLE tracks ADD COLUMN IF NOT EXISTS checkout_url VARCHAR(1024)"
            ))
            await conn.execute(text(
                "ALTER TABLE tracks ADD COLUMN IF NOT EXISTS lemon_variant_id INTEGER"
            ))
            await conn.execute(text(
                "ALTER TABLE tracks ADD COLUMN IF NOT EXISTS is_free BOOLEAN NOT NULL DEFAULT FALSE"
            ))
            await conn.execute(text(
                "ALTER TABLE tracks ADD COLUMN IF NOT EXISTS free_download_url VARCHAR(1024)"
            ))
            await conn.execute(text(
                "ALTER TABLE tracks ADD COLUMN IF NOT EXISTS category VARCHAR(50) NOT NULL DEFAULT 'edit'"
            ))
            await conn.execute(text(
                "UPDATE tracks SET category = CASE WHEN is_free THEN 'remix' ELSE 'edit' END WHERE category IS NULL"
            ))
            await conn.execute(text(
                "ALTER TABLE purchases ADD COLUMN IF NOT EXISTS license_type VARCHAR(100)"
            ))

    await seed_tracks()
    await seed_admin_user()


async def seed_tracks():
    async with async_session() as session:
        result = await session.execute(select(Track.id).limit(1))
        existing_track = result.scalar_one_or_none()

        if existing_track is None:
            session.add_all([
                Track(
                    title="Midnight Drive",
                    artist="Nova Lane",
                    price=1.99,
                    cover_image_url=None,
                    checkout_url=None,
                    preview_url="https://example.com/previews/midnight-drive.mp3",
                    full_file_path="/music/midnight-drive.mp3",
                    category="edit",
                ),
                Track(
                    title="Sunset Echoes",
                    artist="Atlas Bloom",
                    price=2.49,
                    cover_image_url=None,
                    checkout_url=None,
                    preview_url="https://example.com/previews/sunset-echoes.mp3",
                    full_file_path="/music/sunset-echoes.mp3",
                    category="edit",
                ),
                Track(
                    title="City Lights",
                    artist="Luna Harbor",
                    price=1.49,
                    cover_image_url=None,
                    checkout_url=None,
                    preview_url="https://example.com/previews/city-lights.mp3",
                    full_file_path="/music/city-lights.mp3",
                    category="remix",
                ),
            ])
            await session.commit()


async def seed_admin_user():
    """Create seed admin user if it doesn't exist."""
    if not ADMIN_PASSWORD:
        return

    async with async_session() as session:
        result = await session.execute(select(User).where(User.email == ADMIN_EMAIL))
        admin_user = result.scalars().first()

        if admin_user:
            if not admin_user.is_admin:
                admin_user.is_admin = True
                await session.commit()
            return

        admin_password_hash = auth.hash_password(ADMIN_PASSWORD)
        admin_user = User(
            email=ADMIN_EMAIL,
            full_name="DJ Bilal Admin",
            hashed_password=admin_password_hash,
            is_admin=True,
        )
        session.add(admin_user)
        await session.commit()


@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/db-check")
async def db_check():
    try:
        await test_connection()
        return {"status": "ok", "db": "reachable"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "detail": str(e)})

@app.post("/register", response_model=schemas.UserRead)
async def register(user: schemas.UserCreate, session: AsyncSession = Depends(get_session)):
    return await user_service.register(session, user)

@app.post("/login", response_model=schemas.TokenResponse)
async def login(
    credentials: schemas.LoginRequest,
    response: Response,
    session: AsyncSession = Depends(get_session),
):
    user = await user_service.authenticate(session, credentials)
    access_token = auth.create_access_token(data={"sub": user.email})
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=IS_PRODUCTION,
        samesite="lax",
        max_age=auth.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token")
    return {"status": "ok"}

@app.get("/me", response_model=schemas.UserRead)
async def get_profile(current_user: User = Depends(auth.get_current_user)):
    return current_user

@app.post("/users", response_model=schemas.UserRead)
async def create_user(
    user: schemas.UserCreate,
    current_user: User = Depends(auth.get_current_user),
    session: AsyncSession = Depends(get_session),
):
    require_admin(current_user)
    return await user_service.register(session, user)

@app.get("/users", response_model=list[schemas.UserRead])
async def list_users(
    current_user: User = Depends(auth.get_current_user),
    session: AsyncSession = Depends(get_session),
):
    require_admin(current_user)
    return await user_service.get_all(session)

@app.post("/users/{email}/make-admin", response_model=schemas.UserRead)
async def promote_to_admin(
    email: str,
    current_user: User = Depends(auth.get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Promote a user to admin. Requires admin privileges."""
    return await user_service.make_admin(session, email, current_user)

@app.post("/tracks", response_model=schemas.TrackResponse)
async def create_track(
    track: schemas.TrackCreate,
    current_user: User = Depends(auth.get_current_user),
    session: AsyncSession = Depends(get_session)
):
    require_admin(current_user)
    return await track_service.create_track(session, track)

@app.post("/tracks/upload", response_model=schemas.TrackResponse)
async def upload_track(
    request: Request,
    title: str = Form(...),
    artist: str = Form(...),
    category: str = Form(...),
    price: float | None = Form(None),
    checkout_url: str | None = Form(None),
    lemon_variant_id: int | None = Form(None),
    is_free: bool = Form(False),
    free_download_url: str | None = Form(None),
    track_file: UploadFile = File(...),
    preview_file: UploadFile = File(...),
    cover_file: UploadFile | None = File(None),
    current_user: User = Depends(auth.get_current_user),
    session: AsyncSession = Depends(get_session),
):
    require_admin(current_user)
    return await track_service.upload_track(
        session=session,
        request=request,
        title=title,
        artist=artist,
        category=category,
        price=price,
        checkout_url=checkout_url,
        lemon_variant_id=lemon_variant_id,
        is_free=is_free,
        free_download_url=free_download_url,
        track_file=track_file,
        preview_file=preview_file,
        cover_file=cover_file,
    )

@app.get("/tracks", response_model=list[schemas.TrackResponse])
async def list_tracks(session: AsyncSession = Depends(get_session)):
    tracks = await track_service.get_all_tracks(session)
    return [
        {
            "id": track.id,
            "title": track.title,
            "artist": track.artist,
            "price": track.price,
            "cover_image_url": normalize_media_url(track.cover_image_url),
            "checkout_url": track.checkout_url,
            "lemon_variant_id": track.lemon_variant_id,
            "preview_url": normalize_media_url(track.preview_url),
            "is_free": track.is_free,
            "free_download_url": normalize_media_url(track.free_download_url),
            "category": track.category,
            "created_at": track.created_at,
        }
        for track in tracks
    ]

@app.get("/tracks/{track_id}", response_model=schemas.TrackResponse)
async def get_track(track_id: int, session: AsyncSession = Depends(get_session)):
    track = await track_service.get_track(session, track_id)
    return {
        "id": track.id,
        "title": track.title,
        "artist": track.artist,
        "price": track.price,
        "cover_image_url": normalize_media_url(track.cover_image_url),
        "checkout_url": track.checkout_url,
        "lemon_variant_id": track.lemon_variant_id,
        "preview_url": normalize_media_url(track.preview_url),
        "is_free": track.is_free,
        "free_download_url": normalize_media_url(track.free_download_url),
        "category": track.category,
        "created_at": track.created_at,
    }

@app.get("/tracks/{track_id}/free-download", response_model=schemas.DownloadResponse)
async def free_download_track(
    track_id: int,
    session: AsyncSession = Depends(get_session),
):
    track = await track_service.get_track(session, track_id)
    if not track.is_free:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This track is not available for free download",
        )
    download_url = normalize_media_url(track.free_download_url) or normalize_media_url(track.full_file_path)
    return {
        "track_id": track.id,
        "full_file_path": normalize_media_url(track.full_file_path),
        "download_url": download_url,
    }


@app.get("/tracks/{track_id}/free-download-file")
async def free_download_track_file(
    track_id: int,
    session: AsyncSession = Depends(get_session),
):
    track = await track_service.get_track(session, track_id)
    if not track.is_free:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This track is not available for free download",
        )
    file_path = resolve_uploaded_file_path(track.full_file_path, "tracks")
    return FileResponse(
        path=file_path,
        filename=file_path.name,
        media_type="application/octet-stream",
    )


@app.post("/tracks/{track_id}/checkout")
async def create_checkout(
    track_id: int,
    current_user: User = Depends(auth.get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await track_service.create_checkout(session, track_id, current_user)


@app.post("/checkout/cart")
async def create_cart_checkout(
    payload: schemas.CartCheckoutRequest,
    current_user: User = Depends(auth.get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await track_service.create_cart_checkout(session, payload.track_ids, current_user)

@app.get("/purchases", response_model=list[int])
async def list_purchases(
    current_user: User = Depends(auth.get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await purchase_service.get_user_purchases(session, current_user.id)

@app.get("/purchases/details", response_model=list[schemas.PurchaseDetail])
async def list_purchases_detailed(
    current_user: User = Depends(auth.get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await purchase_service.get_user_purchases_detailed(session, current_user.id)


@app.get("/purchases/{purchase_id}/license-pdf")
async def download_purchase_license_pdf(
    purchase_id: int,
    current_user: User = Depends(auth.get_current_user),
    session: AsyncSession = Depends(get_session),
):
    pdf_bytes, filename = await purchase_service.generate_license_document(
        session, current_user, purchase_id
    )
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)

@app.post("/webhooks/lemonsqueezy")
async def lemonsqueezy_webhook(request: Request, session: AsyncSession = Depends(get_session)):
    raw_body = await request.body()
    signature = request.headers.get("X-Signature") or request.headers.get("X-Lemon-Squeezy-Signature")

    if not verify_webhook_signature(raw_body, signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook signature")

    payload = json.loads(raw_body.decode("utf-8"))
    return await purchase_service.process_successful_payment_payload(session, payload)

@app.get("/tracks/{track_id}/download", response_model=schemas.DownloadResponse)
async def download_track(
    track_id: int,
    current_user: User = Depends(auth.get_current_user),
    session: AsyncSession = Depends(get_session),
):
    track = await track_service.get_track(session, track_id)
    
    if not await purchase_service.can_download(session, current_user.id, track_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must purchase this track before downloading it",
        )

    return {
        "track_id": track.id,
        "full_file_path": normalize_media_url(track.full_file_path),
        "download_url": normalize_media_url(track.full_file_path),
    }


@app.get("/tracks/{track_id}/download-file")
async def download_track_file(
    track_id: int,
    current_user: User = Depends(auth.get_current_user),
    session: AsyncSession = Depends(get_session),
):
    track = await track_service.get_track(session, track_id)

    if not await purchase_service.can_download(session, current_user.id, track_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must purchase this track before downloading it",
        )

    file_path = resolve_uploaded_file_path(track.full_file_path, "tracks")
    return FileResponse(
        path=file_path,
        filename=file_path.name,
        media_type="application/octet-stream",
    )
