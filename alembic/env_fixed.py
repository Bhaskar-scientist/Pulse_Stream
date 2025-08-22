"""Fixed Alembic environment for proper auto-generation."""

from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# Import our models and config
from core.config import settings
from core.database import Base

# Import all models to ensure they're registered
from apps.storage.models.tenant import Tenant
from apps.storage.models.user import User  
from apps.storage.models.event import Event
from apps.storage.models.alert import AlertRule, Alert

# This is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set the database URL from our settings
# IMPORTANT: Use sync URL for Alembic (remove +asyncpg)
sync_database_url = str(settings.database_url).replace("+asyncpg", "")
config.set_main_option("sqlalchemy.url", sync_database_url)

# Add your model's MetaData object here for 'autogenerate' support
target_metadata = Base.metadata


def include_name(name: str, type_: str, parent_names: dict) -> bool:
    """Include only our tables in migrations."""
    if type_ == "table":
        # Only include our application tables
        return name in [
            "tenants",
            "users", 
            "events",
            "alert_rules",
            "alerts",
        ]
    return True


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_name=include_name,
        compare_type=True,           # Enable type comparison
        compare_server_default=True, # Enable default comparison
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    
    # Create engine with sync driver
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_name=include_name,
            compare_type=True,           # Enable type comparison
            compare_server_default=True, # Enable default comparison
            # Enable column comparison options
            render_as_batch=True,        # For better SQL generation
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
