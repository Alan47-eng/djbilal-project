"""Initial baseline schema.

Revision ID: 20260930_0001
Revises:
Create Date: 2026-09-30
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260930_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("is_admin", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_id", "users", ["id"], unique=False)

    op.create_table(
        "tracks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("artist", sa.String(length=255), nullable=False),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("cover_image_url", sa.String(length=1024), nullable=True),
        sa.Column("checkout_url", sa.String(length=1024), nullable=True),
        sa.Column("lemon_variant_id", sa.Integer(), nullable=True),
        sa.Column("preview_url", sa.String(length=1024), nullable=False),
        sa.Column("full_file_path", sa.String(length=1024), nullable=False),
        sa.Column("is_free", sa.Boolean(), nullable=False),
        sa.Column("free_download_url", sa.String(length=1024), nullable=True),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tracks_artist", "tracks", ["artist"], unique=False)
    op.create_index("ix_tracks_id", "tracks", ["id"], unique=False)
    op.create_index("ix_tracks_title", "tracks", ["title"], unique=False)

    op.create_table(
        "purchases",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("track_id", sa.Integer(), nullable=False),
        sa.Column("license_type", sa.String(length=100), nullable=True),
        sa.Column("purchased_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["track_id"], ["tracks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "track_id", name="uq_user_track_purchase"),
    )
    op.create_index("ix_purchases_id", "purchases", ["id"], unique=False)
    op.create_index("ix_purchases_track_id", "purchases", ["track_id"], unique=False)
    op.create_index("ix_purchases_user_id", "purchases", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_purchases_user_id", table_name="purchases")
    op.drop_index("ix_purchases_track_id", table_name="purchases")
    op.drop_index("ix_purchases_id", table_name="purchases")
    op.drop_table("purchases")

    op.drop_index("ix_tracks_title", table_name="tracks")
    op.drop_index("ix_tracks_id", table_name="tracks")
    op.drop_index("ix_tracks_artist", table_name="tracks")
    op.drop_table("tracks")

    op.drop_index("ix_users_id", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
