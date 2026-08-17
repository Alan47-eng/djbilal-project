"""Business logic layer - Service classes for domain operations."""
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from . import auth, schemas
from .models import User, Track, Purchase
from .repositories import UserRepository, TrackRepository, PurchaseRepository


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
            preview_url=track_data.preview_url,
            full_file_path=track_data.full_file_path,
            is_free=track_data.is_free,
            free_download_url=track_data.free_download_url,
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
        # Verify track exists
        await self.track_service.get_track(session, track_id)
        
        # Check if already purchased
        existing = await self.repo.get_purchase(session, user_id, track_id)
        if existing:
            return existing
        
        # Record new purchase
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
