"""Event model for time-series data storage."""

from typing import Any, Dict, Optional

from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from core.database import Base, TenantMixin
from core.constants import EventType, ProcessingStatus, MAX_STRING_LENGTH


class Event(Base, TenantMixin):
    """Event model for storing time-series event data."""
    
    __tablename__ = "events"
    
    # Event Classification
    event_type = Column(
        String(50),
        nullable=False,
        index=True,
        doc="Type of event (api_call, user_action, system_event, etc.)"
    )
    
    # Event Source Information
    source = Column(
        String(MAX_STRING_LENGTH),
        nullable=True,
        index=True,
        doc="Source of the event (service name, application, etc.)"
    )
    
    source_version = Column(
        String(50),
        nullable=True,
        doc="Version of the source system"
    )
    
    # Event Timing
    event_timestamp = Column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        doc="When the event actually occurred (vs when it was ingested)"
    )
    
    ingested_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
        doc="When the event was ingested into PulseStream"
    )
    
    # Event Data
    payload = Column(
        JSONB,
        nullable=False,
        doc="JSON payload containing event data"
    )
    
    # Event Metadata
    event_metadata = Column(
        JSONB,
        nullable=True,
        doc="Additional metadata (user_agent, ip, geo, etc.)"
    )
    
    # Event Identification
    external_id = Column(
        String(MAX_STRING_LENGTH),
        nullable=True,
        index=True,
        doc="External identifier from source system"
    )
    
    correlation_id = Column(
        String(MAX_STRING_LENGTH),
        nullable=True,
        index=True,
        doc="Correlation ID for tracing related events"
    )
    
    # Processing Information
    processing_status = Column(
        String(20),
        default=ProcessingStatus.PENDING,
        nullable=False,
        index=True,
        doc="Processing status (pending, processing, completed, failed)"
    )
    
    processed_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="When the event was processed"
    )
    
    # Event Metrics (extracted from payload for easy querying)
    duration_ms = Column(
        Integer,
        nullable=True,
        index=True,
        doc="Duration in milliseconds (for API calls, etc.)"
    )
    
    status_code = Column(
        Integer,
        nullable=True,
        index=True,
        doc="Status code (HTTP status, etc.)"
    )
    
    error_message = Column(
        Text,
        nullable=True,
        doc="Error message if event represents an error"
    )
    
    # Enrichment Data
    geo_country = Column(
        String(3),
        nullable=True,
        index=True,
        doc="Country code from IP geolocation"
    )
    
    geo_city = Column(
        String(100),
        nullable=True,
        doc="City from IP geolocation"
    )
    
    user_agent = Column(
        Text,
        nullable=True,
        doc="User agent string"
    )
    
    device_type = Column(
        String(50),
        nullable=True,
        index=True,
        doc="Device type (mobile, desktop, tablet, etc.)"
    )
    
    # Alert Processing
    alert_processed = Column(
        String(10),
        default="false",
        nullable=False,
        index=True,
        doc="Whether this event has been processed for alerts"
    )
    
    alerts_triggered = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Number of alerts triggered by this event"
    )
    
    # Relationships
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Tenant this event belongs to"
    )
    
    tenant = relationship(
        "Tenant",
        back_populates="events",
        lazy="select"
    )
    
    # Database optimizations
    __table_args__ = (
        # Time-based index for efficient querying by time ranges
        Index('idx_events_tenant_timestamp', 'tenant_id', 'event_timestamp'),
        Index('idx_events_tenant_type_timestamp', 'tenant_id', 'event_type', 'event_timestamp'),
        Index('idx_events_processing_status', 'processing_status', 'tenant_id'),
        Index('idx_events_alert_processing', 'alert_processed', 'tenant_id'),
        
        # Indexes for common query patterns
        Index('idx_events_status_code', 'tenant_id', 'status_code'),
        Index('idx_events_duration', 'tenant_id', 'duration_ms'),
        Index('idx_events_correlation', 'tenant_id', 'correlation_id'),
        
        # Index for JSON payload queries (examples)
        Index('idx_events_payload_endpoint', func.expr(
            "((payload->>'endpoint'))"
        ), postgresql_using='gin'),
        Index('idx_events_payload_user_id', func.expr(
            "((payload->>'user_id'))"
        ), postgresql_using='gin'),
    )
    
    @property
    def is_error(self) -> bool:
        """Check if this event represents an error."""
        return (
            self.status_code and self.status_code >= 400
        ) or bool(self.error_message)
    
    @property
    def is_slow(self) -> bool:
        """Check if this event represents a slow operation (>1s)."""
        return self.duration_ms and self.duration_ms > 1000
    
    def get_payload_value(self, key: str, default: Any = None) -> Any:
        """Get a value from the JSON payload."""
        if not self.payload:
            return default
        return self.payload.get(key, default)
    
    def set_payload_value(self, key: str, value: Any) -> None:
        """Set a value in the JSON payload."""
        if not self.payload:
            self.payload = {}
        self.payload[key] = value
    
    def get_metadata_value(self, key: str, default: Any = None) -> Any:
        """Get a value from the metadata."""
        if not self.event_metadata:
            return default
        return self.event_metadata.get(key, default)
    
    def set_metadata_value(self, key: str, value: Any) -> None:
        """Set a value in the metadata."""
        if not self.event_metadata:
            self.event_metadata = {}
        self.event_metadata[key] = value
    
    def mark_processed(self) -> None:
        """Mark event as processed."""
        self.processing_status = ProcessingStatus.COMPLETED
        self.processed_at = func.now()
    
    def mark_failed(self, error: str) -> None:
        """Mark event processing as failed."""
        self.processing_status = ProcessingStatus.FAILED
        self.error_message = error
        self.processed_at = func.now()
    
    def mark_alert_processed(self) -> None:
        """Mark event as processed for alerts."""
        self.alert_processed = "true"
    
    def add_alert_triggered(self) -> None:
        """Increment the alert counter."""
        self.alerts_triggered += 1
    
    def extract_common_metrics(self) -> None:
        """Extract common metrics from payload for indexing."""
        if not self.payload:
            return
        
        # Extract duration
        duration = self.payload.get('duration_ms') or self.payload.get('response_time')
        if duration and isinstance(duration, (int, float)):
            self.duration_ms = int(duration)
        
        # Extract status code
        status = self.payload.get('status_code') or self.payload.get('status')
        if status and isinstance(status, int):
            self.status_code = status
        
        # Extract error message
        error = self.payload.get('error') or self.payload.get('error_message')
        if error and isinstance(error, str):
            self.error_message = error
    
    def enrich_from_metadata(self) -> None:
        """Extract enrichment data from metadata."""
        if not self.event_metadata:
            return
        
        # Extract geo information
        geo = self.event_metadata.get('geo', {})
        if isinstance(geo, dict):
            self.geo_country = geo.get('country')
            self.geo_city = geo.get('city')
        
        # Extract user agent
        self.user_agent = self.event_metadata.get('user_agent')
        
        # Extract device type
        self.device_type = self.event_metadata.get('device_type')
    
    def to_dict_summary(self) -> Dict[str, Any]:
        """Convert to dictionary with summary information."""
        return {
            'id': str(self.id),
            'event_type': self.event_type,
            'event_timestamp': self.event_timestamp.isoformat() if self.event_timestamp else None,
            'status_code': self.status_code,
            'duration_ms': self.duration_ms,
            'is_error': self.is_error,
            'source': self.source,
        }
    
    def __str__(self) -> str:
        """String representation."""
        return f"Event({self.event_type})"
    
    def __repr__(self) -> str:
        """Detailed representation."""
        return (
            f"<Event(id={self.id}, type='{self.event_type}', "
            f"timestamp={self.event_timestamp}, tenant_id={self.tenant_id})>"
        )
