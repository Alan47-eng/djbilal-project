"""Store Shopier REST product mappings and webhook IDs.

Revision ID: 20261108_0011
Revises: 20261107_0010
Create Date: 2026-11-08
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261108_0011"
down_revision: Union[str, None] = "20261107_0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tracks", sa.Column("shopier_product_id", sa.String(length=255), nullable=True)
    )
    op.add_column(
        "tracks", sa.Column("shopier_product_url", sa.String(length=1024), nullable=True)
    )
    op.create_index(
        "ix_tracks_shopier_product_id",
        "tracks",
        ["shopier_product_id"],
        unique=True,
    )
    op.create_table(
        "shopier_webhook_events",
        sa.Column("id", sa.String(length=255), nullable=False),
        sa.Column("event", sa.String(length=100), nullable=False),
        sa.Column("shopier_order_id", sa.String(length=255), nullable=False),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_shopier_webhook_events_shopier_order_id",
        "shopier_webhook_events",
        ["shopier_order_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_shopier_webhook_events_shopier_order_id",
        table_name="shopier_webhook_events",
    )
    op.drop_table("shopier_webhook_events")
    op.drop_index("ix_tracks_shopier_product_id", table_name="tracks")
    op.drop_column("tracks", "shopier_product_url")
    op.drop_column("tracks", "shopier_product_id")
