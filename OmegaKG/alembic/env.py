import asyncio
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context
from omega_kg.settings import settings

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# for 'autogenerate' support
from omega_kg.database.base import Base
from omega_kg.models import terminal, validation  # noqa: F401

# Import other models here if they exist and use the shared Base
target_metadata = Base.metadata

# Set the database URL from settings
print(f"DEBUG: Alembic using database URL: {settings.database_url}")
config.set_main_option("sqlalchemy.url", settings.database_url)


def run_migrations_offline() -> None:
    """
    Run Alembic migrations without a live database connection.

    Configures the migration context using the configured SQLAlchemy URL and executes the migrations, emitting SQL to the script output instead of applying changes to a database.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table="alembic_version_omegakg",
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """
    Configure the Alembic migration context with the provided DB connection and execute migrations inside a transaction.

    Parameters:
        connection (sqlalchemy.engine.Connection): An open SQLAlchemy connection used by Alembic to run migrations.
    """
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        version_table="alembic_version_omegakg",
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """
    Run Alembic migrations against the configured database using an asynchronous SQLAlchemy engine.

    Creates an async engine from the Alembic configuration, opens an asynchronous connection, executes the migration operations within that connection, and disposes the engine when complete.
    """

    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """
    Run Alembic migrations in online mode using an asynchronous engine.
    """
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
