"""Store a Gumroad checkout URL and product ID on each track.

Revision ID: 20261030_0007
Revises: 20261025_0006
Create Date: 2026-10-30
"""

from typing import Sequence, Union
from urllib.parse import urlparse
import re

from alembic import op
import sqlalchemy as sa


revision: str = "20261030_0007"
down_revision: Union[str, None] = "20261025_0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tracks", sa.Column("gumroad_url", sa.String(length=1024), nullable=True))
    op.add_column("tracks", sa.Column("gumroad_product_id", sa.String(length=255), nullable=True))
    op.create_index(
        "ix_tracks_gumroad_product_id",
        "tracks",
        ["gumroad_product_id"],
        unique=True,
    )

    connection = op.get_bind()
    tracks = sa.table(
        "tracks",
        sa.column("id", sa.Integer()),
        sa.column("external_product_id", sa.String()),
        sa.column("gumroad_url", sa.String()),
    )
    for track_id, external_product_id in connection.execute(
        sa.select(tracks.c.id, tracks.c.external_product_id)
    ):
        if not external_product_id:
            continue
        value = external_product_id.strip()
        if "://" in value:
            parsed = urlparse(value)
            host = (parsed.hostname or "").lower()
            parts = [part for part in parsed.path.split("/") if part]
            if (
                parsed.scheme == "https"
                and (host == "gumroad.com" or host.endswith(".gumroad.com"))
                and len(parts) == 2
                and parts[0] == "l"
                and re.fullmatch(r"[A-Za-z0-9_-]+", parts[1])
            ):
                gumroad_url = f"https://{parsed.netloc}/l/{parts[1]}"
            else:
                continue
        elif re.fullmatch(r"[A-Za-z0-9_-]+", value):
            gumroad_url = f"https://djbilal.gumroad.com/l/{value}"
        else:
            continue
        connection.execute(
            tracks.update()
            .where(tracks.c.id == track_id)
            .values(gumroad_url=gumroad_url)
        )


def downgrade() -> None:
    op.drop_index("ix_tracks_gumroad_product_id", table_name="tracks")
    op.drop_column("tracks", "gumroad_product_id")
    op.drop_column("tracks", "gumroad_url")
