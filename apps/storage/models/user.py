"""User model for authentication and authorization."""

from typing import Optional, List

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from passlib.context import CryptContext

from core.database import Base, TenantMixin
from core.constants import MAX_STRING_LENGTH, TenantRole

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class User(Base, TenantMixin):
    """User model for authentication and role-based access."""
    
    __tablename__ = "users"
    
    # Basic Information
    email = Column(
        String(MAX_STRING_LENGTH),
        nullable=False,
        index=True,
        doc="User email address (unique per tenant)"
    )
    
    username = Column(
        String(100),
        nullable=True,
        doc="Optional username"
    )
    
    full_name = Column(
        String(MAX_STRING_LENGTH),
        nullable=True,
        doc="User's full name"
    )
    
    # Authentication
    hashed_password = Column(
        String(128),
        nullable=False,
        doc="Bcrypt hashed password"
    )
    
    # Authorization
    role = Column(
        String(20),
        nullable=False,
        default=TenantRole.VIEWER,
        doc="User role within tenant (viewer, admin, owner)"
    )
    
    # Status
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        doc="Whether user account is active"
    )
    
    is_verified = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether user email is verified"
    )
    
    # Activity Tracking
    last_login_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Last login timestamp"
    )
    
    last_active_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Last activity timestamp"
    )
    
    login_count = Column(
        String(20),
        default="0",
        nullable=False,
        doc="Total login count"
    )
    
    # Password Management
    password_changed_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="When password was last changed"
    )
    
    # User Preferences
    preferences = Column(
        JSONB,
        nullable=True,
        doc="User preferences (theme, notifications, etc.)"
    )
    
    # Notification Settings
    notification_preferences = Column(
        JSONB,
        nullable=True,
        doc="User-specific notification preferences"
    )
    
    # Security
    failed_login_attempts = Column(
        String(10),
        default="0",
        nullable=False,
        doc="Number of failed login attempts"
    )
    
    locked_until = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Account locked until this timestamp"
    )
    
    # API Access
    api_access_enabled = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether user can access API directly"
    )
    
    # Relationships
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Tenant this user belongs to"
    )
    
    tenant = relationship(
        "Tenant",
        back_populates="users",
        lazy="select"
    )
    
    # Class methods for password handling
    @classmethod
    def verify_password(cls, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return pwd_context.verify(plain_password, hashed_password)
    
    @classmethod
    def get_password_hash(cls, password: str) -> str:
        """Hash a password."""
        return pwd_context.hash(password)
    
    # Instance methods
    def check_password(self, password: str) -> bool:
        """Check if provided password is correct."""
        return self.verify_password(password, self.hashed_password)
    
    def set_password(self, password: str) -> None:
        """Set a new password."""
        self.hashed_password = self.get_password_hash(password)
        self.password_changed_at = func.now()
    
    def is_admin(self) -> bool:
        """Check if user is admin or owner."""
        return self.role in [TenantRole.ADMIN, TenantRole.OWNER]
    
    def is_owner(self) -> bool:
        """Check if user is owner."""
        return self.role == TenantRole.OWNER
    
    def can_manage_users(self) -> bool:
        """Check if user can manage other users."""
        return self.role in [TenantRole.ADMIN, TenantRole.OWNER]
    
    def can_manage_alerts(self) -> bool:
        """Check if user can manage alert rules."""
        return self.role in [TenantRole.ADMIN, TenantRole.OWNER]
    
    def can_access_api(self) -> bool:
        """Check if user can access API."""
        return self.is_active and self.api_access_enabled
    
    def is_account_locked(self) -> bool:
        """Check if account is currently locked."""
        if not self.locked_until:
            return False
        return func.now() < self.locked_until
    
    def record_login(self) -> None:
        """Record a successful login."""
        self.last_login_at = func.now()
        self.last_active_at = func.now()
        self.login_count = str(int(self.login_count) + 1)
        self.failed_login_attempts = "0"
    
    def record_failed_login(self) -> None:
        """Record a failed login attempt."""
        current_attempts = int(self.failed_login_attempts)
        self.failed_login_attempts = str(current_attempts + 1)
        
        # Lock account after 5 failed attempts for 30 minutes
        if current_attempts >= 4:
            self.locked_until = func.now() + func.interval('30 minutes')
    
    def update_activity(self) -> None:
        """Update last activity timestamp."""
        self.last_active_at = func.now()
    
    def get_preference(self, key: str, default=None):
        """Get a user preference."""
        if not self.preferences:
            return default
        return self.preferences.get(key, default)
    
    def set_preference(self, key: str, value) -> None:
        """Set a user preference."""
        if not self.preferences:
            self.preferences = {}
        self.preferences[key] = value
    
    def get_notification_preference(self, channel: str, event_type: str) -> bool:
        """Get notification preference for a specific channel and event type."""
        if not self.notification_preferences:
            return True  # Default to enabled
        
        channel_prefs = self.notification_preferences.get(channel, {})
        return channel_prefs.get(event_type, True)
    
    def set_notification_preference(self, channel: str, event_type: str, enabled: bool) -> None:
        """Set notification preference."""
        if not self.notification_preferences:
            self.notification_preferences = {}
        
        if channel not in self.notification_preferences:
            self.notification_preferences[channel] = {}
        
        self.notification_preferences[channel][event_type] = enabled
    
    def __str__(self) -> str:
        """String representation."""
        return f"User({self.email})"
    
    def __repr__(self) -> str:
        """Detailed representation."""
        return f"<User(id={self.id}, email='{self.email}', role='{self.role}', tenant_id={self.tenant_id})>"
