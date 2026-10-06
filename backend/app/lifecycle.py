import os

from sqlalchemy import select

from . import auth
from .database import async_session, test_connection
from .models import Track, User

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "gbilal1717@gmail.com")
IS_PRODUCTION = os.getenv("ENVIRONMENT", "development").lower() == "production"
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
if not ADMIN_PASSWORD:
    if IS_PRODUCTION:
        raise RuntimeError("ADMIN_PASSWORD must be set in the environment before starting the app")
    ADMIN_PASSWORD = "DjBilal@2026"


async def initialize_application() -> None:
    await test_connection()
    await seed_tracks()
    await seed_admin_user()


async def seed_tracks() -> None:
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
                    preview_url="https://example.com/previews/midnight-drive.mp3",
                    full_file_path="/music/midnight-drive.mp3",
                    category="edit",
                ),
                Track(
                    title="Sunset Echoes",
                    artist="Atlas Bloom",
                    price=2.49,
                    cover_image_url=None,
                    preview_url="https://example.com/previews/sunset-echoes.mp3",
                    full_file_path="/music/sunset-echoes.mp3",
                    category="edit",
                ),
                Track(
                    title="City Lights",
                    artist="Luna Harbor",
                    price=1.49,
                    cover_image_url=None,
                    preview_url="https://example.com/previews/city-lights.mp3",
                    full_file_path="/music/city-lights.mp3",
                    category="remix",
                ),
            ])
            await session.commit()


async def seed_admin_user() -> None:
    async with async_session() as session:
        result = await session.execute(select(User).where(User.email == ADMIN_EMAIL))
        admin_user = result.scalars().first()

        if admin_user:
            if not admin_user.is_admin:
                admin_user.is_admin = True
                await session.commit()
            return

        admin_user = User(
            email=ADMIN_EMAIL,
            full_name="DJ Bilal Admin",
            hashed_password=auth.hash_password(ADMIN_PASSWORD),
            is_admin=True,
        )
        session.add(admin_user)
        await session.commit()
