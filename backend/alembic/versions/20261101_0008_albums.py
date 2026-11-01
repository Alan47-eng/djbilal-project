"""Add albums and optional track album association.

Revision ID: 20261101_0008
Revises: 20261030_0007
Create Date: 2026-11-01
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261101_0008"
down_revision: Union[str, None] = "20261030_0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "albums",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("cover_image_url", sa.String(length=1024), nullable=True),
        sa.Column("release_date", sa.Date(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
    )
    op.create_index("ix_albums_id", "albums", ["id"], unique=False)
    op.create_index("ix_albums_title", "albums", ["title"], unique=False)
    op.add_column(
        "tracks",
        sa.Column(
            "album_id",
            sa.Integer(),
            sa.ForeignKey("albums.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_tracks_album_id", "tracks", ["album_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_tracks_album_id", table_name="tracks")
    op.drop_column("tracks", "album_id")
    op.drop_index("ix_albums_title", table_name="albums")
    op.drop_index("ix_albums_id", table_name="albums")
    op.drop_table("albums")
