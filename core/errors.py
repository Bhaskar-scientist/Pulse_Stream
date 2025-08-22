"""Custom exception classes for PulseStream."""

from typing import Any, Dict, Optional


class PulseStreamError(Exception):
    """Base exception for all PulseStream errors."""
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class AuthenticationError(PulseStreamError):
    """Raised when authentication fails."""
    
    def __init__(self, message: str = "Authentication failed", **kwargs):
        super().__init__(message, error_code="AUTH_FAILED", **kwargs)


class AuthorizationError(PulseStreamError):
    """Raised when authorization fails."""
    
    def __init__(self, message: str = "Authorization failed", **kwargs):
        super().__init__(message, error_code="AUTHZ_FAILED", **kwargs)


class TenantNotFoundError(PulseStreamError):
    """Raised when tenant is not found."""
    
    def __init__(self, tenant_id: str, **kwargs):
        message = f"Tenant not found: {tenant_id}"
        super().__init__(message, error_code="TENANT_NOT_FOUND", **kwargs)


class ValidationError(PulseStreamError):
    """Raised when data validation fails."""
    
    def __init__(self, message: str = "Validation failed", **kwargs):
        super().__init__(message, error_code="VALIDATION_ERROR", **kwargs)


class RateLimitExceededError(PulseStreamError):
    """Raised when rate limit is exceeded."""
    
    def __init__(self, message: str = "Rate limit exceeded", **kwargs):
        super().__init__(message, error_code="RATE_LIMIT_EXCEEDED", **kwargs)


class EventProcessingError(PulseStreamError):
    """Raised when event processing fails."""
    
    def __init__(self, message: str = "Event processing failed", **kwargs):
        super().__init__(message, error_code="PROCESSING_ERROR", **kwargs)


class AlertingError(PulseStreamError):
    """Raised when alerting fails."""
    
    def __init__(self, message: str = "Alerting failed", **kwargs):
        super().__init__(message, error_code="ALERTING_ERROR", **kwargs)


class DatabaseError(PulseStreamError):
    """Raised when database operations fail."""
    
    def __init__(self, message: str = "Database operation failed", **kwargs):
        super().__init__(message, error_code="DATABASE_ERROR", **kwargs)


class RedisError(PulseStreamError):
    """Raised when Redis operations fail."""
    
    def __init__(self, message: str = "Redis operation failed", **kwargs):
        super().__init__(message, error_code="REDIS_ERROR", **kwargs)


class ConfigurationError(PulseStreamError):
    """Raised when configuration is invalid."""
    
    def __init__(self, message: str = "Configuration error", **kwargs):
        super().__init__(message, error_code="CONFIG_ERROR", **kwargs)
