from sqlalchemy import (
    Boolean,
    BigInteger,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=True)
    hashed_password = Column(String(255), nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    email_verified = Column(Boolean, default=True, server_default="true", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Album(Base):
    __tablename__ = "albums"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    cover_image_url = Column(String(1024), nullable=True)
    release_date = Column(Date, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Track(Base):
    __tablename__ = 'tracks'

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    artist = Column(String(255), nullable=False, index=True)
    price = Column(Float, nullable=False)
    cover_image_url = Column(String(1024), nullable=True)
    album_id = Column(Integer, ForeignKey("albums.id", ondelete="SET NULL"), nullable=True, index=True)
    preview_url = Column(String(1024), nullable=False)
    full_file_path = Column(String(1024), nullable=False)
    is_free = Column(Boolean, default=False, nullable=False)
    free_download_url = Column(String(1024), nullable=True)
    category = Column(String(50), nullable=False, default="edit")
    shopier_product_id = Column(String(255), nullable=True, unique=True, index=True)
    shopier_product_url = Column(String(1024), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
class ProfilePhoto(Base):
    __tablename__ = "profile_photos"

    id = Column(Integer, primary_key=True)
    image_url = Column(String(1024), nullable=False)


class PendingRegistration(Base):
    __tablename__ = "pending_registrations"

    email = Column(String(255), primary_key=True)
    full_name = Column(String(255), nullable=True)
    hashed_password = Column(String(255), nullable=False)
    verification_code_hash = Column(String(64), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    attempts = Column(Integer, default=0, nullable=False)


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'paid_pending_delivery', 'success', 'failed')",
            name="ck_orders_status",
        ),
        CheckConstraint("total_amount_minor > 0", name="ck_orders_total_amount_positive"),
        CheckConstraint("currency IN (0, 1, 2)", name="ck_orders_currency"),
    )

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    platform_order_id = Column(String(255), nullable=False, unique=True)
    total_amount_minor = Column(BigInteger, nullable=False)
    currency = Column(SmallInteger, nullable=False)
    status = Column(String(32), nullable=False, default="pending", server_default="pending", index=True)
    shopier_payment_id = Column(String(255), nullable=True, unique=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    paid_at = Column(DateTime(timezone=True), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)


class OrderItem(Base):
    __tablename__ = "order_items"
    __table_args__ = (
        UniqueConstraint("order_id", "track_id", name="uq_order_item_track"),
        CheckConstraint("price_minor > 0", name="ck_order_item_price_positive"),
    )

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    track_id = Column(Integer, ForeignKey("tracks.id", ondelete="RESTRICT"), nullable=False, index=True)
    track_title = Column(String(255), nullable=False)
    price_minor = Column(Integer, nullable=False)


class Purchase(Base):
    __tablename__ = "purchases"
    __table_args__ = (
        UniqueConstraint("user_id", "track_id", name="uq_user_track_purchase"),
    )

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    track_id = Column(Integer, ForeignKey("tracks.id", ondelete="RESTRICT"), nullable=False, index=True)
    purchased_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class ShopierWebhookEvent(Base):
    __tablename__ = "shopier_webhook_events"

    id = Column(String(255), primary_key=True)
    event = Column(String(100), nullable=False)
    shopier_order_id = Column(String(255), nullable=False, index=True)
    received_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
