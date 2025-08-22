"""Authentication schemas for PulseStream."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, validator

from core.constants import TenantRole


class TokenResponse(BaseModel):
    """JWT token response schema."""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Access token expiration in seconds")
    refresh_expires_in: int = Field(..., description="Refresh token expiration in seconds")
    user_id: str = Field(..., description="User ID")
    tenant_id: str = Field(..., description="Tenant ID")
    email: str = Field(..., description="User email")
    role: str = Field(..., description="User role")


class LoginRequest(BaseModel):
    """User login request schema."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password")
    tenant_slug: str = Field(..., description="Tenant slug for multi-tenant login")
    remember_me: bool = Field(default=False, description="Remember login for longer session")


class RefreshTokenRequest(BaseModel):
    """Token refresh request schema."""
    refresh_token: str = Field(..., description="Valid refresh token")


class UserRegistrationRequest(BaseModel):
    """User registration request schema."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password")
    confirm_password: str = Field(..., description="Password confirmation")
    full_name: str = Field(..., min_length=2, max_length=100, description="User's full name")
    username: Optional[str] = Field(None, min_length=3, max_length=50, description="Optional username")
    role: str = Field(default=TenantRole.VIEWER, description="User role")
    
    @validator('confirm_password')
    def passwords_match(cls, v, values, **kwargs):
        if 'password' in values and v != values['password']:
            raise ValueError('Passwords do not match')
        return v
    
    @validator('role')
    def validate_role(cls, v):
        if v not in [TenantRole.VIEWER, TenantRole.ADMIN, TenantRole.OWNER]:
            raise ValueError(f'Invalid role. Must be one of: {", ".join([TenantRole.VIEWER, TenantRole.ADMIN, TenantRole.OWNER])}')
        return v


class TenantRegistrationRequest(BaseModel):
    """Tenant registration request schema."""
    name: str = Field(..., min_length=2, max_length=255, description="Company/organization name")
    slug: str = Field(..., min_length=2, max_length=100, description="Unique tenant slug")
    contact_email: EmailStr = Field(..., description="Primary contact email")
    billing_email: Optional[EmailStr] = Field(None, description="Billing email (optional)")
    subscription_tier: str = Field(default="free", description="Subscription tier")
    timezone: str = Field(default="UTC", description="Default timezone")
    
    @validator('slug')
    def validate_slug(cls, v):
        if not v.replace('-', '').replace('_', '').isalnum():
            raise ValueError('Slug must contain only letters, numbers, hyphens, and underscores')
        return v.lower()


class PasswordChangeRequest(BaseModel):
    """Password change request schema."""
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, description="New password")
    confirm_new_password: str = Field(..., description="New password confirmation")
    
    @validator('confirm_new_password')
    def passwords_match(cls, v, values, **kwargs):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('New passwords do not match')
        return v


class PasswordResetRequest(BaseModel):
    """Password reset request schema."""
    email: EmailStr = Field(..., description="User email address")
    tenant_slug: str = Field(..., description="Tenant slug")


class PasswordResetConfirmRequest(BaseModel):
    """Password reset confirmation schema."""
    token: str = Field(..., description="Password reset token")
    new_password: str = Field(..., min_length=8, description="New password")
    confirm_new_password: str = Field(..., description="New password confirmation")
    
    @validator('confirm_new_password')
    def passwords_match(cls, v, values, **kwargs):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('New passwords do not match')
        return v


class UserProfileResponse(BaseModel):
    """User profile response schema."""
    id: str = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    username: Optional[str] = Field(None, description="Username")
    full_name: Optional[str] = Field(None, description="Full name")
    role: str = Field(..., description="User role")
    is_active: bool = Field(..., description="Account active status")
    is_verified: bool = Field(..., description="Email verification status")
    last_login_at: Optional[datetime] = Field(None, description="Last login timestamp")
    last_active_at: Optional[datetime] = Field(None, description="Last activity timestamp")
    login_count: str = Field(..., description="Total login count")
    api_access_enabled: bool = Field(..., description="API access status")
    created_at: datetime = Field(..., description="Account creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    class Config:
        from_attributes = True


class UserProfileUpdateRequest(BaseModel):
    """User profile update request schema."""
    username: Optional[str] = Field(None, min_length=3, max_length=50, description="Username")
    full_name: Optional[str] = Field(None, min_length=2, max_length=100, description="Full name")
    preferences: Optional[dict] = Field(None, description="User preferences")
    notification_preferences: Optional[dict] = Field(None, description="Notification preferences")


class TenantProfileResponse(BaseModel):
    """Tenant profile response schema."""
    id: str = Field(..., description="Tenant ID")
    name: str = Field(..., description="Company/organization name")
    slug: str = Field(..., description="Tenant slug")
    api_key: str = Field(..., description="API key (masked)")
    is_active: bool = Field(..., description="Tenant active status")
    subscription_tier: str = Field(..., description="Subscription tier")
    contact_email: Optional[str] = Field(None, description="Contact email")
    billing_email: Optional[str] = Field(None, description="Billing email")
    timezone: str = Field(..., description="Default timezone")
    rate_limit_per_minute: int = Field(..., description="Rate limit per minute")
    max_events_per_month: int = Field(..., description="Monthly event limit")
    current_month_events: int = Field(..., description="Current month event count")
    last_activity_at: Optional[datetime] = Field(None, description="Last activity timestamp")
    created_at: datetime = Field(..., description="Tenant creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    class Config:
        from_attributes = True


class TenantProfileUpdateRequest(BaseModel):
    """Tenant profile update request schema."""
    name: Optional[str] = Field(None, min_length=2, max_length=255, description="Company name")
    contact_email: Optional[EmailStr] = Field(None, description="Contact email")
    billing_email: Optional[EmailStr] = Field(None, description="Billing email")
    timezone: Optional[str] = Field(None, description="Default timezone")
    notification_settings: Optional[dict] = Field(None, description="Notification settings")


class UserListResponse(BaseModel):
    """User list response schema."""
    users: List[UserProfileResponse] = Field(..., description="List of users")
    total: int = Field(..., description="Total number of users")
    page: int = Field(..., description="Current page number")
    size: int = Field(..., description="Page size")
    pages: int = Field(..., description="Total number of pages")


class AuthenticationAuditLog(BaseModel):
    """Authentication audit log entry."""
    user_id: str = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    action: str = Field(..., description="Authentication action")
    ip_address: Optional[str] = Field(None, description="IP address")
    user_agent: Optional[str] = Field(None, description="User agent string")
    success: bool = Field(..., description="Action success status")
    details: Optional[dict] = Field(None, description="Additional details")
    timestamp: datetime = Field(..., description="Action timestamp")
    
    class Config:
        from_attributes = True


class LoginAttemptResponse(BaseModel):
    """Login attempt response for failed logins."""
    message: str = Field(..., description="Response message")
    remaining_attempts: int = Field(..., description="Remaining login attempts")
    locked_until: Optional[datetime] = Field(None, description="Account lockout end time")
    requires_captcha: bool = Field(default=False, description="Whether CAPTCHA is required")


class TwoFactorAuthRequest(BaseModel):
    """Two-factor authentication request."""
    code: str = Field(..., min_length=6, max_length=6, description="2FA code")
    remember_device: bool = Field(default=False, description="Remember this device")


class TwoFactorAuthSetupRequest(BaseModel):
    """Two-factor authentication setup request."""
    method: str = Field(..., description="2FA method (totp, sms, email)")
    phone_number: Optional[str] = Field(None, description="Phone number for SMS")
    backup_email: Optional[EmailStr] = Field(None, description="Backup email")


class TwoFactorAuthSetupResponse(BaseModel):
    """Two-factor authentication setup response."""
    secret_key: str = Field(..., description="TOTP secret key")
    qr_code_url: str = Field(..., description="QR code URL for TOTP apps")
    backup_codes: List[str] = Field(..., description="Backup codes for account recovery")
    setup_complete: bool = Field(..., description="Whether setup is complete")
