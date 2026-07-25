from __future__ import annotations
import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://djbilal:password@postgres:5432/djbilal_db")

# Async engine and sessionmaker for SQLAlchemy
engine = create_async_engine(DATABASE_URL, echo=False, future=True)
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session

async def test_connection() -> bool:
    """Run a lightweight query to verify DB connectivity."""
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    return True
