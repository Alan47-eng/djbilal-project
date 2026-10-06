"""Allow full Gumroad product URLs in track metadata.

Revision ID: 20261006_0003
Revises: 20261006_0002
Create Date: 2026-10-06
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261006_0003"
down_revision: Union[str, None] = "20261006_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    connection = op.get_bind()
    tracks = sa.table(
        "tracks",
        sa.column("id", sa.Integer()),
        sa.column("external_product_id", sa.String()),
    )
    for track_id, product_id in connection.execute(
        sa.select(tracks.c.id, tracks.c.external_product_id)
    ):
        if product_id and product_id.isdecimal():
            connection.execute(
                tracks.update()
                .where(tracks.c.id == track_id)
                .values(external_product_id=None)
            )

    with op.batch_alter_table("tracks") as batch_op:
        batch_op.alter_column(
            "external_product_id",
            existing_type=sa.String(length=255),
            type_=sa.String(length=1024),
            existing_nullable=True,
        )


def downgrade() -> None:
    with op.batch_alter_table("tracks") as batch_op:
        batch_op.alter_column(
            "external_product_id",
            existing_type=sa.String(length=1024),
            type_=sa.String(length=255),
            existing_nullable=True,
        )
