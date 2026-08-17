from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, func, ForeignKey, UniqueConstraint
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Track(Base):
    __tablename__ = 'tracks'

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    artist = Column(String(255), nullable=False, index=True)
    price = Column(Float, nullable=False)
    cover_image_url = Column(String(1024), nullable=True)
    checkout_url = Column(String(1024), nullable=True)
    preview_url = Column(String(1024), nullable=False)
    full_file_path = Column(String(1024), nullable=False)
    is_free = Column(Boolean, default=False, nullable=False)
    free_download_url = Column(String(1024), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Purchase(Base):
    __tablename__ = 'purchases'
    __table_args__ = (
        UniqueConstraint('user_id', 'track_id', name='uq_user_track_purchase'),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    track_id = Column(Integer, ForeignKey('tracks.id', ondelete='CASCADE'), nullable=False, index=True)
    license_type = Column(String(100), nullable=True)
    created_at = Column('purchased_at', DateTime(timezone=True), server_default=func.now())
