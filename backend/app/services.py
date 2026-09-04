"""Business logic layer - Service classes for domain operations."""
import os
from typing import Optional
from fastapi import HTTPException, status
from fastapi import Request, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from . import auth, schemas
from .models import User, Track, Purchase
from .repositories import UserRepository, TrackRepository, PurchaseRepository
from .utils import (
    TRACK_UPLOAD_DIR,
    PREVIEW_UPLOAD_DIR,
    COVER_UPLOAD_DIR,
    build_media_url,
    build_storage_name,
    save_upload_file,
    build_checkout_url,
    extract_custom_data,
    create_lemonsqueezy_checkout,
    validate_upload_file,
    AUDIO_EXTENSIONS,
    IMAGE_EXTENSIONS,
    MAX_TRACK_UPLOAD_BYTES,
    MAX_PREVIEW_UPLOAD_BYTES,
    MAX_COVER_UPLOAD_BYTES,
    is_successful_payment_event,
    generate_license_pdf,
)


class UserService:
    """Handle user-related business logic."""

    def __init__(self):
        self.repo = UserRepository()

    async def register(self, session: AsyncSession, user_data: schemas.UserCreate) -> User:
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
            hashed_password=hashed_password
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

        return user

    async def get_by_email(self, session: AsyncSession, email: str) -> Optional[User]:
        """Get user by email."""
        return await self.repo.get_by_email(session, email)

    async def get_all(self, session: AsyncSession) -> list[User]:
        """Get all users (admin only)."""
        return await self.repo.get_all(session)

    async def make_admin(self, session: AsyncSession, email: str, current_user: User) -> User:
        """Make a user admin. Only admins can do this."""
        if not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can promote users"
            )

        user = await self.repo.get_by_email(session, email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        user.is_admin = True
        await session.commit()
        await session.refresh(user)
        return user


class TrackService:
    """Handle track-related business logic."""

    def __init__(self):
        self.repo = TrackRepository()

    async def create_track(
        self, session: AsyncSession, track_data: schemas.TrackCreate
    ) -> Track:
        """Create new track."""
        return await self.repo.create(
            session,
            title=track_data.title,
            artist=track_data.artist,
            price=track_data.price,
            cover_image_url=track_data.cover_image_url,
            checkout_url=track_data.checkout_url,
            lemon_variant_id=track_data.lemon_variant_id,
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
        update_values = track_data.model_dump(exclude_unset=True)
        if not update_values:
            return track

        if "category" in update_values:
            update_values["category"] = update_values["category"].strip().lower()

        effective_is_free = update_values.get("is_free", track.is_free)
        effective_category = update_values.get("category", track.category)
        effective_price = update_values.get("price", track.price)

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
        """Delete a track and its purchase records via cascade."""
        track = await self.get_track(session, track_id)
        await self.repo.delete(session, track)

    async def upload_track(
        self,
        *,
        session: AsyncSession,
        request: Request,
        title: str,
        artist: str,
        category: str,
        price: float | None,
        checkout_url: str | None,
        lemon_variant_id: int | None,
        is_free: bool,
        free_download_url: str | None,
        track_file: UploadFile,
        preview_file: UploadFile,
        cover_file: UploadFile | None,
    ) -> Track:
        """Validate, persist files, and create a track record."""
        if not is_free and price is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Price is required for paid tracks",
            )
        if not is_free and lemon_variant_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Lemon variant ID is required for paid tracks",
            )

        validate_upload_file(track_file, AUDIO_EXTENSIONS, MAX_TRACK_UPLOAD_BYTES, "Track file")
        validate_upload_file(preview_file, AUDIO_EXTENSIONS, MAX_PREVIEW_UPLOAD_BYTES, "Preview file")
        if cover_file is not None:
            validate_upload_file(cover_file, IMAGE_EXTENSIONS, MAX_COVER_UPLOAD_BYTES, "Cover image")

        track_filename = build_storage_name(track_file.filename)
        preview_filename = build_storage_name(preview_file.filename)
        cover_filename = build_storage_name(cover_file.filename) if cover_file else None

        await save_upload_file(track_file, TRACK_UPLOAD_DIR / track_filename, MAX_TRACK_UPLOAD_BYTES)
        await save_upload_file(preview_file, PREVIEW_UPLOAD_DIR / preview_filename, MAX_PREVIEW_UPLOAD_BYTES)
        if cover_file and cover_filename:
            await save_upload_file(cover_file, COVER_UPLOAD_DIR / cover_filename, MAX_COVER_UPLOAD_BYTES)

        track_full_url = build_media_url(request, "tracks", track_filename)
        normalized_price = 0.0 if is_free and price is None else (price or 0.0)
        checkout_url_value = None if is_free else (checkout_url.strip() if checkout_url else None)
        track_data = schemas.TrackCreate(
            title=title.strip(),
            artist=artist.strip(),
            price=normalized_price,
            cover_image_url=build_media_url(request, "covers", cover_filename) if cover_filename else None,
            checkout_url=checkout_url_value,
            lemon_variant_id=None if is_free else lemon_variant_id,
            preview_url=build_media_url(request, "previews", preview_filename),
            full_file_path=track_full_url,
            is_free=is_free,
            free_download_url=free_download_url.strip() if free_download_url else (track_full_url if is_free else None),
            category=category.strip().lower(),
        )
        return await self.create_track(session, track_data)

    async def create_checkout(self, session: AsyncSession, track_id: int, current_user: User) -> dict:
        """Create checkout URL for one paid track."""
        track = await self.get_track(session, track_id)
        if track.is_free:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This track is free to download",
            )

        if track.lemon_variant_id:
            checkout_url = await create_lemonsqueezy_checkout(
                variant_quantities=[{"variant_id": track.lemon_variant_id, "quantity": 1}],
                custom_data={
                    "track_id": str(track.id),
                    "track_ids": str(track.id),
                    "user_id": str(current_user.id),
                },
                email=current_user.email,
            )
        else:
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

    async def create_cart_checkout(
        self,
        session: AsyncSession,
        track_ids: list[int],
        current_user: User,
    ) -> dict:
        """Create checkout URL for paid tracks in cart using Lemon Squeezy cart variant."""
        tracks_result = await session.execute(
            select(Track).where(Track.id.in_(track_ids))
        )
        tracks_by_id = {track.id: track for track in tracks_result.scalars().all()}
        missing_ids = [track_id for track_id in track_ids if track_id not in tracks_by_id]
        if missing_ids:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tracks not found: {', '.join(str(track_id) for track_id in missing_ids)}",
            )

        selected_tracks = [tracks_by_id[track_id] for track_id in track_ids]
        paid_tracks = [track for track in selected_tracks if not track.is_free]
        if not paid_tracks:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cart must include at least one paid track",
            )

        cart_track_ids = [track.id for track in paid_tracks]

        # 1. Sepetteki toplam tutari hesapla ve Cent cinsine cevir ($3.50 -> 350)
        total_price = sum(float(track.price or 0) for track in paid_tracks)
        total_cents = max(int(round(total_price * 100)), 100)

        # 2. Railway'e tanimladigin Joker Varyant ID'sini al
        cart_variant_id = os.getenv("LEMON_SQUEEZY_CART_VARIANT_ID")
        if not cart_variant_id:
            cart_variant_id = paid_tracks[0].lemon_variant_id

        if not cart_variant_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="LEMON_SQUEEZY_CART_VARIANT_ID is not configured in environment.",
            )

        # 3. Lemon Squeezy'ye tek bir joker varyant ve ozel sepet tutarini gonder
        custom_data = {
            "track_ids": ",".join(str(track_id) for track_id in cart_track_ids),
            "user_id": str(current_user.id),
        }

        try:
            checkout_url = await create_lemonsqueezy_checkout(
                variant_quantities=[{"variant_id": int(cart_variant_id), "quantity": 1}],
                custom_data=custom_data,
                email=current_user.email,
                custom_price=total_cents,
            )
        except TypeError:
            checkout_url = await create_lemonsqueezy_checkout(
                variant_quantities=[{"variant_id": int(cart_variant_id), "quantity": 1}],
                custom_data=custom_data,
                email=current_user.email,
            )

        return {
            "track_ids": cart_track_ids,
            "checkout_url": checkout_url,
        }


class PurchaseService:
    """Handle purchase-related business logic."""

    def __init__(self):
        self.repo = PurchaseRepository()
        self.track_service = TrackService()

    async def get_user_purchases(self, session: AsyncSession, user_id: int) -> list[int]:
        """Get user's purchased track IDs."""
        return await self.repo.get_user_purchases(session, user_id)

    async def record_purchase(
        self, session: AsyncSession, user_id: int, track_id: int, license_type: str | None = None
    ) -> Purchase:
        """Record a purchase."""
        await self.track_service.get_track(session, track_id)

        existing = await self.repo.get_purchase(session, user_id, track_id)
        if existing:
            return existing

        return await self.repo.create(
            session,
            user_id=user_id,
            track_id=track_id,
            license_type=license_type,
        )

    async def get_user_purchases_detailed(self, session: AsyncSession, user_id: int) -> list[dict]:
        """Get detailed purchase list with track info."""
        return await self.repo.get_user_purchases_detailed(session, user_id)

    async def can_download(
        self, session: AsyncSession, user_id: int, track_id: int
    ) -> bool:
        """Check if user can download track."""
        return await self.repo.has_purchased(session, user_id, track_id)

    async def process_successful_payment_payload(
        self,
        session: AsyncSession,
        payload: dict,
    ) -> dict:
        """Persist purchases for successful Lemon Squeezy webhook payload."""
        if not is_successful_payment_event(payload):
            return {"status": "ignored"}

        custom_data = extract_custom_data(payload)
        track_id = custom_data.get("track_id")
        track_ids = custom_data.get("track_ids")
        user_id = custom_data.get("user_id")
        license_type = custom_data.get("license_type")

        if not user_id or (not track_id and not track_ids):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing custom data",
            )

        resolved_track_ids: list[int] = []
        if track_ids:
            for raw_id in track_ids.split(","):
                value = raw_id.strip()
                if not value:
                    continue
                resolved_track_ids.append(int(value))
        elif track_id:
            resolved_track_ids.append(int(track_id))

        if not resolved_track_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid track IDs in custom data",
            )

        purchase_ids: list[int] = []
        for resolved_track_id in resolved_track_ids:
            purchase = await self.record_purchase(session, int(user_id), resolved_track_id, license_type)
            purchase_ids.append(purchase.id)
        return {"status": "ok", "purchase_ids": purchase_ids}

    async def generate_license_document(
        self,
        session: AsyncSession,
        current_user: User,
        purchase_id: int,
    ) -> tuple[bytes, str]:
        """Generate PDF license file for a user's purchase."""
        row = await self.repo.get_purchase_with_track_for_user(session, current_user.id, purchase_id)
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Purchase not found",
            )

        purchase, track = row
        buyer_name = (current_user.full_name or "").strip() or current_user.email
        pdf_bytes = generate_license_pdf(
            purchase_id=purchase.id,
            buyer_name=buyer_name,
            buyer_email=current_user.email,
            track_title=track.title,
            track_artist=track.artist,
            license_type=purchase.license_type or "Standard",
            purchased_at=purchase.created_at,
        )
        filename = f"license-{purchase.id}.pdf"
        return pdf_bytes, filename