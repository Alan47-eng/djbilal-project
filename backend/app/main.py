import os
import json
from pathlib import Path

from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from .database import test_connection, engine, get_session, async_session
from .models import Base, User, Track, Purchase
from . import schemas, auth
from .services import UserService, TrackService, PurchaseService
from .utils import (
    TRACK_UPLOAD_DIR, PREVIEW_UPLOAD_DIR, COVER_UPLOAD_DIR,
    UPLOAD_ROOT, build_media_url, build_storage_name,
    save_upload_file, build_checkout_url, extract_custom_data,
    is_successful_payment_event, verify_webhook_signature
)

app = FastAPI()

app.mount("/media", StaticFiles(directory=str(UPLOAD_ROOT)), name="media")

# Allow all origins for now - simplest solution
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
                "ALTER TABLE tracks ADD COLUMN IF NOT EXISTS cover_image_url VARCHAR(1024)"
            ))
            await conn.execute(text(
                "ALTER TABLE tracks ADD COLUMN IF NOT EXISTS checkout_url VARCHAR(1024)"
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
                ),
                Track(
                    title="Sunset Echoes",
                    artist="Atlas Bloom",
                    price=2.49,
                    cover_image_url=None,
                    checkout_url=None,
                    preview_url="https://example.com/previews/sunset-echoes.mp3",
                    full_file_path="/music/sunset-echoes.mp3",
                ),
                Track(
                    title="City Lights",
                    artist="Luna Harbor",
                    price=1.49,
                    cover_image_url=None,
                    checkout_url=None,
                    preview_url="https://example.com/previews/city-lights.mp3",
                    full_file_path="/music/city-lights.mp3",
                ),
            ])
            await session.commit()


async def seed_admin_user():
    """Create seed admin user if it doesn't exist."""
    async with async_session() as session:
        result = await session.execute(select(User).where(User.email == "admin@djbilal.com"))
        admin_user = result.scalars().first()

        if admin_user:
            if not admin_user.is_admin:
                admin_user.is_admin = True
        else:
            admin_user = User(
                email="admin@djbilal.com",
                hashed_password=auth.hash_password("Admin123!"),
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
async def login(credentials: schemas.LoginRequest, session: AsyncSession = Depends(get_session)):
    user = await user_service.authenticate(session, credentials)
    access_token = auth.create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

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
    price: float = Form(...),
    checkout_url: str | None = Form(None),
    track_file: UploadFile = File(...),
    preview_file: UploadFile = File(...),
    cover_file: UploadFile | None = File(None),
    current_user: User = Depends(auth.get_current_user),
    session: AsyncSession = Depends(get_session),
):
    require_admin(current_user)

    track_filename = build_storage_name(track_file.filename)
    preview_filename = build_storage_name(preview_file.filename)
    cover_filename = build_storage_name(cover_file.filename) if cover_file else None

    await save_upload_file(track_file, TRACK_UPLOAD_DIR / track_filename)
    await save_upload_file(preview_file, PREVIEW_UPLOAD_DIR / preview_filename)
    if cover_file and cover_filename:
        await save_upload_file(cover_file, COVER_UPLOAD_DIR / cover_filename)

    track_data = schemas.TrackCreate(
        title=title.strip(),
        artist=artist.strip(),
        price=price,
        cover_image_url=build_media_url(request, "covers", cover_filename) if cover_filename else None,
        checkout_url=checkout_url.strip() if checkout_url else None,
        preview_url=build_media_url(request, "previews", preview_filename),
        full_file_path=build_media_url(request, "tracks", track_filename),
    )
    return await track_service.create_track(session, track_data)

@app.get("/tracks", response_model=list[schemas.TrackResponse])
async def list_tracks(session: AsyncSession = Depends(get_session)):
    return await track_service.get_all_tracks(session)

@app.get("/tracks/{track_id}", response_model=schemas.TrackResponse)
async def get_track(track_id: int, session: AsyncSession = Depends(get_session)):
    return await track_service.get_track(session, track_id)


@app.post("/tracks/{track_id}/checkout")
async def create_checkout(
    track_id: int,
    current_user: User = Depends(auth.get_current_user),
    session: AsyncSession = Depends(get_session),
):
    track = await track_service.get_track(session, track_id)

    if not track.checkout_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Checkout URL not configured for this track",
        )

    checkout_url = build_checkout_url(
        track.checkout_url,
        {
            "track_id": str(track.id),
            "user_id": str(current_user.id),
        },
        email=current_user.email,
    )

    return {
        "track_id": track.id,
        "checkout_url": checkout_url,
    }

@app.get("/purchases", response_model=list[int])
async def list_purchases(
    current_user: User = Depends(auth.get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await purchase_service.get_user_purchases(session, current_user.id)

@app.post("/webhooks/lemonsqueezy")
async def lemonsqueezy_webhook(request: Request, session: AsyncSession = Depends(get_session)):
    raw_body = await request.body()
    signature = request.headers.get("X-Signature") or request.headers.get("X-Lemon-Squeezy-Signature")

    if not verify_webhook_signature(raw_body, signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook signature")

    payload = json.loads(raw_body.decode("utf-8"))
    if not is_successful_payment_event(payload):
        return {"status": "ignored"}

    custom_data = extract_custom_data(payload)
    track_id = custom_data.get("track_id")
    user_id = custom_data.get("user_id")

    if not track_id or not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing custom data",
        )

    purchase = await purchase_service.record_purchase(session, int(user_id), int(track_id))
    return {"status": "ok", "purchase_id": purchase.id}

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
        "full_file_path": track.full_file_path,
        "download_url": track.full_file_path,
    }
