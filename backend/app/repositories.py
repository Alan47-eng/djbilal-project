"""Data access layer - Repository pattern for database operations."""

from datetime import datetime
from typing import Generic, TypeVar, TypedDict, cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Purchase, Track, User

ModelT = TypeVar("ModelT", User, Track, Purchase)


class PurchaseDetailData(TypedDict):
    id: int
    track_id: int
    track_title: str
    track_artist: str
    cover_image_url: str | None
    download_url: str
    license_pdf_url: str
    license_type: str | None
    purchased_at: datetime | None


class BaseRepository(Generic[ModelT]):
    """Base repository with common CRUD operations."""

    def __init__(self, model: type[ModelT]) -> None:
        self.model = model

    async def get_by_id(self, session: AsyncSession, entity_id: int) -> ModelT | None:
        """Get entity by ID."""
        result = await session.execute(
            select(self.model).where(self.model.__table__.c.id == entity_id)
        )
        return result.scalars().first()

    async def get_all(self, session: AsyncSession) -> list[ModelT]:
        """Get all entities."""
        result = await session.execute(select(self.model))
        return list(result.scalars().all())

    async def create(self, session: AsyncSession, **kwargs: object) -> ModelT:
        """Create new entity."""
        entity = cast(ModelT, self.model(**kwargs))
        session.add(entity)
        await session.commit()
        await session.refresh(entity)
        return entity

    async def delete(self, session: AsyncSession, entity: ModelT) -> None:
        """Delete entity."""
        await session.delete(entity)
        await session.commit()


class UserRepository(BaseRepository[User]):
    """User data access."""

    def __init__(self) -> None:
        super().__init__(User)

    async def get_by_email(self, session: AsyncSession, email: str) -> User | None:
        """Get user by email."""
        result = await session.execute(select(User).where(User.email == email))
        return result.scalars().first()

    async def email_exists(self, session: AsyncSession, email: str) -> bool:
        """Check if email already exists."""
        result = await session.execute(
            select(User.id).where(User.email == email).limit(1)
        )
        return result.scalar_one_or_none() is not None


class TrackRepository(BaseRepository[Track]):
    """Track data access."""

    def __init__(self) -> None:
        super().__init__(Track)


class PurchaseRepository(BaseRepository[Purchase]):
    """Purchase data access."""

    def __init__(self) -> None:
        super().__init__(Purchase)

    async def get_user_purchases(self, session: AsyncSession, user_id: int) -> list[int]:
        """Get list of track IDs purchased by user."""
        result = await session.execute(
            select(Purchase.track_id)
            .where(Purchase.user_id == user_id)
            .order_by(Purchase.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_purchase(
        self, session: AsyncSession, user_id: int, track_id: int
    ) -> Purchase | None:
        """Get specific purchase."""
        result = await session.execute(
            select(Purchase).where(
                Purchase.user_id == user_id,
                Purchase.track_id == track_id,
            )
        )
        return result.scalars().first()

    async def get_purchase_with_track_for_user(
        self, session: AsyncSession, user_id: int, purchase_id: int
    ) -> tuple[Purchase, Track] | None:
        """Get one purchase (owned by user) with its track."""
        result = await session.execute(
            select(Purchase, Track)
            .join(Track, Purchase.track_id == Track.id)
            .where(
                Purchase.id == purchase_id,
                Purchase.user_id == user_id,
            )
        )
        row = result.first()
        return (row[0], row[1]) if row is not None else None

    async def has_purchased(self, session: AsyncSession, user_id: int, track_id: int) -> bool:
        """Check if user has purchased track."""
        result = await session.execute(
            select(Purchase.id)
            .where(
                Purchase.user_id == user_id,
                Purchase.track_id == track_id,
            )
            .limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def get_user_purchases_detailed(
        self, session: AsyncSession, user_id: int
    ) -> list[PurchaseDetailData]:
        """Get detailed purchase list with track info for a user."""
        result = await session.execute(
            select(Purchase, Track)
            .join(Track, Purchase.track_id == Track.id)
            .where(Purchase.user_id == user_id)
            .order_by(Purchase.created_at.desc())
        )
        rows = result.all()
        return [
            {
                "id": purchase.id,
                "track_id": track.id,
                "track_title": track.title,
                "track_artist": track.artist,
                "cover_image_url": track.cover_image_url,
                "download_url": track.full_file_path,
                "license_pdf_url": f"/purchases/{purchase.id}/license-pdf",
                "license_type": purchase.license_type,
                "purchased_at": purchase.created_at,
            }
            for purchase, track in rows
        ]
