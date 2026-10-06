"""Replace provider-specific checkout metadata with generic product IDs.

Revision ID: 20261006_0002
Revises: 20260930_0001
Create Date: 2026-10-06
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261006_0002"
down_revision: Union[str, None] = "20260930_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("tracks") as batch_op:
        batch_op.alter_column(
            "lemon_variant_id",
            new_column_name="external_product_id",
            existing_type=sa.Integer(),
            type_=sa.String(length=255),
            existing_nullable=True,
        )
        batch_op.drop_column("checkout_url")

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


def downgrade() -> None:
    op.drop_index("ix_gumroad_sales_user_id", table_name="gumroad_sales")
    op.drop_table("gumroad_sales")
    with op.batch_alter_table("tracks") as batch_op:
        batch_op.add_column(sa.Column("checkout_url", sa.String(length=1024), nullable=True))
        batch_op.drop_column("external_product_id")
        batch_op.add_column(sa.Column("lemon_variant_id", sa.Integer(), nullable=True))
