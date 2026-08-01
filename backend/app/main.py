import os
import hmac
import json
import hashlib
from pathlib import Path
from urllib.parse import urlencode, urlparse, parse_qsl, urlunparse
from uuid import uuid4

from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from .database import test_connection, engine, get_session, async_session
from .models import Base, User, Track, Purchase
from . import schemas, auth

app = FastAPI()

UPLOAD_ROOT = Path(__file__).resolve().parent / "uploads"
TRACK_UPLOAD_DIR = UPLOAD_ROOT / "tracks"
PREVIEW_UPLOAD_DIR = UPLOAD_ROOT / "previews"
COVER_UPLOAD_DIR = UPLOAD_ROOT / "covers"

TRACK_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
PREVIEW_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
COVER_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/media", StaticFiles(directory=str(UPLOAD_ROOT)), name="media")

frontend_origins = [
    origin.strip()
    for origin in os.getenv("FRONTEND_ORIGINS", "http://localhost:3000").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=frontend_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
    async with async_session() as session:
        result = await session.execute(select(User).where(User.email == "admin@djbilal.com"))
        admin_user = result.scalars().first()

        if admin_user:
            admin_user.is_admin = True
        else:
            admin_user = User(
                email="admin@djbilal.com",
                hashed_password=auth.hash_password("Admin123!"),
                is_admin=True,
            )
            session.add(admin_user)

        await session.commit()


def build_media_url(request: Request, folder: str, filename: str) -> str:
    return f"{str(request.base_url).rstrip('/')}/media/{folder}/{filename}"


def build_storage_name(filename: str) -> str:
    suffix = Path(filename).suffix
    stem = Path(filename).stem or "upload"
    return f"{stem}-{uuid4().hex}{suffix}"


async def save_upload_file(upload_file: UploadFile, destination: Path) -> None:
    contents = await upload_file.read()
    destination.write_bytes(contents)
    await upload_file.close()


def build_uploaded_media_url(request: Request, folder: str, filename: str) -> str:
    return build_media_url(request, folder, filename)


def require_admin(current_user: User) -> None:
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )


def get_request_origin(request: Request) -> str:
    return str(request.base_url).rstrip("/")


def build_checkout_url(base_url: str, custom_data: dict[str, str], email: str | None = None) -> str:
    parsed_url = urlparse(base_url)
    query_items = dict(parse_qsl(parsed_url.query, keep_blank_values=True))

    if email:
        query_items["checkout[email]"] = email

    for key, value in custom_data.items():
        query_items[f"checkout[custom][{key}]"] = value

    return urlunparse(parsed_url._replace(query=urlencode(query_items)))


def extract_nested_dict(payload: dict, target_key: str) -> dict | None:
    if not isinstance(payload, dict):
        return None

    if target_key in payload and isinstance(payload[target_key], dict):
        return payload[target_key]

    for value in payload.values():
        if isinstance(value, dict):
            nested = extract_nested_dict(value, target_key)
            if nested is not None:
                return nested
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    nested = extract_nested_dict(item, target_key)
                    if nested is not None:
                        return nested

    return None


def extract_custom_data(payload: dict) -> dict[str, str]:
    for key in ("custom_data", "custom", "checkout_data"):
        nested = extract_nested_dict(payload, key)
        if nested:
            return {str(k): str(v) for k, v in nested.items() if v is not None}
    return {}


def is_successful_payment_event(payload: dict) -> bool:
    event_name = (
        payload.get("meta", {}).get("event_name")
        or payload.get("meta", {}).get("name")
        or payload.get("event_name")
        or payload.get("type")
        or ""
    ).lower()

    status_value = (
        payload.get("data", {}).get("attributes", {}).get("status")
        or payload.get("data", {}).get("attributes", {}).get("status_formatted")
        or payload.get("meta", {}).get("status")
        or ""
    ).lower()

    if any(token in event_name for token in ("order", "payment", "license")):
        return "fail" not in event_name and status_value not in ("failed", "canceled", "cancelled", "unpaid")

    return status_value in ("paid", "succeeded", "successful", "completed")

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
    # Check if user already exists
    result = await session.execute(select(User).where(User.email == user.email))
    existing_user = result.scalars().first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Hash password and create user
    hashed_password = auth.hash_password(user.password)
    new_user = User(email=user.email, hashed_password=hashed_password)
    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)
    return new_user

@app.post("/login", response_model=schemas.TokenResponse)
async def login(credentials: schemas.LoginRequest, session: AsyncSession = Depends(get_session)):
    # Find user by email
    result = await session.execute(select(User).where(User.email == credentials.email))
    user = result.scalars().first()
    
    if not user or not auth.verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
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

    new_user = User(email=user.email, hashed_password=auth.hash_password(user.password))
    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)
    return new_user

@app.get("/users", response_model=list[schemas.UserRead])
async def list_users(
    current_user: User = Depends(auth.get_current_user),
    session: AsyncSession = Depends(get_session),
):
    require_admin(current_user)

    result = await session.execute(select(User))
    users = result.scalars().all()
    return users

@app.post("/tracks", response_model=schemas.TrackResponse)
async def create_track(
    track: schemas.TrackCreate,
    current_user: User = Depends(auth.get_current_user),
    session: AsyncSession = Depends(get_session)
):
    require_admin(current_user)

    new_track = Track(
        title=track.title,
        artist=track.artist,
        price=track.price,
        cover_image_url=track.cover_image_url,
        checkout_url=track.checkout_url,
        preview_url=track.preview_url,
        full_file_path=track.full_file_path
    )
    session.add(new_track)
    await session.commit()
    await session.refresh(new_track)
    return new_track


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

    new_track = Track(
        title=title.strip(),
        artist=artist.strip(),
        price=price,
        cover_image_url=build_uploaded_media_url(request, "covers", cover_filename) if cover_filename else None,
        checkout_url=checkout_url.strip() if checkout_url else None,
        preview_url=build_media_url(request, "previews", preview_filename),
        full_file_path=build_media_url(request, "tracks", track_filename),
    )
    session.add(new_track)
    await session.commit()
    await session.refresh(new_track)
    return new_track

@app.get("/tracks", response_model=list[schemas.TrackResponse])
async def list_tracks(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Track))
    tracks = result.scalars().all()
    return tracks

@app.get("/tracks/{track_id}", response_model=schemas.TrackResponse)
async def get_track(track_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Track).where(Track.id == track_id))
    track = result.scalars().first()
    if not track:
        return JSONResponse(status_code=404, content={"detail": "Track not found"})
    return track


@app.post("/tracks/{track_id}/checkout")
async def create_checkout(
    track_id: int,
    current_user: User = Depends(auth.get_current_user),
    session: AsyncSession = Depends(get_session),
):
    track_result = await session.execute(select(Track).where(Track.id == track_id))
    track = track_result.scalars().first()
    if not track:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Track not found")

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
    result = await session.execute(
        select(Purchase.track_id)
        .where(Purchase.user_id == current_user.id)
        .order_by(Purchase.created_at.desc())
    )
    return list(result.scalars().all())


@app.post("/webhooks/lemonsqueezy")
async def lemonsqueezy_webhook(request: Request, session: AsyncSession = Depends(get_session)):
    raw_body = await request.body()
    secret = os.getenv("LEMON_SQUEEZY_WEBHOOK_SECRET", "").strip()

    if secret:
        signature = request.headers.get("X-Signature") or request.headers.get("X-Lemon-Squeezy-Signature")
        expected = hmac.new(
            secret.encode("utf-8"),
            raw_body,
            hashlib.sha256,
        ).hexdigest()
        if not signature or not hmac.compare_digest(signature, expected):
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

    track_result = await session.execute(select(Track).where(Track.id == int(track_id)))
    track = track_result.scalars().first()
    if not track:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Track not found")

    purchase_result = await session.execute(
        select(Purchase).where(
            Purchase.user_id == int(user_id),
            Purchase.track_id == track.id,
        )
    )
    existing_purchase = purchase_result.scalars().first()
    if existing_purchase:
        return {"status": "ok", "purchase_id": existing_purchase.id}

    purchase = Purchase(user_id=int(user_id), track_id=track.id)
    session.add(purchase)
    await session.commit()
    await session.refresh(purchase)

    return {"status": "ok", "purchase_id": purchase.id}


@app.get("/tracks/{track_id}/download", response_model=schemas.DownloadResponse)
async def download_track(
    track_id: int,
    current_user: User = Depends(auth.get_current_user),
    session: AsyncSession = Depends(get_session),
):
    track_result = await session.execute(select(Track).where(Track.id == track_id))
    track = track_result.scalars().first()
    if not track:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Track not found")

    purchase_result = await session.execute(
        select(Purchase.id).where(
            Purchase.user_id == current_user.id,
            Purchase.track_id == track_id,
        )
    )
    purchase = purchase_result.scalar_one_or_none()
    if not purchase:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must purchase this track before downloading it",
        )

    return {
        "track_id": track.id,
        "full_file_path": track.full_file_path,
        "download_url": track.full_file_path,
    }
