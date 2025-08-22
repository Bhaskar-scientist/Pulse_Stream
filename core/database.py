"""Database connection and session management for PulseStream."""

import uuid
from typing import Any, AsyncGenerator, Dict, Optional

from sqlalchemy import Column, DateTime, String, Boolean, create_engine, event
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.sql import func

from core.config import settings
from core.logging import get_logger

logger = get_logger(__name__)

# Create sync engine for migrations
sync_engine = create_engine(
    str(settings.database_url),
    echo=settings.database_echo,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    pool_pre_ping=True,
)

# Create async engine for application
async_database_url = str(settings.database_url).replace("postgresql://", "postgresql+asyncpg://")
async_engine = create_async_engine(
    async_database_url,
    echo=settings.database_echo,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    pool_pre_ping=True,
)

# Session factories
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)
AsyncSessionLocal = async_sessionmaker(
    async_engine, class_=AsyncSession, expire_on_commit=False
)


class BaseModel:
    """Base model with common fields and utilities."""
    
    @declared_attr
    def __tablename__(cls) -> str:
        """Generate table name from class name."""
        return cls.__name__.lower()
    
    # Primary key
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        doc="Unique identifier"
    )
    
    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="Record creation timestamp"
    )
    
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        doc="Record last update timestamp"
    )
    
    # Soft delete
    is_deleted = Column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        doc="Soft delete flag"
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }
    
    def update_from_dict(self, data: Dict[str, Any]) -> None:
        """Update model from dictionary."""
        for key, value in data.items():
            if hasattr(self, key) and key not in ('id', 'created_at'):
                setattr(self, key, value)
    
    def __repr__(self) -> str:
        """String representation of the model."""
        return f"<{self.__class__.__name__}(id={self.id})>"


class TenantMixin:
    """Mixin for models that belong to a tenant."""
    
    tenant_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        doc="Tenant identifier for multi-tenant isolation"
    )


# Base class for all models
Base = declarative_base(cls=BaseModel)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Get async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_sync_session():
    """Get sync database session for migrations."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


async def init_database() -> None:
    """Initialize database and create tables."""
    logger.info("Initializing database")
    
    try:
        async with async_engine.begin() as conn:
            # Import all models to ensure they're registered
            from apps.storage.models import tenant, event, alert, user  # noqa: F401
            
            # Create all tables
            await conn.run_sync(Base.metadata.create_all)
            
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error("Failed to initialize database", error=str(e))
        raise


async def close_database() -> None:
    """Close database connections."""
    logger.info("Closing database connections")
    await async_engine.dispose()


def create_database_url(
    host: str = "localhost",
    port: int = 5432,
    username: str = "postgres",
    password: str = "postgres",
    database: str = "pulsestream_dev"
) -> str:
    """Create database URL from components."""
    return f"postgresql://{username}:{password}@{host}:{port}/{database}"


# Event listeners for automatic tenant validation
@event.listens_for(BaseModel, 'before_insert', propagate=True)
def receive_before_insert(mapper, connection, target):
    """Validate tenant isolation before insert."""
    if hasattr(target, 'tenant_id') and not target.tenant_id:
        raise ValueError("tenant_id is required for multi-tenant models")


@event.listens_for(BaseModel, 'before_update', propagate=True)
def receive_before_update(mapper, connection, target):
    """Validate tenant isolation before update."""
    if hasattr(target, 'tenant_id') and not target.tenant_id:
        raise ValueError("tenant_id is required for multi-tenant models")
