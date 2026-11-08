"""Business logic layer - Service classes for domain operations."""
import io
import logging

from fastapi import HTTPException, status
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from . import auth, schemas
from .interfaces import BaseStorageService
from .models import Album, User, Track
from .repositories import TrackRepository, UserRepository
from .utils import (
    build_storage_name,
    validate_upload_data,
    AUDIO_EXTENSIONS,
    IMAGE_EXTENSIONS,
    MAX_TRACK_UPLOAD_BYTES,
    MAX_PREVIEW_UPLOAD_BYTES,
    MAX_COVER_UPLOAD_BYTES,
)

logger = logging.getLogger(__name__)


class UserService:
    """Handle user-related business logic."""

    def __init__(self) -> None:
        self.repo = UserRepository()

    async def register(
        self,
        session: AsyncSession,
        user_data: schemas.UserCreate,
        *,
        email_verified: bool = False,
    ) -> User:
        """Register new user."""
        if await self.repo.email_exists(session, user_data.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        hashed_password = auth.hash_password(user_data.password)
        return await self.repo.create(
            session,
            email=user_data.email,
            full_name=user_data.full_name,
            hashed_password=hashed_password,
            email_verified=email_verified,
        )

    async def authenticate(
        self, session: AsyncSession, credentials: schemas.LoginRequest
    ) -> User:
        """Authenticate user with email and password."""
        user = await self.repo.get_by_email(session, credentials.email)

        if not user or not auth.verify_password(credentials.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.email_verified:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Please verify your email before logging in",
            )

        return user

    async def get_by_email(self, session: AsyncSession, email: str) -> User | None:
        """Get user by email."""
        return await self.repo.get_by_email(session, email)

    async def get_all(self, session: AsyncSession) -> list[User]:
        """Get all users (admin only)."""
        return await self.repo.get_all(session)

    async def update_role(
        self,
        session: AsyncSession,
        user_id: int,
        role: str,
        current_user: User,
    ) -> User:
        """Update a user's role while ensuring at least one admin remains."""
        if not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can update user roles",
            )

        if role not in {"user", "admin"}:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Role must be 'user' or 'admin'",
            )

        if role == "user" and user_id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="En az bir admin bulunmalıdır",
            )

        if role == "user":
            admin_result = await session.execute(
                select(User)
                .where(User.is_admin.is_(True))
                .with_for_update()
            )
            admins = admin_result.scalars().all()
            if len(admins) <= 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="En az bir admin bulunmalıdır",
                )

        user = await self.repo.get_by_id(session, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        user.is_admin = role == "admin"
        await session.commit()
        await session.refresh(user)
        return user

    async def make_admin(
        self, session: AsyncSession, email: str, current_user: User
    ) -> User:
        """Make a user admin. Only admins can do this."""
        if not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can promote users",
            )
        user = await self.repo.get_by_email(session, email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        return await self.update_role(session, user.id, "admin", current_user)


class TrackService:
    """Handle track-related business logic."""

    def __init__(
        self,
        storage_service: BaseStorageService,
    ) -> None:
        self.repo = TrackRepository()
        self.storage_service = storage_service

    async def create_track(
        self, session: AsyncSession, track_data: schemas.TrackCreate
    ) -> Track:
        """Create new track."""
        if (
            track_data.album_id is not None
            and await session.get(Album, track_data.album_id) is None
        ):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Album not found",
            )
        return await self.repo.create(
            session,
            title=track_data.title,
            artist=track_data.artist,
            price=track_data.price,
            cover_image_url=track_data.cover_image_url,
            album_id=track_data.album_id,
            preview_url=track_data.preview_url,
            full_file_path=track_data.full_file_path,
            is_free=track_data.is_free,
            free_download_url=track_data.free_download_url,
            category=track_data.category,
        )

    async def get_track(self, session: AsyncSession, track_id: int) -> Track:
        """Get track by ID."""
        track = await self.repo.get_by_id(session, track_id)
        if not track:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Track not found"
            )
        return track

    async def get_all_tracks(self, session: AsyncSession) -> list[Track]:
        """Get all tracks."""
        return await self.repo.get_all(session)

    async def update_track(
        self,
        session: AsyncSession,
        track_id: int,
        track_data: schemas.TrackUpdate,
    ) -> Track:
        """Update a track record."""
        track = await self.get_track(session, track_id)
        update_values: dict[str, object] = track_data.model_dump(exclude_unset=True)
        if not update_values:
            return track

        album_id = update_values.get("album_id")
        if album_id is not None and await session.get(Album, album_id) is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Album not found",
            )

        category_value = update_values.get("category")
        if isinstance(category_value, str):
            update_values["category"] = category_value.strip().lower()

        is_free_value = update_values.get("is_free", track.is_free)
        effective_is_free = is_free_value if isinstance(is_free_value, bool) else track.is_free
        updated_category = update_values.get("category", track.category)
        effective_category = updated_category if isinstance(updated_category, str) else track.category
        updated_price = update_values.get("price", track.price)
        effective_price = updated_price if isinstance(updated_price, (int, float)) else track.price

        if effective_is_free and effective_category == "edit":
            effective_category = "remix"
            update_values["category"] = effective_category

        if effective_is_free and effective_category not in schemas.FREE_TRACK_CATEGORIES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Free tracks must use category: remix, simple-pack, or vst",
            )

        if not effective_is_free and effective_category not in schemas.PAID_TRACK_CATEGORIES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Paid tracks must use category: edit or remix",
            )

        if effective_price is not None and effective_price < 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Price must be greater than 0",
            )

        if not effective_is_free and effective_price is not None and effective_price <= 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Price must be greater than 0 for paid tracks",
            )

        if effective_is_free and effective_price is not None and effective_price != 0:
            update_values["price"] = 0.0

        if effective_is_free and "price" not in update_values:
            update_values["price"] = 0.0

        for field, value in update_values.items():
            setattr(track, field, value)

        await session.commit()
        await session.refresh(track)
        return track

    async def delete_track(self, session: AsyncSession, track_id: int) -> None:
        """Delete a track."""
        track = await self.get_track(session, track_id)
        try:
            await self.repo.delete(session, track)
        except IntegrityError as exc:
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Tracks in an order or user library cannot be deleted",
            ) from exc

    async def upload_track(
        self,
        *,
        session: AsyncSession,
        title: str,
        artist: str,
        category: str,
        price: float | None,
        album_id: int | None,
        is_free: bool,
        free_download_url: str | None,
        track_file: bytes,
        track_filename: str,
        preview_file: bytes,
        preview_filename: str,
        cover_file: bytes | None,
        cover_filename: str | None,
    ) -> Track:
        """Validate, persist files, and create a track record."""
        if not is_free and price is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Price is required for paid tracks",
            )

        normalized_price = 0.0 if is_free and price is None else (price or 0.0)
        try:
            track_data = schemas.TrackCreate(
                title=title.strip(),
                artist=artist.strip(),
                price=normalized_price,
                album_id=album_id,
                preview_url="/media/previews/pending.mp3",
                full_file_path="/media/tracks/pending.mp3",
                is_free=is_free,
                free_download_url=(
                    free_download_url.strip()
                    if free_download_url
                    else ("/media/tracks/pending.mp3" if is_free else None)
                ),
                category=category.strip().lower(),
            )
        except ValidationError as exc:
            errors = exc.errors(include_url=False, include_context=False)
            detail = "; ".join(
                f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}"
                if error["loc"]
                else error["msg"]
                for error in errors
            )
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=detail,
            ) from exc
        track_bytes = track_file
        preview_bytes = preview_file
        cover_bytes = cover_file
        validate_upload_data(
            track_filename, len(track_bytes), AUDIO_EXTENSIONS,
            MAX_TRACK_UPLOAD_BYTES, "Track file",
        )
        validate_upload_data(
            preview_filename, len(preview_bytes), AUDIO_EXTENSIONS,
            MAX_PREVIEW_UPLOAD_BYTES, "Preview file",
        )
        if cover_bytes is not None:
            validate_upload_data(
                cover_filename, len(cover_bytes), IMAGE_EXTENSIONS,
                MAX_COVER_UPLOAD_BYTES, "Cover image",
            )

        track_filename = build_storage_name(track_filename)
        preview_filename = build_storage_name(preview_filename)
        cover_filename = build_storage_name(cover_filename) if cover_bytes is not None and cover_filename else None

        uploaded_objects: list[str] = []
        try:
            track_r2_key = await self.storage_service.upload_file(
                io.BytesIO(track_bytes), "tracks", track_filename
            )
            uploaded_objects.append(f"tracks/{track_filename}")
            preview_r2_url = await self.storage_service.upload_file(
                io.BytesIO(preview_bytes), "previews", preview_filename
            )
            uploaded_objects.append(f"previews/{preview_filename}")
            cover_r2_url = None
            if cover_bytes is not None and cover_filename is not None:
                cover_r2_url = await self.storage_service.upload_file(
                    io.BytesIO(cover_bytes), "covers", cover_filename
                )
                uploaded_objects.append(f"covers/{cover_filename}")

            track_full_url = (
                track_r2_key
                if track_r2_key.startswith("tracks/") or "/" not in track_r2_key
                else track_r2_key
            )
            if (
                not track_full_url.startswith("http")
                and not track_full_url.startswith("/")
                and not track_full_url.startswith("tracks/")
            ):
                track_full_url = f"/{track_r2_key}"

            track_data.cover_image_url = cover_r2_url
            track_data.preview_url = preview_r2_url
            track_data.full_file_path = track_full_url
            if is_free and not free_download_url:
                track_data.free_download_url = track_full_url
            return await self.create_track(session, track_data)
        except Exception as exc:
            await session.rollback()
            for object_key in uploaded_objects:
                try:
                    self.storage_service.delete_file(object_key)
                except Exception as cleanup_error:
                    exc.add_note(
                        f"Could not clean up uploaded object {object_key}: "
                        f"{cleanup_error}"
                    )
            if isinstance(exc, HTTPException):
                raise
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Track upload failed while storing files or saving track metadata",
            ) from exc
