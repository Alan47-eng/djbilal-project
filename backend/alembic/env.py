import os
import sys
import asyncio
from logging.config import fileConfig

from alembic import context
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import pool
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import create_async_engine

backend_path = os.path.dirname(os.path.dirname(__file__))
if backend_path not in sys.path:
    sys.path.append(backend_path)

from app.models import Base
from app.database import DATABASE_URL

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata
config.set_main_option("sqlalchemy.url", DATABASE_URL.replace("%", "%%"))

BASELINE_REVISION = "20260930_0001"
BASELINE_TABLE_COLUMNS = {
    "users": {"id", "email", "hashed_password"},
    "tracks": {
        "id",
        "title",
        "artist",
        "price",
        "checkout_url",
        "lemon_variant_id",
        "preview_url",
        "full_file_path",
        "is_free",
        "category",
    },
    "purchases": {"id", "user_id", "track_id"},
}


def stamp_existing_baseline(connection) -> None:
    """Stamp pre-Alembic databases only when their schema matches the baseline."""
    inspector = inspect(connection)
    table_names = set(inspector.get_table_names())
    existing_core_tables = table_names.intersection(BASELINE_TABLE_COLUMNS)
    if not existing_core_tables:
        connection.commit()
        return

    if "alembic_version" in table_names:
        has_revision = connection.execute(
            text("SELECT 1 FROM alembic_version LIMIT 1")
        ).first()
        if has_revision:
            connection.commit()
            return

    missing_tables = set(BASELINE_TABLE_COLUMNS).difference(table_names)
    if missing_tables:
        raise RuntimeError(
            "Found an unversioned partial application schema "
            f"(missing tables: {', '.join(sorted(missing_tables))}). "
            "Refusing to stamp the baseline automatically."
        )

    incompatible_tables = []
    for table_name, expected_columns in BASELINE_TABLE_COLUMNS.items():
        actual_columns = {
            column["name"] for column in inspector.get_columns(table_name)
        }
        if not expected_columns.issubset(actual_columns):
            incompatible_tables.append(table_name)
    if incompatible_tables:
        raise RuntimeError(
            "Found unversioned application tables that do not match migration "
            f"{BASELINE_REVISION} (incompatible tables: "
            f"{', '.join(sorted(incompatible_tables))}). "
            "Refusing to stamp the baseline automatically."
        )

    migration_context = MigrationContext.configure(connection)
    migration_context.stamp(
        ScriptDirectory.from_config(config),
        BASELINE_REVISION,
    )
    connection.commit()


def run_migrations_offline() -> None:
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    stamp_existing_baseline(connection)
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = create_async_engine(DATABASE_URL, poolclass=pool.NullPool)
    try:
        async with connectable.connect() as connection:
            await connection.run_sync(do_run_migrations)
    finally:
        await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
