"""Authentication API endpoints for PulseStream."""

import secrets
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import (
    get_current_user, get_current_active_user, get_current_tenant,
    require_permissions, require_roles
)
from core.database import get_async_session
from core.logging import get_logger
from apps.auth.schemas import (
    LoginRequest, TokenResponse, RefreshTokenRequest, UserRegistrationRequest,
    TenantRegistrationRequest, PasswordChangeRequest, PasswordResetRequest,
    PasswordResetConfirmRequest, UserProfileResponse, UserProfileUpdateRequest,
    TenantProfileResponse, TenantProfileUpdateRequest, UserListResponse
)
from apps.auth.services import auth_service, user_service, tenant_service
from apps.storage.models.user import User
from apps.storage.models.tenant import Tenant

logger = get_logger(__name__)

# Create router
router = APIRouter(prefix="/auth", tags=["Authentication"])

# Security
security = HTTPBearer()


@router.post("/login", response_model=TokenResponse)
async def login(
    login_data: LoginRequest,
    request: Request,
    session: AsyncSession = Depends(get_async_session)
):
    """User login endpoint."""
    try:
        # Authenticate user
        user, access_token, refresh_token = await auth_service.authenticate_user(
            session, login_data, request
        )
        
        # Calculate expiration times
        expires_in = settings.access_token_expire_minutes * 60  # Convert to seconds
        refresh_expires_in = settings.refresh_token_expire_days * 24 * 60 * 60  # Convert to seconds
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=expires_in,
            refresh_expires_in=refresh_expires_in,
            user_id=str(user.id),
            tenant_id=str(user.tenant_id),
            email=user.email,
            role=user.role
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    session: AsyncSession = Depends(get_async_session)
):
    """Refresh access token endpoint."""
    try:
        # Refresh tokens
        new_access_token, new_refresh_token = await auth_service.refresh_access_token(
            session, refresh_data.refresh_token
        )
        
        # Decode tokens to get user info
        from core.auth import auth_manager
        access_payload = auth_manager.verify_token(new_access_token)
        refresh_payload = auth_manager.verify_token(new_refresh_token)
        
        # Calculate expiration times
        expires_in = settings.access_token_expire_minutes * 60
        refresh_expires_in = settings.refresh_token_expire_days * 24 * 60 * 60
        
        return TokenResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            expires_in=expires_in,
            refresh_expires_in=refresh_expires_in,
            user_id=access_payload.get("sub"),
            tenant_id=access_payload.get("tenant_id"),
            email=access_payload.get("email"),
            role=access_payload.get("role")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )


@router.post("/register/tenant", response_model=dict)
async def register_tenant(
    tenant_data: TenantRegistrationRequest,
    session: AsyncSession = Depends(get_async_session)
):
    """Register a new tenant with owner user."""
    try:
        # Register tenant and create owner user
        tenant, owner_user = await tenant_service.register_tenant(session, tenant_data)
        
        # Generate temporary password for owner
        temp_password = secrets.token_urlsafe(12)
        owner_user.set_password(temp_password)
        await session.commit()
        
        return {
            "message": "Tenant registered successfully",
            "tenant": {
                "id": str(tenant.id),
                "name": tenant.name,
                "slug": tenant.slug,
                "api_key": tenant.api_key
            },
            "owner_user": {
                "id": str(owner_user.id),
                "email": owner_user.email,
                "temporary_password": temp_password
            },
            "next_steps": [
                "Login with the temporary password",
                "Change password on first login",
                "Configure tenant settings"
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Tenant registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Tenant registration failed"
        )


@router.post("/register/user", response_model=UserProfileResponse)
async def register_user(
    user_data: UserRegistrationRequest,
    current_user: User = Depends(require_roles("admin", "owner")),
    session: AsyncSession = Depends(get_async_session)
):
    """Register a new user in the current tenant."""
    try:
        # Register user
        user = await user_service.register_user(
            session, user_data, current_user.tenant_id, current_user
        )
        
        return UserProfileResponse.from_orm(user)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"User registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User registration failed"
        )


@router.get("/profile", response_model=UserProfileResponse)
async def get_user_profile(
    current_user: User = Depends(get_current_active_user)
):
    """Get current user profile."""
    return UserProfileResponse.from_orm(current_user)


@router.put("/profile", response_model=UserProfileResponse)
async def update_user_profile(
    profile_data: UserProfileUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Update current user profile."""
    try:
        updated_user = await user_service.update_user_profile(
            session, current_user, profile_data
        )
        
        return UserProfileResponse.from_orm(updated_user)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Profile update error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Profile update failed"
        )


@router.post("/change-password")
async def change_password(
    password_data: PasswordChangeRequest,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Change user password."""
    try:
        success = await user_service.change_password(
            session, current_user, password_data
        )
        
        if success:
            return {"message": "Password changed successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password change failed"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password change error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password change failed"
        )


@router.get("/users", response_model=UserListResponse)
async def get_users(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    search: Optional[str] = Query(None, description="Search term for email or name"),
    current_user: User = Depends(require_roles("admin", "owner")),
    session: AsyncSession = Depends(get_async_session)
):
    """Get users in the current tenant."""
    try:
        users, total = await user_service.get_users_by_tenant(
            session, current_user.tenant_id, skip, limit, search
        )
        
        # Calculate pagination
        pages = (total + limit - 1) // limit
        
        return UserListResponse(
            users=[UserProfileResponse.from_orm(user) for user in users],
            total=total,
            page=(skip // limit) + 1,
            size=limit,
            pages=pages
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve users"
        )


@router.get("/tenant/profile", response_model=TenantProfileResponse)
async def get_tenant_profile(
    current_tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_async_session)
):
    """Get current tenant profile."""
    return TenantProfileResponse.from_orm(current_tenant)


@router.put("/tenant/profile", response_model=TenantProfileResponse)
async def update_tenant_profile(
    profile_data: TenantProfileUpdateRequest,
    current_tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_async_session)
):
    """Update current tenant profile."""
    try:
        updated_tenant = await tenant_service.update_tenant_profile(
            session, current_tenant, profile_data
        )
        
        return TenantProfileResponse.from_orm(updated_tenant)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Tenant profile update error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Tenant profile update failed"
        )


@router.post("/tenant/regenerate-api-key")
async def regenerate_api_key(
    current_tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_async_session)
):
    """Regenerate tenant API key."""
    try:
        new_api_key = await tenant_service.regenerate_api_key(session, current_tenant)
        
        return {
            "message": "API key regenerated successfully",
            "new_api_key": new_api_key,
            "warning": "Previous API key is now invalid. Update all integrations immediately."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API key regeneration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API key regeneration failed"
        )


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """User logout endpoint."""
    try:
        # Update last activity
        current_user.update_activity()
        await session.commit()
        
        logger.info(f"User {current_user.email} logged out")
        
        return {"message": "Logged out successfully"}
        
    except Exception as e:
        logger.error(f"Logout error: {e}")
        # Don't fail logout on error
        return {"message": "Logged out successfully"}


@router.post("/password-reset/request")
async def request_password_reset(
    reset_data: PasswordResetRequest,
    session: AsyncSession = Depends(get_async_session)
):
    """Request password reset."""
    try:
        # Get tenant by slug
        tenant = await tenant_crud.get_by_slug(session, slug=reset_data.tenant_slug)
        if not tenant:
            # Don't reveal if tenant exists
            return {"message": "If the email exists, a reset link has been sent"}
        
        # Get user by email
        user = await user_crud.get_by_email(session, tenant_id=tenant.id, email=reset_data.email)
        if not user:
            # Don't reveal if user exists
            return {"message": "If the email exists, a reset link has been sent"}
        
        # Generate reset token (implement email sending logic here)
        reset_token = secrets.token_urlsafe(32)
        
        # Store reset token (implement token storage logic here)
        # For now, just log it
        logger.info(f"Password reset requested for {reset_data.email}. Token: {reset_token}")
        
        return {"message": "If the email exists, a reset link has been sent"}
        
    except Exception as e:
        logger.error(f"Password reset request error: {e}")
        # Don't reveal errors to user
        return {"message": "If the email exists, a reset link has been sent"}


@router.post("/password-reset/confirm")
async def confirm_password_reset(
    reset_data: PasswordResetConfirmRequest,
    session: AsyncSession = Depends(get_async_session)
):
    """Confirm password reset."""
    try:
        # Validate reset token (implement token validation logic here)
        # For now, just return success
        logger.info(f"Password reset confirmed with token: {reset_data.token}")
        
        return {"message": "Password reset successful"}
        
    except Exception as e:
        logger.error(f"Password reset confirmation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password reset failed"
        )


@router.get("/health")
async def auth_health_check():
    """Health check endpoint for authentication service."""
    return {
        "status": "healthy",
        "service": "authentication",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }
