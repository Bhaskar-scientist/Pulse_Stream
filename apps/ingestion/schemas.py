"""Event ingestion schemas for PulseStream."""

from datetime import datetime
from typing import Optional, Dict, Any, List, Union
from enum import Enum
from pydantic import BaseModel, Field, validator, HttpUrl

from core.constants import EventType, EventSeverity


class EventSource(BaseModel):
    """Source information for an event."""
    service: str = Field(..., min_length=1, max_length=100, description="Service name")
    endpoint: str = Field(..., min_length=1, max_length=500, description="API endpoint")
    method: str = Field(..., min_length=1, max_length=10, description="HTTP method")
    version: Optional[str] = Field(None, max_length=20, description="API version")
    environment: Optional[str] = Field(None, max_length=50, description="Environment (dev, staging, prod)")


class EventContext(BaseModel):
    """Contextual information for an event."""
    user_id: Optional[str] = Field(None, description="User ID if applicable")
    session_id: Optional[str] = Field(None, description="Session ID if applicable")
    request_id: Optional[str] = Field(None, description="Request correlation ID")
    ip_address: Optional[str] = Field(None, description="Client IP address")
    user_agent: Optional[str] = Field(None, max_length=500, description="User agent string")
    referrer: Optional[HttpUrl] = Field(None, description="Referrer URL")
    tags: Optional[Dict[str, str]] = Field(None, description="Custom tags for categorization")


class APIMetrics(BaseModel):
    """API performance metrics."""
    response_time_ms: float = Field(..., ge=0, description="Response time in milliseconds")
    status_code: int = Field(..., ge=100, le=599, description="HTTP status code")
    request_size_bytes: Optional[int] = Field(None, ge=0, description="Request size in bytes")
    response_size_bytes: Optional[int] = Field(None, ge=0, description="Response size in bytes")
    cache_hit: Optional[bool] = Field(None, description="Whether response was served from cache")


class ErrorDetails(BaseModel):
    """Error information for failed events."""
    error_code: Optional[str] = Field(None, max_length=100, description="Error code")
    error_message: Optional[str] = Field(None, max_length=1000, description="Error message")
    stack_trace: Optional[str] = Field(None, description="Stack trace if available")
    error_type: Optional[str] = Field(None, max_length=100, description="Error type/class")


class EventIngestionRequest(BaseModel):
    """Main event ingestion request schema."""
    # Event identification
    event_type: EventType = Field(..., description="Type of event")
    event_id: Optional[str] = Field(None, max_length=100, description="Unique event ID")
    
    # Event content
    title: str = Field(..., min_length=1, max_length=200, description="Event title")
    message: Optional[str] = Field(None, max_length=2000, description="Event description")
    severity: EventSeverity = Field(default=EventSeverity.INFO, description="Event severity level")
    
    # Source and context
    source: EventSource = Field(..., description="Event source information")
    context: Optional[EventContext] = Field(None, description="Event context")
    
    # Performance metrics (for API events)
    metrics: Optional[APIMetrics] = Field(None, description="Performance metrics")
    error_details: Optional[ErrorDetails] = Field(None, description="Error information")
    
    # Custom data
    payload: Optional[Dict[str, Any]] = Field(None, description="Event payload data")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    
    # Timestamps
    timestamp: Optional[datetime] = Field(None, description="Event timestamp (defaults to now)")
    received_at: Optional[datetime] = Field(None, description="When event was received")
    
    @validator('timestamp', 'received_at', pre=True, always=True)
    def set_timestamps(cls, v):
        """Set default timestamps if not provided."""
        if v is None:
            return datetime.utcnow()
        return v
    
    @validator('event_id', pre=True, always=True)
    def generate_event_id(cls, v):
        """Generate event ID if not provided."""
        if v is None:
            import uuid
            return str(uuid.uuid4())
        return v


class BatchEventIngestionRequest(BaseModel):
    """Batch event ingestion request schema."""
    events: List[EventIngestionRequest] = Field(..., min_items=1, max_items=1000, description="List of events")
    batch_id: Optional[str] = Field(None, max_length=100, description="Batch identifier")
    source_application: Optional[str] = Field(None, max_length=100, description="Source application name")
    
    @validator('batch_id', pre=True, always=True)
    def generate_batch_id(cls, v):
        """Generate batch ID if not provided."""
        if v is None:
            import uuid
            return str(uuid.uuid4())
        return v


class EventIngestionResponse(BaseModel):
    """Response for event ingestion."""
    success: bool = Field(..., description="Whether ingestion was successful")
    event_id: str = Field(..., description="Event ID")
    ingested_at: datetime = Field(..., description="When event was ingested")
    processing_status: str = Field(default="queued", description="Processing status")
    message: Optional[str] = Field(None, description="Response message")
    errors: Optional[List[str]] = Field(None, description="Any validation errors")


class BatchEventIngestionResponse(BaseModel):
    """Response for batch event ingestion."""
    batch_id: str = Field(..., description="Batch identifier")
    total_events: int = Field(..., description="Total events in batch")
    successful_events: int = Field(..., description="Successfully ingested events")
    failed_events: int = Field(..., description="Failed events")
    ingested_at: datetime = Field(..., description="When batch was ingested")
    results: List[EventIngestionResponse] = Field(..., description="Individual event results")
    processing_status: str = Field(default="queued", description="Overall processing status")


class EventValidationError(BaseModel):
    """Event validation error details."""
    field: str = Field(..., description="Field with validation error")
    error: str = Field(..., description="Validation error message")
    value: Optional[Any] = Field(None, description="Invalid value")
    suggestion: Optional[str] = Field(None, description="Suggested fix")


class EventIngestionStats(BaseModel):
    """Event ingestion statistics."""
    tenant_id: str = Field(..., description="Tenant identifier")
    total_events: int = Field(..., description="Total events ingested")
    events_today: int = Field(..., description="Events ingested today")
    events_this_hour: int = Field(..., description="Events ingested this hour")
    events_this_minute: int = Field(..., description="Events ingested this minute")
    last_event_at: Optional[datetime] = Field(None, description="Timestamp of last event")
    processing_queue_size: int = Field(..., description="Current processing queue size")
    error_rate: float = Field(..., ge=0, le=1, description="Error rate (0-1)")
    
    class Config:
        from_attributes = True


class EventFilter(BaseModel):
    """Event filtering criteria."""
    event_type: Optional[EventType] = Field(None, description="Filter by event type")
    severity: Optional[EventSeverity] = Field(None, description="Filter by severity")
    service: Optional[str] = Field(None, description="Filter by service")
    endpoint: Optional[str] = Field(None, description="Filter by endpoint")
    status_code: Optional[int] = Field(None, description="Filter by HTTP status code")
    user_id: Optional[str] = Field(None, description="Filter by user ID")
    tags: Optional[Dict[str, str]] = Field(None, description="Filter by tags")
    start_time: Optional[datetime] = Field(None, description="Start time for filtering")
    end_time: Optional[datetime] = Field(None, description="End time for filtering")
    limit: int = Field(default=100, ge=1, le=1000, description="Maximum number of events")
    offset: int = Field(default=0, ge=0, description="Number of events to skip")


class EventSearchResponse(BaseModel):
    """Response for event search/filtering."""
    events: List[Dict[str, Any]] = Field(..., description="Filtered events")
    total_count: int = Field(..., description="Total matching events")
    filtered_count: int = Field(..., description="Number of events returned")
    has_more: bool = Field(..., description="Whether more events are available")
    search_id: str = Field(..., description="Search identifier for pagination")
    execution_time_ms: float = Field(..., description="Search execution time in milliseconds")


class EventHealthCheck(BaseModel):
    """Event ingestion health check response."""
    status: str = Field(..., description="Health status")
    timestamp: datetime = Field(..., description="Health check timestamp")
    ingestion_rate: float = Field(..., description="Events per second")
    queue_size: int = Field(..., description="Current queue size")
    worker_status: str = Field(..., description="Worker status")
    last_event_received: Optional[datetime] = Field(None, description="Last event timestamp")
    errors_last_hour: int = Field(..., description="Errors in last hour")
    uptime_seconds: int = Field(..., description="Service uptime in seconds")


class RateLimitInfo(BaseModel):
    """Rate limiting information."""
    limit: int = Field(..., description="Rate limit per time window")
    remaining: int = Field(..., description="Remaining requests in current window")
    reset_time: datetime = Field(..., description="When rate limit resets")
    window_size_seconds: int = Field(..., description="Rate limit window size in seconds")
    exceeded: bool = Field(..., description="Whether rate limit was exceeded")


class EventIngestionConfig(BaseModel):
    """Event ingestion configuration."""
    max_events_per_request: int = Field(default=1000, ge=1, le=10000, description="Maximum events per single request")
    max_batch_size: int = Field(default=1000, ge=1, le=10000, description="Maximum events per batch")
    max_payload_size_mb: int = Field(default=10, ge=1, le=100, description="Maximum payload size in MB")
    enable_validation: bool = Field(default=True, description="Enable event validation")
    enable_rate_limiting: bool = Field(default=True, description="Enable rate limiting")
    enable_compression: bool = Field(default=True, description="Enable request compression")
    retention_days: int = Field(default=90, ge=1, le=3650, description="Event retention period in days")
    enable_analytics: bool = Field(default=True, description="Enable real-time analytics")
    enable_alerting: bool = Field(default=True, description="Enable event-based alerting")
