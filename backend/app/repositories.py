"""Data access layer - Repository pattern for database operations."""

from typing import Generic, TypeVar, cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Track, User

ModelT = TypeVar("ModelT", User, Track)


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
