from alembic import context

# Import your models and Base here
import asyncio
import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine

# Add the app directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

from app.core.database import Base
from app.models import (
    organization,  # noqa: F401
    user,  # noqa: F401
    location,  # noqa: F401
    asset,  # noqa: F401
    inventory,  # noqa: F401
    preventive_maintenance,  # noqa: F401
    work_order,  # noqa: F401
    audit_log,  # noqa: F401
    user_group,  # noqa: F401
    user_group_member,  # noqa: F401
    scheduler_control,  # noqa: F401
)

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# Get database URL from environment
database_url = os.getenv("DATABASE_URL")
if database_url:
    config.set_main_option("sqlalchemy.url", database_url)

def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # Handle both sync and async URLs
    url = config.get_main_option("sqlalchemy.url")
    if url and url.startswith("postgresql+asyncpg://"):
        # Convert async URL to sync for alembic
        url = url.replace("postgresql+asyncpg://", "postgresql://")

    connectable = create_engine(
        url,
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
