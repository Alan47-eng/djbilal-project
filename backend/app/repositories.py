"""Data access layer - Repository pattern for database operations."""
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import User, Track, Purchase


class BaseRepository:
    """Base repository with common CRUD operations."""
    
    def __init__(self, model):
        self.model = model
    
    async def get_by_id(self, session: AsyncSession, id: int):
        """Get entity by ID."""
        result = await session.execute(select(self.model).where(self.model.id == id))
        return result.scalars().first()
    
    async def get_all(self, session: AsyncSession):
        """Get all entities."""
        result = await session.execute(select(self.model))
        return result.scalars().all()
    
    async def create(self, session: AsyncSession, **kwargs):
        """Create new entity."""
        entity = self.model(**kwargs)
        session.add(entity)
        await session.commit()
        await session.refresh(entity)
        return entity
    
    async def delete(self, session: AsyncSession, entity):
        """Delete entity."""
        await session.delete(entity)
        await session.commit()


class UserRepository(BaseRepository):
    """User data access."""
    
    def __init__(self):
        super().__init__(User)
    
    async def get_by_email(self, session: AsyncSession, email: str) -> Optional[User]:
        """Get user by email."""
        result = await session.execute(select(User).where(User.email == email))
        return result.scalars().first()
    
    async def email_exists(self, session: AsyncSession, email: str) -> bool:
        """Check if email already exists."""
        result = await session.execute(
            select(User.id).where(User.email == email).limit(1)
        )
        return result.scalar_one_or_none() is not None


class TrackRepository(BaseRepository):
    """Track data access."""
    
    def __init__(self):
        super().__init__(Track)


class PurchaseRepository(BaseRepository):
    """Purchase data access."""
    
    def __init__(self):
        super().__init__(Purchase)
    
    async def get_user_purchases(self, session: AsyncSession, user_id: int) -> List[int]:
        """Get list of track IDs purchased by user."""
        result = await session.execute(
            select(Purchase.track_id)
            .where(Purchase.user_id == user_id)
            .order_by(Purchase.created_at.desc())
        )
        return list(result.scalars().all())
    
    async def get_purchase(
        self, session: AsyncSession, user_id: int, track_id: int
    ) -> Optional[Purchase]:
        """Get specific purchase."""
        result = await session.execute(
            select(Purchase).where(
                Purchase.user_id == user_id,
                Purchase.track_id == track_id,
            )
        )
        return result.scalars().first()
    
    async def has_purchased(self, session: AsyncSession, user_id: int, track_id: int) -> bool:
        """Check if user has purchased track."""
        result = await session.execute(
            select(Purchase.id).where(
                Purchase.user_id == user_id,
                Purchase.track_id == track_id,
            ).limit(1)
        )
        return result.scalar_one_or_none() is not None
