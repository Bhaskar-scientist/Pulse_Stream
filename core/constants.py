"""Application constants for PulseStream."""

from enum import Enum


class EventType(str, Enum):
    """Event types supported by PulseStream."""
    
    API_CALL = "api_call"
    USER_ACTION = "user_action"
    SYSTEM_EVENT = "system_event"
    ERROR_EVENT = "error_event"
    CUSTOM_EVENT = "custom_event"


class EventSeverity(str, Enum):
    """Event severity levels."""
    
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertStatus(str, Enum):
    """Alert status values."""
    
    PENDING = "pending"
    ACTIVE = "active"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


class TenantRole(str, Enum):
    """Tenant user roles."""
    
    VIEWER = "viewer"
    ADMIN = "admin"
    OWNER = "owner"


class ProcessingStatus(str, Enum):
    """Event processing status."""
    
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


class NotificationChannel(str, Enum):
    """Notification channel types."""
    
    EMAIL = "email"
    SLACK = "slack"
    SMS = "sms"
    WEBHOOK = "webhook"


# Rate limiting constants
DEFAULT_RATE_LIMIT_PER_MINUTE = 100
DEFAULT_RATE_LIMIT_BURST = 200

# Token expiration
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Database constants
MAX_STRING_LENGTH = 255
MAX_TEXT_LENGTH = 10000
MAX_JSON_DEPTH = 10

# Event processing
MAX_RETRY_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 60
BATCH_SIZE = 100

# Alert processing
ALERT_COOLDOWN_MINUTES = 5
MAX_ALERTS_PER_RULE_PER_HOUR = 10

# Time windows for metrics
TIME_WINDOWS = {
    "1m": 60,
    "5m": 300,
    "15m": 900,
    "1h": 3600,
    "6h": 21600,
    "24h": 86400,
    "7d": 604800,
}

# HTTP status code ranges
HTTP_SUCCESS_RANGE = (200, 299)
HTTP_CLIENT_ERROR_RANGE = (400, 499)
HTTP_SERVER_ERROR_RANGE = (500, 599)
