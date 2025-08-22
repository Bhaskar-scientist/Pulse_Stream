"""Core authentication and authorization for PulseStream."""

import uuid
from datetime import datetime, timedelta
from typing import Optional, Union, Dict, Any

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.database import get_async_session
from core.logging import get_logger
from apps.storage.models.user import User
from apps.storage.models.tenant import Tenant
from apps.storage.crud import user_crud, tenant_crud

logger = get_logger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT token security
security = HTTPBearer()


class AuthManager:
    """Manages authentication and authorization operations."""
    
    def __init__(self):
        self.secret_key = settings.secret_key
        self.algorithm = settings.algorithm
        self.access_token_expire_minutes = settings.access_token_expire_minutes
        self.refresh_token_expire_days = settings.refresh_token_expire_days
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return pwd_context.verify(plain_password, hashed_password)
    
    def get_password_hash(self, password: str) -> str:
        """Hash a password."""
        return pwd_context.hash(password)
    
    def create_access_token(
        self, 
        data: Dict[str, Any], 
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create a JWT access token."""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        
        to_encode.update({"exp": expire, "type": "access"})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def create_refresh_token(
        self, 
        data: Dict[str, Any], 
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create a JWT refresh token."""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)
        
        to_encode.update({"exp": expire, "type": "refresh"})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify and decode a JWT token."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except JWTError as e:
            logger.warning(f"JWT verification failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    async def authenticate_user(
        self, 
        session: AsyncSession, 
        tenant_id: uuid.UUID, 
        email: str, 
        password: str
    ) -> Optional[User]:
        """Authenticate a user with email and password."""
        try:
            # Get user by email within tenant
            user = await user_crud.get_by_email(session, tenant_id=tenant_id, email=email)
            
            if not user:
                return None
            
            # Check if user is active
            if not user.is_active:
                logger.warning(f"Login attempt for inactive user: {email}")
                return None
            
            # Check if account is locked
            if user.is_account_locked():
                logger.warning(f"Login attempt for locked account: {email}")
                return None
            
            # Verify password
            if not self.verify_password(password, user.hashed_password):
                # Record failed login attempt
                user.record_failed_login()
                await session.commit()
                return None
            
            # Record successful login
            user.record_login()
            await session.commit()
            
            return user
            
        except Exception as e:
            logger.error(f"Authentication error for user {email}: {e}")
            return None
    
    async def get_current_user(
        self,
        credentials: HTTPAuthorizationCredentials = Depends(security),
        session: AsyncSession = Depends(get_async_session)
    ) -> User:
        """Get the current authenticated user from JWT token."""
        try:
            # Verify token
            payload = self.verify_token(credentials.credentials)
            
            # Extract user information
            user_id = payload.get("sub")
            tenant_id = payload.get("tenant_id")
            token_type = payload.get("type")
            
            if not user_id or not tenant_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token payload"
                )
            
            if token_type != "access":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type"
                )
            
            # Get user from database
            user = await user_crud.get(session, id=uuid.UUID(user_id), tenant_id=uuid.UUID(tenant_id))
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found"
                )
            
            if not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Inactive user account"
                )
            
            # Update last activity
            user.update_activity()
            await session.commit()
            
            return user
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting current user: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication failed"
            )
    
    async def get_current_active_user(
        self,
        current_user: User = Depends(get_current_user)
    ) -> User:
        """Get the current active user."""
        if not current_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user"
            )
        return current_user


class TenantAuthManager:
    """Manages tenant-level authentication and API key validation."""
    
    def __init__(self):
        self.secret_key = settings.secret_key
        self.algorithm = settings.algorithm
    
    async def authenticate_tenant(
        self, 
        session: AsyncSession, 
        api_key: str
    ) -> Optional[Tenant]:
        """Authenticate a tenant using API key."""
        try:
            tenant = await tenant_crud.get_by_api_key(session, api_key=api_key)
            
            if not tenant or not tenant.is_active:
                return None
            
            # Update last activity
            tenant.last_activity_at = datetime.utcnow()
            await session.commit()
            
            return tenant
            
        except Exception as e:
            logger.error(f"Tenant authentication error: {e}")
            return None
    
    async def get_current_tenant(
        self,
        request: Request,
        session: AsyncSession = Depends(get_async_session)
    ) -> Tenant:
        """Get the current tenant from API key in headers."""
        try:
            # Extract API key from headers
            api_key = request.headers.get("X-API-Key")
            
            if not api_key:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="API key required",
                    headers={"WWW-Authenticate": "APIKey"},
                )
            
            # Authenticate tenant
            tenant = await self.authenticate_tenant(session, api_key)
            
            if not tenant:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid API key",
                    headers={"WWW-Authenticate": "APIKey"},
                )
            
            return tenant
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting current tenant: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Tenant authentication failed"
            )


# Global instances
auth_manager = AuthManager()
tenant_auth_manager = TenantAuthManager()


# Dependency functions for FastAPI
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_async_session)
) -> User:
    """Get current authenticated user."""
    return await auth_manager.get_current_user(credentials, session)


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current active user."""
    return await auth_manager.get_current_active_user(current_user)


async def get_current_tenant(
    request: Request,
    session: AsyncSession = Depends(get_async_session)
) -> Tenant:
    """Get current authenticated tenant."""
    return await tenant_auth_manager.get_current_tenant(request, session)


def require_permissions(*required_permissions: str):
    """Decorator to require specific permissions."""
    def permission_checker(current_user: User = Depends(get_current_active_user)):
        # Check if user has required permissions
        for permission in required_permissions:
            if not hasattr(current_user, f"can_{permission}"):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission check failed: {permission}"
                )
            
            if not getattr(current_user, f"can_{permission}")():
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions: {permission}"
                )
        
        return current_user
    
    return permission_checker


def require_roles(*required_roles: str):
    """Decorator to require specific user roles."""
    def role_checker(current_user: User = Depends(get_current_active_user)):
        if current_user.role not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required roles: {required_roles}, user role: {current_user.role}"
            )
        return current_user
    
    return role_checker
