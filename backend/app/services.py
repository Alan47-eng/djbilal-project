"""Business logic layer - Service classes for domain operations."""
from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException, status
from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from . import auth, schemas
from .adapters.gumroad import GumroadService
from .interfaces import BaseStorageService
from .models import GumroadSale, User, Track, Purchase
from .repositories import PurchaseDetailData, PurchaseRepository, TrackRepository, UserRepository
from .utils import (
    build_storage_name,
    build_gumroad_checkout_url,
    validate_upload_file,
    AUDIO_EXTENSIONS,
    IMAGE_EXTENSIONS,
    MAX_TRACK_UPLOAD_BYTES,
    MAX_PREVIEW_UPLOAD_BYTES,
    MAX_COVER_UPLOAD_BYTES,
    generate_license_pdf,
)


class UserService:
    """Handle user-related business logic."""

    def __init__(self) -> None:
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

    async def get_by_email(self, session: AsyncSession, email: str) -> User | None:
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
        return await self.repo.create(
            session,
            title=track_data.title,
            artist=track_data.artist,
            price=track_data.price,
            cover_image_url=track_data.cover_image_url,
            external_product_id=track_data.external_product_id,
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
        """Delete a track and its purchase records via cascade."""
        track = await self.get_track(session, track_id)
        await self.repo.delete(session, track)

    async def upload_track(
        self,
        *,
        session: AsyncSession,
        title: str,
        artist: str,
        category: str,
        price: float | None,
        external_product_id: str | None,
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
        validate_upload_file(track_file, AUDIO_EXTENSIONS, MAX_TRACK_UPLOAD_BYTES, "Track file")
        validate_upload_file(preview_file, AUDIO_EXTENSIONS, MAX_PREVIEW_UPLOAD_BYTES, "Preview file")
        if cover_file is not None:
            validate_upload_file(cover_file, IMAGE_EXTENSIONS, MAX_COVER_UPLOAD_BYTES, "Cover image")

        track_filename = build_storage_name(track_file.filename or "")
        preview_filename = build_storage_name(preview_file.filename or "")
        cover_filename = build_storage_name(cover_file.filename or "") if cover_file else None

        track_r2_key = self.storage_service.upload_file(track_file, "tracks", track_filename)
        preview_r2_url = self.storage_service.upload_file(preview_file, "previews", preview_filename)
        cover_r2_url = (
            self.storage_service.upload_file(cover_file, "covers", cover_filename)
            if cover_file and cover_filename
            else None
        )

        track_full_url = track_r2_key if track_r2_key.startswith("tracks/") or "/" not in track_r2_key else track_r2_key
        if not track_full_url.startswith("http") and not track_full_url.startswith("/") and not track_full_url.startswith("tracks/"):
            track_full_url = f"/{track_r2_key}"

        normalized_price = 0.0 if is_free and price is None else (price or 0.0)
        track_data = schemas.TrackCreate(
            title=title.strip(),
            artist=artist.strip(),
            price=normalized_price,
            cover_image_url=cover_r2_url,
            external_product_id=None if is_free else external_product_id,
            preview_url=preview_r2_url,
            full_file_path=track_full_url,
            is_free=is_free,
            free_download_url=free_download_url.strip() if free_download_url else (track_full_url if is_free else None),
            category=category.strip().lower(),
        )
        return await self.create_track(session, track_data)

    async def create_checkout(
        self, session: AsyncSession, track_id: int, current_user: User
    ) -> dict[str, int | str]:
        """Create checkout URL for one paid track."""
        track = await self.get_track(session, track_id)
        if track.is_free:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This track is free to download",
            )

        checkout_url = self._build_gumroad_checkout_url(
            track,
            current_user,
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
    ) -> dict[str, list[int] | list[dict[str, int | str]]]:
        """Create signed Gumroad product links for each paid item in the cart."""
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

        return {
            "track_ids": cart_track_ids,
            "checkout_items": [
                {
                    "track_id": track.id,
                    "checkout_url": self._build_gumroad_checkout_url(
                        track,
                        current_user,
                    ),
                }
                for track in paid_tracks
            ],
        }

    @staticmethod
    def _build_gumroad_checkout_url(track: Track, current_user: User) -> str:
        product_url = (track.external_product_id or "").strip()
        canonical_permalink = GumroadService.normalize_product_permalink(product_url)
        if not canonical_permalink:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"A valid Gumroad product URL is required for track {track.id}",
            )
        if "://" not in product_url:
            product_url = f"https://gumroad.com/l/{product_url}"
        return build_gumroad_checkout_url(
            product_url,
            user_id=current_user.id,
            track_ids=[track.id],
            signature=GumroadService.checkout_signature(
                current_user.id,
                track.id,
                canonical_permalink,
            ),
        )


class PurchaseService:
    """Handle purchase-related business logic."""

    def __init__(
        self,
        gumroad_service: GumroadService,
        track_service: TrackService,
    ) -> None:
        self.repo = PurchaseRepository()
        self.track_service = track_service
        self.gumroad_service = gumroad_service

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

    async def get_user_purchases_detailed(
        self, session: AsyncSession, user_id: int
    ) -> list[PurchaseDetailData]:
        """Get detailed purchase list with track info."""
        return await self.repo.get_user_purchases_detailed(session, user_id)

    async def can_download(
        self, session: AsyncSession, user_id: int, track_id: int
    ) -> bool:
        """Check if user can download track."""
        return await self.repo.has_purchased(session, user_id, track_id)

    async def process_gumroad_ping(
        self,
        session: AsyncSession,
        payload: dict[str, str],
    ) -> dict[str, str | list[int]]:
        """Verify a Gumroad sale and add its paid tracks to the buyer's library."""
        custom_data = self.gumroad_service.extract_checkout_data(payload)
        user_id_value = custom_data.get("user_id")
        track_ids_value = custom_data.get("track_ids")
        signature = custom_data.get("signature")
        if not user_id_value or not track_ids_value or not signature:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing Gumroad cart information",
            )

        try:
            user_id = int(user_id_value)
            resolved_track_ids = [
                int(value.strip()) for value in track_ids_value.split(",")
            ]
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Gumroad cart contains invalid IDs",
            ) from exc
        if (
            user_id <= 0
            or not resolved_track_ids
            or any(track_id <= 0 for track_id in resolved_track_ids)
            or len(set(resolved_track_ids)) != len(resolved_track_ids)
            or len(resolved_track_ids) != 1
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Gumroad cart contains invalid IDs",
            )

        sale = await self.gumroad_service.verify_sale(payload)
        existing_sale = await session.get(GumroadSale, sale["sale_id"])
        if existing_sale:
            return {"status": "duplicate", "purchase_ids": []}

        user = await UserRepository().get_by_id(session, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Gumroad buyer account was not found",
            )

        tracks_result = await session.execute(
            select(Track).where(Track.id.in_(resolved_track_ids))
        )
        tracks_by_id = {track.id: track for track in tracks_result.scalars().all()}
        if len(tracks_by_id) != len(resolved_track_ids):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Gumroad cart references an unknown track",
            )
        tracks = [tracks_by_id[track_id] for track_id in resolved_track_ids]
        if any(track.is_free for track in tracks):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Gumroad cart can only grant paid tracks",
            )

        track = tracks[0]
        track_permalink = GumroadService.normalize_product_permalink(
            track.external_product_id or ""
        )
        sale_permalink = GumroadService.normalize_product_permalink(
            sale["product_permalink"]
        )
        if track_permalink is None or sale_permalink != track_permalink:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Gumroad sale product does not match the requested track",
            )
        expected_cents = int(
            (Decimal(str(track.price)) * 100).quantize(
                Decimal("1"),
                rounding=ROUND_HALF_UP,
            )
        )
        if int(sale["price"]) != expected_cents:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Gumroad sale amount does not match the track price",
            )
        if not self.gumroad_service.verify_checkout_signature(
            user_id=user_id,
            track_id=track.id,
            product_permalink=track_permalink,
            signature=signature,
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Gumroad checkout signature",
            )

        license_type = custom_data.get("license_type")
        session.add(
            GumroadSale(
                sale_id=sale["sale_id"],
                user_id=user_id,
                track_ids=resolved_track_ids,
                paid_cents=int(sale["price"]),
            )
        )
        purchases: list[Purchase] = []
        existing_purchase_ids: list[int] = []
        for resolved_track_id in resolved_track_ids:
            purchase = await self.repo.get_purchase(
                session, user_id, resolved_track_id
            )
            if purchase:
                existing_purchase_ids.append(purchase.id)
                continue
            purchase = Purchase(user_id=user_id, track_id=resolved_track_id)
            if license_type is not None:
                purchase.license_type = license_type
            session.add(purchase)
            purchases.append(purchase)

        try:
            await session.flush()
            purchase_ids = existing_purchase_ids + [
                purchase.id for purchase in purchases
            ]
            await session.commit()
        except IntegrityError:
            await session.rollback()
            if await session.get(GumroadSale, sale["sale_id"]):
                return {"status": "duplicate", "purchase_ids": []}
            raise

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