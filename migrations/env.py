
from logging.config import fileConfig
import os
from pathlib import Path

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool
from app.db.base import Base
from app.models import user
from app.models import organization
from app.models import organization_membership
# Load the .env file from the AKMORI project root.
env_path = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(env_path)

# Alembic configuration.
config = context.config

# Build the database URL from environment variables.
database_url = (
    f"postgresql+psycopg://{os.getenv('DB_USER')}:"
    f"{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:"
    f"{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
)

if not all(
    os.getenv(key)
    for key in (
        "DB_USER",
        "DB_PASSWORD",
        "DB_HOST",
        "DB_PORT",
        "DB_NAME",
    )
):
    raise RuntimeError(
        "Database settings are missing. Check the AKMORI .env file."
    )

config.set_main_option("sqlalchemy.url", database_url)

# Configure logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# SQLAlchemy model metadata will be connected here later.

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations without creating a database connection."""
    url = config.get_main_option("sqlalchemy.url")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations using a live database connection."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
