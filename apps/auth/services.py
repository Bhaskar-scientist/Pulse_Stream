"""Authentication services for PulseStream."""

import uuid
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple

from fastapi import HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from core.auth import auth_manager, tenant_auth_manager
from core.logging import get_logger
from core.config import settings
from apps.storage.models.user import User
from apps.storage.models.tenant import Tenant
from apps.storage.crud import user_crud, tenant_crud
from apps.auth.schemas import (
    LoginRequest, UserRegistrationRequest, TenantRegistrationRequest,
    PasswordChangeRequest, PasswordResetRequest, PasswordResetConfirmRequest,
    UserProfileUpdateRequest, TenantProfileUpdateRequest
)

logger = get_logger(__name__)


class AuthenticationService:
    """Service for user authentication operations."""
    
    def __init__(self):
        self.auth_manager = auth_manager
    
    async def authenticate_user(
        self, 
        session: AsyncSession, 
        login_data: LoginRequest,
        request: Request
    ) -> Tuple[User, str, str]:
        """Authenticate user and return user object with tokens."""
        try:
            # Get tenant by slug
            tenant = await tenant_crud.get_by_slug(session, slug=login_data.tenant_slug)
            if not tenant or not tenant.is_active:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid tenant or tenant inactive"
                )
            
            # Authenticate user
            user = await self.auth_manager.authenticate_user(
                session, 
                tenant_id=tenant.id, 
                email=login_data.email, 
                password=login_data.password
            )
            
            if not user:
                # Log failed login attempt
                await self._log_failed_login(session, login_data.email, tenant.id, request)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid email or password"
                )
            
            # Check if account is locked
            if user.is_account_locked():
                raise HTTPException(
                    status_code=status.HTTP_423_LOCKED,
                    detail="Account is temporarily locked due to multiple failed login attempts"
                )
            
            # Generate tokens
            access_token = await self._create_user_access_token(user, tenant)
            refresh_token = await self._create_user_refresh_token(user, tenant)
            
            # Log successful login
            await self._log_successful_login(session, user, request)
            
            return user, access_token, refresh_token
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication failed"
            )
    
    async def _create_user_access_token(self, user: User, tenant: Tenant) -> str:
        """Create access token for user."""
        token_data = {
            "sub": str(user.id),
            "email": user.email,
            "tenant_id": str(tenant.id),
            "role": user.role,
            "type": "access"
        }
        
        # Adjust expiration for remember me
        expires_delta = None
        if hasattr(user, 'remember_me') and user.remember_me:
            expires_delta = timedelta(days=7)  # 7 days for remember me
        
        return self.auth_manager.create_access_token(token_data, expires_delta)
    
    async def _create_user_refresh_token(self, user: User, tenant: Tenant) -> str:
        """Create refresh token for user."""
        token_data = {
            "sub": str(user.id),
            "email": user.email,
            "tenant_id": str(tenant.id),
            "type": "refresh"
        }
        
        return self.auth_manager.create_refresh_token(token_data)
    
    async def refresh_access_token(
        self, 
        session: AsyncSession, 
        refresh_token: str
    ) -> Tuple[str, str]:
        """Refresh access token using refresh token."""
        try:
            # Verify refresh token
            payload = self.auth_manager.verify_token(refresh_token)
            
            # Check token type
            if payload.get("type") != "refresh":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type"
                )
            
            # Get user and tenant
            user_id = payload.get("sub")
            tenant_id = payload.get("tenant_id")
            
            if not user_id or not tenant_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token payload"
                )
            
            user = await user_crud.get(session, id=uuid.UUID(user_id), tenant_id=uuid.UUID(tenant_id))
            tenant = await tenant_crud.get(session, id=uuid.UUID(tenant_id))
            
            if not user or not tenant or not user.is_active or not tenant.is_active:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User or tenant not found or inactive"
                )
            
            # Generate new tokens
            new_access_token = await self._create_user_access_token(user, tenant)
            new_refresh_token = await self._create_user_refresh_token(user, tenant)
            
            return new_access_token, new_refresh_token
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Token refresh error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Token refresh failed"
            )
    
    async def _log_failed_login(
        self, 
        session: AsyncSession, 
        email: str, 
        tenant_id: uuid.UUID, 
        request: Request
    ):
        """Log failed login attempt."""
        try:
            # Get user if exists
            user = await user_crud.get_by_email(session, tenant_id=tenant_id, email=email)
            
            if user:
                # Update failed login count
                user.record_failed_login()
                await session.commit()
                
                logger.warning(
                    f"Failed login attempt for user {email} in tenant {tenant_id}. "
                    f"IP: {request.client.host}, User-Agent: {request.headers.get('user-agent')}"
                )
            else:
                logger.warning(
                    f"Failed login attempt for non-existent user {email} in tenant {tenant_id}. "
                    f"IP: {request.client.host}"
                )
                
        except Exception as e:
            logger.error(f"Error logging failed login: {e}")
    
    async def _log_successful_login(
        self, 
        session: AsyncSession, 
        user: User, 
        request: Request
    ):
        """Log successful login."""
        try:
            logger.info(
                f"Successful login for user {user.email} in tenant {user.tenant_id}. "
                f"IP: {request.client.host}, User-Agent: {request.headers.get('user-agent')}"
            )
        except Exception as e:
            logger.error(f"Error logging successful login: {e}")


class UserManagementService:
    """Service for user management operations."""
    
    def __init__(self):
        self.auth_manager = auth_manager
    
    async def register_user(
        self, 
        session: AsyncSession, 
        user_data: UserRegistrationRequest,
        tenant_id: uuid.UUID,
        created_by: Optional[User] = None
    ) -> User:
        """Register a new user."""
        try:
            # Check if user already exists in tenant
            existing_user = await user_crud.get_by_email(session, tenant_id=tenant_id, email=user_data.email)
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User with this email already exists in this tenant"
                )
            
            # Check username uniqueness if provided
            if user_data.username:
                existing_username = await user_crud.get_by_username(session, tenant_id=tenant_id, username=user_data.username)
                if existing_username:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Username already taken in this tenant"
                    )
            
            # Hash password
            hashed_password = self.auth_manager.get_password_hash(user_data.password)
            
            # Create user
            user = await user_crud.create_user(
                session,
                tenant_id=tenant_id,
                email=user_data.email,
                password=hashed_password,
                full_name=user_data.full_name,
                username=user_data.username,
                role=user_data.role
            )
            
            logger.info(f"User {user_data.email} registered in tenant {tenant_id}")
            return user
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"User registration error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="User registration failed"
            )
    
    async def update_user_profile(
        self, 
        session: AsyncSession, 
        user: User, 
        profile_data: UserProfileUpdateRequest
    ) -> User:
        """Update user profile."""
        try:
            # Update user fields
            if profile_data.username is not None:
                # Check username uniqueness
                if profile_data.username != user.username:
                    existing_username = await user_crud.get_by_username(
                        session, tenant_id=user.tenant_id, username=profile_data.username
                    )
                    if existing_username:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Username already taken"
                        )
                user.username = profile_data.username
            
            if profile_data.full_name is not None:
                user.full_name = profile_data.full_name
            
            if profile_data.preferences is not None:
                user.preferences = profile_data.preferences
            
            if profile_data.notification_preferences is not None:
                user.notification_preferences = profile_data.notification_preferences
            
            # Update timestamp
            user.updated_at = datetime.utcnow()
            
            await session.commit()
            
            logger.info(f"Profile updated for user {user.email}")
            return user
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Profile update error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Profile update failed"
            )
    
    async def change_password(
        self, 
        session: AsyncSession, 
        user: User, 
        password_data: PasswordChangeRequest
    ) -> bool:
        """Change user password."""
        try:
            # Verify current password
            if not self.auth_manager.verify_password(password_data.current_password, user.hashed_password):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Current password is incorrect"
                )
            
            # Hash new password
            new_hashed_password = self.auth_manager.get_password_hash(password_data.new_password)
            
            # Update password
            user.hashed_password = new_hashed_password
            user.password_changed_at = datetime.utcnow()
            user.updated_at = datetime.utcnow()
            
            await session.commit()
            
            logger.info(f"Password changed for user {user.email}")
            return True
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Password change error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Password change failed"
            )
    
    async def get_users_by_tenant(
        self, 
        session: AsyncSession, 
        tenant_id: uuid.UUID,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None
    ) -> Tuple[List[User], int]:
        """Get users for a tenant with pagination and search."""
        try:
            users, total = await user_crud.get_multi_by_tenant(
                session, 
                tenant_id=tenant_id,
                skip=skip,
                limit=limit,
                search=search
            )
            
            return users, total
            
        except Exception as e:
            logger.error(f"Error getting users for tenant {tenant_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve users"
            )


class TenantManagementService:
    """Service for tenant management operations."""
    
    async def register_tenant(
        self, 
        session: AsyncSession, 
        tenant_data: TenantRegistrationRequest
    ) -> Tuple[Tenant, User]:
        """Register a new tenant with owner user."""
        try:
            # Check if tenant slug already exists
            existing_tenant = await tenant_crud.get_by_slug(session, slug=tenant_data.slug)
            if existing_tenant:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Tenant slug already taken"
                )
            
            # Check if contact email already exists
            existing_email = await tenant_crud.get_by_contact_email(session, email=tenant_data.contact_email)
            if existing_email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Contact email already registered"
                )
            
            # Generate API key
            api_key = secrets.token_urlsafe(32)
            
            # Create tenant
            tenant = await tenant_crud.create_tenant(
                session,
                name=tenant_data.name,
                slug=tenant_data.slug,
                api_key=api_key,
                contact_email=tenant_data.contact_email,
                billing_email=tenant_data.billing_email,
                subscription_tier=tenant_data.subscription_tier,
                timezone=tenant_data.timezone
            )
            
            # Create owner user
            user_service = UserManagementService()
            owner_user = await user_service.register_user(
                session,
                user_data=UserRegistrationRequest(
                    email=tenant_data.contact_email,
                    password=secrets.token_urlsafe(12),  # Temporary password
                    confirm_password=secrets.token_urlsafe(12),
                    full_name="Tenant Owner",
                    role="owner"
                ),
                tenant_id=tenant.id
            )
            
            logger.info(f"Tenant {tenant_data.name} registered with slug {tenant_data.slug}")
            return tenant, owner_user
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Tenant registration error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Tenant registration failed"
            )
    
    async def update_tenant_profile(
        self, 
        session: AsyncSession, 
        tenant: Tenant, 
        profile_data: TenantProfileUpdateRequest
    ) -> Tenant:
        """Update tenant profile."""
        try:
            # Update tenant fields
            if profile_data.name is not None:
                tenant.name = profile_data.name
            
            if profile_data.contact_email is not None:
                # Check email uniqueness
                if profile_data.contact_email != tenant.contact_email:
                    existing_tenant = await tenant_crud.get_by_contact_email(
                        session, email=profile_data.contact_email
                    )
                    if existing_tenant and existing_tenant.id != tenant.id:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Contact email already registered"
                        )
                tenant.contact_email = profile_data.contact_email
            
            if profile_data.billing_email is not None:
                tenant.billing_email = profile_data.billing_email
            
            if profile_data.timezone is not None:
                tenant.timezone = profile_data.timezone
            
            if profile_data.notification_settings is not None:
                tenant.notification_settings = profile_data.notification_settings
            
            # Update timestamp
            tenant.updated_at = datetime.utcnow()
            
            await session.commit()
            
            logger.info(f"Profile updated for tenant {tenant.name}")
            return tenant
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Tenant profile update error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Tenant profile update failed"
            )
    
    async def regenerate_api_key(
        self, 
        session: AsyncSession, 
        tenant: Tenant
    ) -> str:
        """Regenerate tenant API key."""
        try:
            # Generate new API key
            new_api_key = secrets.token_urlsafe(32)
            
            # Update tenant
            tenant.api_key = new_api_key
            tenant.updated_at = datetime.utcnow()
            
            await session.commit()
            
            logger.info(f"API key regenerated for tenant {tenant.name}")
            return new_api_key
            
        except Exception as e:
            logger.error(f"API key regeneration error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="API key regeneration failed"
            )


# Global service instances
auth_service = AuthenticationService()
user_service = UserManagementService()
tenant_service = TenantManagementService()
