"""Tenant model for multi-tenant architecture."""

import secrets
from typing import List, Optional

from sqlalchemy import Column, String, Boolean, Integer, DateTime, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from core.database import Base
from core.constants import MAX_STRING_LENGTH


class Tenant(Base):
    """Tenant model for multi-tenant isolation."""
    
    __tablename__ = "tenants"
    
    # Basic Information
    name = Column(
        String(MAX_STRING_LENGTH),
        nullable=False,
        doc="Human-readable tenant name"
    )
    
    slug = Column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
        doc="URL-friendly tenant identifier"
    )
    
    # API Access
    api_key = Column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
        doc="API key for tenant authentication"
    )
    
    # Status and Configuration
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        doc="Whether tenant is active"
    )
    
    # Rate Limiting Configuration
    rate_limit_per_minute = Column(
        Integer,
        default=100,
        nullable=False,
        doc="Rate limit per minute for this tenant"
    )
    
    rate_limit_burst = Column(
        Integer,
        default=200,
        nullable=False,
        doc="Burst rate limit for this tenant"
    )
    
    # Subscription and Limits
    subscription_tier = Column(
        String(50),
        default="free",
        nullable=False,
        doc="Subscription tier (free, pro, enterprise)"
    )
    
    max_events_per_month = Column(
        Integer,
        default=10000,
        nullable=False,
        doc="Maximum events per month for this tenant"
    )
    
    max_alert_rules = Column(
        Integer,
        default=10,
        nullable=False,
        doc="Maximum alert rules for this tenant"
    )
    
    # Contact and Billing
    contact_email = Column(
        String(MAX_STRING_LENGTH),
        nullable=True,
        doc="Primary contact email for tenant"
    )
    
    billing_email = Column(
        String(MAX_STRING_LENGTH),
        nullable=True,
        doc="Billing contact email"
    )
    
    # Notification Configuration
    notification_settings = Column(
        JSONB,
        nullable=True,
        doc="JSON configuration for notifications (email, slack, etc.)"
    )
    
    # Metadata
    tenant_metadata = Column(
        JSONB,
        nullable=True,
        doc="Additional tenant metadata"
    )
    
    # Usage Tracking
    current_month_events = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Current month event count"
    )
    
    last_activity_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Last activity timestamp"
    )
    
    # Timezone
    timezone = Column(
        String(50),
        default="UTC",
        nullable=False,
        doc="Tenant timezone for date/time display"
    )
    
    # Relationships
    users = relationship(
        "User",
        back_populates="tenant",
        lazy="select",
        doc="Users belonging to this tenant"
    )
    
    events = relationship(
        "Event",
        back_populates="tenant",
        lazy="select",
        doc="Events belonging to this tenant"
    )
    
    alert_rules = relationship(
        "AlertRule",
        back_populates="tenant",
        lazy="select",
        doc="Alert rules belonging to this tenant"
    )
    
    alerts = relationship(
        "Alert",
        back_populates="tenant",
        lazy="select",
        doc="Alerts belonging to this tenant"
    )
    
    # Table constraints
    __table_args__ = (
        UniqueConstraint('slug', name='uq_tenant_slug'),
        UniqueConstraint('api_key', name='uq_tenant_api_key'),
    )
    
    @classmethod
    def generate_api_key(cls) -> str:
        """Generate a secure API key."""
        return secrets.token_urlsafe(32)
    
    def is_rate_limited(self, current_requests: int) -> bool:
        """Check if tenant has exceeded rate limits."""
        return current_requests >= self.rate_limit_per_minute
    
    def is_within_monthly_limit(self) -> bool:
        """Check if tenant is within monthly event limits."""
        return self.current_month_events < self.max_events_per_month
    
    def can_create_alert_rule(self, current_rules: int) -> bool:
        """Check if tenant can create more alert rules."""
        return current_rules < self.max_alert_rules
    
    def update_activity(self) -> None:
        """Update last activity timestamp."""
        self.last_activity_at = func.now()
    
    def increment_monthly_events(self, count: int = 1) -> None:
        """Increment monthly event counter."""
        self.current_month_events += count
    
    def reset_monthly_events(self) -> None:
        """Reset monthly event counter (called monthly)."""
        self.current_month_events = 0
    
    def get_notification_config(self, channel: str) -> Optional[dict]:
        """Get notification configuration for a specific channel."""
        if not self.notification_settings:
            return None
        return self.notification_settings.get(channel)
    
    def set_notification_config(self, channel: str, config: dict) -> None:
        """Set notification configuration for a specific channel."""
        if not self.notification_settings:
            self.notification_settings = {}
        self.notification_settings[channel] = config
    
    def __str__(self) -> str:
        """String representation."""
        return f"Tenant({self.name})"
    
    def __repr__(self) -> str:
        """Detailed representation."""
        return f"<Tenant(id={self.id}, name='{self.name}', slug='{self.slug}', active={self.is_active})>"
