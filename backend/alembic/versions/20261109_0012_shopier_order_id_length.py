"""Allow Shopier order IDs up to 255 characters.

Revision ID: 20261109_0012
Revises: 20261108_0011
Create Date: 2026-11-09
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261109_0012"
down_revision: Union[str, None] = "20261108_0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if op.get_bind().dialect.name != "sqlite":
        op.alter_column(
            "orders",
            "platform_order_id",
            existing_type=sa.String(length=36),
            type_=sa.String(length=255),
            existing_nullable=False,
        )


def downgrade() -> None:
    if op.get_bind().dialect.name != "sqlite":
        op.alter_column(
            "orders",
            "platform_order_id",
            existing_type=sa.String(length=255),
            type_=sa.String(length=36),
            existing_nullable=False,
        )
