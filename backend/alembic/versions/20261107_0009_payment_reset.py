"""Remove legacy payment integration schema.

Revision ID: 20261107_0009
Revises: 20261101_0008
Create Date: 2026-11-07
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261107_0009"
down_revision: Union[str, None] = "20261101_0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("ix_gumroad_sales_user_id", table_name="gumroad_sales")
    op.drop_table("gumroad_sales")
    op.drop_index("ix_purchases_user_id", table_name="purchases")
    op.drop_index("ix_purchases_track_id", table_name="purchases")
    op.drop_index("ix_purchases_id", table_name="purchases")
    op.drop_table("purchases")

    op.drop_index("ix_tracks_gumroad_product_id", table_name="tracks")
    with op.batch_alter_table("tracks") as batch_op:
        batch_op.drop_column("gumroad_product_id")
        batch_op.drop_column("gumroad_url")
        batch_op.drop_column("external_product_id")


def downgrade() -> None:
    with op.batch_alter_table("tracks") as batch_op:
        batch_op.add_column(sa.Column("external_product_id", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("gumroad_url", sa.String(length=1024), nullable=True))
        batch_op.add_column(sa.Column("gumroad_product_id", sa.String(length=255), nullable=True))
    op.create_index(
        "ix_tracks_gumroad_product_id",
        "tracks",
        ["gumroad_product_id"],
        unique=True,
    )

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
    op.create_table(
        "gumroad_sales",
        sa.Column("sale_id", sa.String(length=255), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("track_ids", sa.JSON(), nullable=False),
        sa.Column("paid_cents", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("sale_id"),
    )
    op.create_index("ix_gumroad_sales_user_id", "gumroad_sales", ["user_id"], unique=False)
