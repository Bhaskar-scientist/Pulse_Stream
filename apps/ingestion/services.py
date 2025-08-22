"""Event ingestion services for PulseStream."""

import uuid
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from redis import Redis

from core.logging import get_logger
from core.config import settings
from core.errors import RateLimitExceededError, ValidationError
from apps.storage.models.event import Event
from apps.storage.models.tenant import Tenant
from apps.storage.crud import event_crud, tenant_crud
from apps.ingestion.schemas import (
    EventIngestionRequest, BatchEventIngestionRequest,
    EventIngestionResponse, BatchEventIngestionResponse,
    EventValidationError, EventIngestionStats, EventFilter,
    EventSearchResponse, RateLimitInfo
)

logger = get_logger(__name__)


@dataclass
class EventProcessingResult:
    """Result of event processing."""
    success: bool
    event_id: str
    message: str
    errors: List[str] = None
    processing_time_ms: float = 0.0


class EventValidationService:
    """Service for event validation and sanitization."""
    
    def __init__(self):
        self.max_payload_size_bytes = 10 * 1024 * 1024  # 10MB
        self.max_events_per_batch = 1000
        self.max_title_length = 200
        self.max_message_length = 2000
    
    def validate_single_event(self, event: EventIngestionRequest) -> List[EventValidationError]:
        """Validate a single event."""
        errors = []
        
        # Validate title length
        if len(event.title) > self.max_title_length:
            errors.append(EventValidationError(
                field="title",
                error=f"Title exceeds maximum length of {self.max_title_length} characters",
                value=event.title,
                suggestion="Shorten the title to fit within the limit"
            ))
        
        # Validate message length
        if event.message and len(event.message) > self.max_message_length:
            errors.append(EventValidationError(
                field="message",
                error=f"Message exceeds maximum length of {self.max_message_length} characters",
                value=event.message,
                suggestion="Shorten the message or split into multiple events"
            ))
        
        # Validate payload size
        if event.payload:
            payload_size = len(json.dumps(event.payload, default=str))
            if payload_size > self.max_payload_size_bytes:
                errors.append(EventValidationError(
                    field="payload",
                    error=f"Payload size ({payload_size} bytes) exceeds maximum of {self.max_payload_size_bytes} bytes",
                    value=payload_size,
                    suggestion="Reduce payload size or split into multiple events"
                ))
        
        # Validate metrics if present
        if event.metrics:
            if event.metrics.response_time_ms < 0:
                errors.append(EventValidationError(
                    field="metrics.response_time_ms",
                    error="Response time cannot be negative",
                    value=event.metrics.response_time_ms,
                    suggestion="Use a positive value for response time"
                ))
            
            if not (100 <= event.metrics.status_code <= 599):
                errors.append(EventValidationError(
                    field="metrics.status_code",
                    error="Status code must be between 100 and 599",
                    value=event.metrics.status_code,
                    suggestion="Use a valid HTTP status code"
                ))
        
        # Validate timestamps
        if event.timestamp:
            if event.timestamp > datetime.utcnow() + timedelta(minutes=5):
                errors.append(EventValidationError(
                    field="timestamp",
                    error="Event timestamp cannot be more than 5 minutes in the future",
                    value=event.timestamp.isoformat(),
                    suggestion="Use current time or recent past time"
                ))
        
        return errors
    
    def validate_batch(self, batch: BatchEventIngestionRequest) -> List[EventValidationError]:
        """Validate a batch of events."""
        errors = []
        
        # Validate batch size
        if len(batch.events) > self.max_events_per_batch:
            errors.append(EventValidationError(
                field="events",
                error=f"Batch size ({len(batch.events)}) exceeds maximum of {self.max_events_per_batch}",
                value=len(batch.events),
                suggestion=f"Split into batches of {self.max_events_per_batch} or fewer events"
            ))
        
        # Validate individual events
        for i, event in enumerate(batch.events):
            event_errors = self.validate_single_event(event)
            for error in event_errors:
                error.field = f"events[{i}].{error.field}"
                errors.append(error)
        
        return errors


class RateLimitService:
    """Service for rate limiting event ingestion."""
    
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self.default_rate_limit = 1000  # events per minute
        self.default_window = 60  # seconds
    
    def _get_rate_limit_key(self, tenant_id: str, window: int) -> str:
        """Get Redis key for rate limiting."""
        current_window = int(datetime.utcnow().timestamp() // window)
        return f"rate_limit:{tenant_id}:{current_window}"
    
    def check_rate_limit(self, tenant_id: str, events_count: int = 1) -> RateLimitInfo:
        """Check if tenant has exceeded rate limit."""
        try:
            # Get tenant's rate limit configuration
            rate_limit = self.default_rate_limit
            window_size = self.default_window
            
            # Check current usage
            key = self._get_rate_limit_key(tenant_id, window_size)
            current_usage = self.redis.get(key)
            current_count = int(current_usage) if current_usage else 0
            
            # Calculate remaining requests
            remaining = max(0, rate_limit - current_count)
            exceeded = current_count + events_count > rate_limit
            
            # Calculate reset time
            current_window = int(datetime.utcnow().timestamp() // window_size)
            reset_time = datetime.fromtimestamp((current_window + 1) * window_size)
            
            return RateLimitInfo(
                limit=rate_limit,
                remaining=remaining,
                reset_time=reset_time,
                window_size_seconds=window_size,
                exceeded=exceeded
            )
            
        except Exception as e:
            logger.error(f"Rate limit check failed for tenant {tenant_id}: {e}")
            # Fail open - allow request if rate limiting fails
            return RateLimitInfo(
                limit=self.default_rate_limit,
                remaining=self.default_rate_limit,
                reset_time=datetime.utcnow() + timedelta(seconds=self.default_window),
                window_size_seconds=self.default_window,
                exceeded=False
            )
    
    def increment_usage(self, tenant_id: str, events_count: int = 1) -> None:
        """Increment rate limit usage for tenant."""
        try:
            key = self._get_rate_limit_key(tenant_id, self.default_window)
            self.redis.incr(key, events_count)
            self.redis.expire(key, self.default_window * 2)  # Keep for 2x window size
            
        except Exception as e:
            logger.error(f"Failed to increment rate limit usage for tenant {tenant_id}: {e}")


class EventIngestionService:
    """Service for event ingestion and processing."""
    
    def __init__(self, redis_client: Redis):
        self.validation_service = EventValidationService()
        self.rate_limit_service = RateLimitService(redis_client)
        self.redis = redis_client
    
    async def ingest_single_event(
        self, 
        session: AsyncSession, 
        event: EventIngestionRequest,
        tenant: Tenant
    ) -> EventProcessingResult:
        """Ingest a single event."""
        start_time = datetime.utcnow()
        
        try:
            # Validate event
            validation_errors = self.validation_service.validate_single_event(event)
            if validation_errors:
                return EventProcessingResult(
                    success=False,
                    event_id=event.event_id,
                    message="Event validation failed",
                    errors=[f"{e.field}: {e.error}" for e in validation_errors]
                )
            
            # Check rate limit
            rate_limit_info = self.rate_limit_service.check_rate_limit(str(tenant.id))
            if rate_limit_info.exceeded:
                raise RateLimitExceededError(
                    f"Rate limit exceeded. Limit: {rate_limit_info.limit} events per {rate_limit_info.window_size_seconds} seconds"
                )
            
            # Create event model using the correct Event model structure
            event_model = Event(
                tenant_id=tenant.id,
                event_type=event.event_type.value,
                source=event.source.service if event.source else None,
                source_version=event.source.version if event.source else None,
                event_timestamp=event.timestamp or datetime.utcnow(),
                payload={
                    "title": event.title,
                    "message": event.message,
                    "severity": event.severity.value if event.severity else None,
                    "source": {
                        "service": event.source.service if event.source else None,
                        "endpoint": event.source.endpoint if event.source else None,
                        "method": event.source.method if event.source else None,
                        "version": event.source.version if event.source else None,
                        "environment": event.source.environment if event.source else None
                    } if event.source else None,
                    "context": {
                        "user_id": event.context.user_id if event.context else None,
                        "session_id": event.context.session_id if event.context else None,
                        "request_id": event.context.request_id if event.context else None,
                        "ip_address": event.context.ip_address if event.context else None,
                        "user_agent": event.context.user_agent if event.context else None,
                        "tags": event.context.tags if event.context else None
                    } if event.context else None,
                    "metrics": {
                        "response_time_ms": event.metrics.response_time_ms if event.metrics else None,
                        "status_code": event.metrics.status_code if event.metrics else None,
                        "request_size_bytes": event.metrics.request_size_bytes if event.metrics else None,
                        "response_size_bytes": event.metrics.response_size_bytes if event.metrics else None,
                        "cache_hit": event.metrics.cache_hit if event.metrics else None
                    } if event.metrics else None,
                    "error_details": {
                        "error_code": event.error_details.error_code if event.error_details else None,
                        "error_message": event.error_details.error_message if event.error_details else None,
                        "error_type": event.error_details.error_type if event.error_details else None
                    } if event.error_details else None,
                    "custom_data": event.payload or {}
                },
                event_metadata={
                    "test_run": event.metadata.get("test_run") if event.metadata else None,
                    "priority": event.metadata.get("priority") if event.metadata else None,
                    "tags": event.context.tags if event.context else None,
                    "user_agent": event.context.user_agent if event.context else None,
                    "ip_address": event.context.ip_address if event.context else None,
                    "additional_metadata": event.metadata or {}
                },
                external_id=event.event_id if hasattr(event, 'event_id') else None,
                correlation_id=event.context.request_id if event.context else None,
                duration_ms=event.metrics.response_time_ms if event.metrics else None,
                status_code=event.metrics.status_code if event.metrics else None,
                error_message=event.error_details.error_message if event.error_details else None,
                user_agent=event.context.user_agent if event.context else None
            )
            
            # Save to database
            await event_crud.create(session, obj_in={
                'tenant_id': event_model.tenant_id,
                'event_type': event_model.event_type,
                'source': event_model.source,
                'source_version': event_model.source_version,
                'event_timestamp': event_model.event_timestamp,
                'payload': event_model.payload,
                'event_metadata': event_model.event_metadata,
                'external_id': event_model.external_id,
                'correlation_id': event_model.correlation_id,
                'duration_ms': event_model.duration_ms,
                'status_code': event_model.status_code,
                'error_message': event_model.error_message,
                'user_agent': event_model.user_agent
            })
            
            # Increment rate limit usage
            self.rate_limit_service.increment_usage(str(tenant.id))
            
            # Queue for background processing
            await self._queue_for_processing(event_model)
            
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return EventProcessingResult(
                success=True,
                event_id=event.event_id,
                message="Event ingested successfully",
                processing_time_ms=processing_time
            )
            
        except Exception as e:
            logger.error(f"Event ingestion failed: {e}")
            return EventProcessingResult(
                success=False,
                event_id=event.event_id,
                message="Event ingestion failed",
                errors=[str(e)]
            )
    
    async def ingest_batch_events(
        self, 
        session: AsyncSession, 
        batch: BatchEventIngestionRequest,
        tenant: Tenant
    ) -> BatchEventIngestionResponse:
        """Ingest a batch of events."""
        start_time = datetime.utcnow()
        
        # Validate batch
        validation_errors = self.validation_service.validate_batch(batch)
        if validation_errors:
            raise ValidationError(f"Batch validation failed: {len(validation_errors)} errors")
        
        # Check rate limit for entire batch
        rate_limit_info = self.rate_limit_service.check_rate_limit(str(tenant.id), len(batch.events))
        if rate_limit_info.exceeded:
            raise RateLimitExceededError(
                f"Rate limit exceeded for batch. Limit: {rate_limit_info.limit} events per {rate_limit_info.window_size_seconds} seconds"
            )
        
        # Process events
        results = []
        successful_count = 0
        failed_count = 0
        
        for event in batch.events:
            result = await self.ingest_single_event(session, event, tenant)
            
            response = EventIngestionResponse(
                success=result.success,
                event_id=result.event_id,
                ingested_at=datetime.utcnow(),
                processing_status="queued" if result.success else "failed",
                message=result.message,
                errors=result.errors
            )
            
            results.append(response)
            
            if result.success:
                successful_count += 1
            else:
                failed_count += 1
        
        # Increment rate limit usage for batch
        self.rate_limit_service.increment_usage(str(tenant.id), len(batch.events))
        
        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return BatchEventIngestionResponse(
            batch_id=batch.batch_id,
            total_events=len(batch.events),
            successful_events=successful_count,
            failed_events=failed_count,
            ingested_at=datetime.utcnow(),
            results=results,
            processing_status="completed"
        )
    
    async def _queue_for_processing(self, event: Event) -> None:
        """Queue event for background processing."""
        try:
            # Add to Redis processing queue
            # Determine priority based on event characteristics
            priority = "normal"
            if event.error_message or (event.status_code and event.status_code >= 500):
                priority = "high"
            elif event.status_code and event.status_code >= 400:
                priority = "medium"
                
            queue_data = {
                "event_id": str(event.id),
                "tenant_id": str(event.tenant_id),
                "event_type": event.event_type,
                "timestamp": event.event_timestamp.isoformat(),
                "priority": priority
            }
            
            self.redis.lpush("event_processing_queue", json.dumps(queue_data))
            logger.info(f"Event {event.id} queued for processing")
            
        except Exception as e:
            logger.error(f"Failed to queue event {event.id} for processing: {e}")
    
    async def get_ingestion_stats(self, session: AsyncSession, tenant_id: str) -> EventIngestionStats:
        """Get event ingestion statistics for a tenant."""
        try:
            # Get total events count
            total_events = await event_crud.count_by_tenant(session=session, tenant_id=tenant_id)
            
            # Get today's events count
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            events_today = await event_crud.count_by_tenant_and_time(session, tenant_id, today_start)
            
            # Get this hour's events count
            hour_start = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
            events_this_hour = await event_crud.count_by_tenant_and_time(session, tenant_id, hour_start)
            
            # Get this minute's events count
            minute_start = datetime.utcnow().replace(second=0, microsecond=0)
            events_this_minute = await event_crud.count_by_tenant_and_time(session, tenant_id, minute_start)
            
            # Get last event timestamp
            last_event = await event_crud.get_last_by_tenant(session, tenant_id)
            last_event_at = last_event.event_timestamp if last_event else None
            
            # Get queue size
            queue_size = self.redis.llen("event_processing_queue")
            
            # Calculate error rate (last 24 hours)
            day_ago = datetime.utcnow() - timedelta(days=1)
            error_events = await event_crud.count_by_tenant_and_severity(session, tenant_id, "ERROR", day_ago)
            total_recent = await event_crud.count_by_tenant_and_time(session, tenant_id, day_ago)
            error_rate = error_events / total_recent if total_recent > 0 else 0.0
            
            return EventIngestionStats(
                tenant_id=tenant_id,
                total_events=total_events,
                events_today=events_today,
                events_this_hour=events_this_hour,
                events_this_minute=events_this_minute,
                last_event_at=last_event_at,
                processing_queue_size=queue_size,
                error_rate=error_rate
            )
            
        except Exception as e:
            logger.error(f"Failed to get ingestion stats for tenant {tenant_id}: {e}")
            raise
    
    async def search_events(
        self, 
        session: AsyncSession,
        tenant_id: str, 
        query: str = None,
        limit: int = 10,
        offset: int = 0
    ) -> EventSearchResponse:
        """Search and filter events for a tenant."""
        start_time = datetime.utcnow()
        
        try:
            # Build filter conditions
            conditions = [Event.tenant_id == tenant_id]
            
            if query:
                # Search in multiple fields
                search_conditions = [
                    Event.event_type.ilike(f"%{query}%"),
                    Event.source.ilike(f"%{query}%"),
                    func.jsonb_extract_path_text(Event.payload, 'title').ilike(f"%{query}%"),
                    func.jsonb_extract_path_text(Event.payload, 'message').ilike(f"%{query}%")
                ]
                conditions.append(or_(*search_conditions))
            
            # Get total count
            total_count = await event_crud.count_by_conditions(
                session=session,
                conditions=conditions
            )
            
            # Get filtered events
            events = await event_crud.get_by_conditions(
                session=session,
                conditions=conditions,
                limit=limit, 
                offset=offset,
                order_by=Event.event_timestamp.desc()
            )
            
            # Convert to dict for response using actual Event model fields
            event_dicts = []
            for event in events:
                event_dict = {
                    "id": str(event.id),
                    "event_type": event.event_type,
                    "source": event.source,
                    "source_version": event.source_version,
                    "timestamp": event.event_timestamp.isoformat() if event.event_timestamp else None,
                    "ingested_at": event.ingested_at.isoformat() if event.ingested_at else None,
                    "status_code": event.status_code,
                    "duration_ms": event.duration_ms,
                    "payload": event.payload,
                    "metadata": event.event_metadata,
                    "external_id": event.external_id,
                    "processing_status": event.processing_status
                }
                event_dicts.append(event_dict)
            
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return EventSearchResponse(
                events=event_dicts,
                total_count=total_count,
                filtered_count=len(event_dicts),
                has_more=len(event_dicts) == limit,
                search_id=str(uuid.uuid4()),
                execution_time_ms=execution_time
            )
            
        except Exception as e:
            logger.error(f"Event search failed for tenant {tenant_id}: {e}")
            raise


# Global service instance
event_ingestion_service = None

def get_event_ingestion_service(redis_client: Redis) -> EventIngestionService:
    """Get or create event ingestion service instance."""
    global event_ingestion_service
    if event_ingestion_service is None:
        event_ingestion_service = EventIngestionService(redis_client)
    return event_ingestion_service
