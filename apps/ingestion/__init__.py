"""Event ingestion module for PulseStream."""

from .schemas import (
    EventSource,
    EventContext,
    APIMetrics,
    ErrorDetails,
    EventIngestionRequest,
    BatchEventIngestionRequest,
    EventIngestionResponse,
    BatchEventIngestionResponse,
    EventValidationError,
    EventIngestionStats,
    EventFilter,
    EventSearchResponse,
    EventHealthCheck,
    RateLimitInfo,
    EventIngestionConfig
)

from .services import (
    EventValidationService,
    RateLimitService,
    EventIngestionService,
    get_event_ingestion_service
)

from .api import router as ingestion_router

__all__ = [
    # Schemas
    "EventSource",
    "EventContext",
    "APIMetrics",
    "ErrorDetails",
    "EventIngestionRequest",
    "BatchEventIngestionRequest",
    "EventIngestionResponse",
    "BatchEventIngestionResponse",
    "EventValidationError",
    "EventIngestionStats",
    "EventFilter",
    "EventSearchResponse",
    "EventHealthCheck",
    "RateLimitInfo",
    "EventIngestionConfig",
    
    # Services
    "EventValidationService",
    "RateLimitService",
    "EventIngestionService",
    "get_event_ingestion_service",
    
    # API
    "ingestion_router"
]
