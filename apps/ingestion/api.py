"""Event ingestion API endpoints for PulseStream."""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from redis import Redis

from core.auth import get_current_tenant
from core.database import get_async_session
from core.logging import get_logger
from core.redis import get_redis_client
from apps.ingestion.schemas import (
    EventIngestionRequest, BatchEventIngestionRequest,
    EventIngestionResponse, BatchEventIngestionResponse,
    EventFilter, EventSearchResponse, EventIngestionStats,
    EventHealthCheck, RateLimitInfo
)
from apps.ingestion.services import get_event_ingestion_service

logger = get_logger(__name__)

# Create router
router = APIRouter(prefix="/ingestion", tags=["Event Ingestion"])


@router.post("/events", response_model=EventIngestionResponse)
async def ingest_single_event(
    event: EventIngestionRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    current_tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_async_session),
    redis_client: Redis = Depends(get_redis_client)
):
    """Ingest a single event."""
    try:
        # Get ingestion service
        ingestion_service = get_event_ingestion_service(redis_client)
        
        # Ingest event
        result = await ingestion_service.ingest_single_event(
            session, event, current_tenant
        )
        
        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": result.message,
                    "errors": result.errors
                }
            )
        
        # Log successful ingestion
        logger.info(
            f"Event ingested successfully: {event.event_id} for tenant {current_tenant.id} "
            f"in {result.processing_time_ms:.2f}ms"
        )
        
        return EventIngestionResponse(
            success=True,
            event_id=event.event_id,
            ingested_at=datetime.utcnow(),
            processing_status="queued",
            message="Event ingested successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Event ingestion failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Event ingestion failed"
        )


@router.post("/events/batch", response_model=BatchEventIngestionResponse)
async def ingest_batch_events(
    batch: BatchEventIngestionRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    current_tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_async_session),
    redis_client: Redis = Depends(get_redis_client)
):
    """Ingest a batch of events."""
    try:
        # Get ingestion service
        ingestion_service = get_event_ingestion_service(redis_client)
        
        # Ingest batch
        result = await ingestion_service.ingest_batch_events(
            session, batch, current_tenant
        )
        
        # Log batch ingestion
        logger.info(
            f"Batch ingested: {batch.batch_id} with {result.successful_events}/{result.total_events} "
            f"successful events for tenant {current_tenant.id}"
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch event ingestion failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Batch event ingestion failed"
        )


@router.get("/events/search", response_model=EventSearchResponse)
async def search_events(
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    severity: Optional[str] = Query(None, description="Filter by severity level"),
    service: Optional[str] = Query(None, description="Filter by service name"),
    endpoint: Optional[str] = Query(None, description="Filter by endpoint"),
    status_code: Optional[int] = Query(None, description="Filter by HTTP status code"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    start_time: Optional[datetime] = Query(None, description="Start time for filtering"),
    end_time: Optional[datetime] = Query(None, description="End time for filtering"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of events"),
    offset: int = Query(0, ge=0, description="Number of events to skip"),
    current_tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_async_session),
    redis_client: Redis = Depends(get_redis_client)
):
    """Search and filter events."""
    try:
        # Build filter
        event_filter = EventFilter(
            event_type=event_type,
            severity=severity,
            service=service,
            endpoint=endpoint,
            status_code=status_code,
            user_id=user_id,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            offset=offset
        )
        
        # Get ingestion service
        ingestion_service = get_event_ingestion_service(redis_client)
        
        # Search events
        result = await ingestion_service.search_events(
            session, str(current_tenant.id), event_filter
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Event search failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Event search failed"
        )


@router.get("/events/{event_id}", response_model=dict)
async def get_event(
    event_id: str,
    current_tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_async_session)
):
    """Get a specific event by ID."""
    try:
        from apps.storage.crud import event_crud
        
        # Get event
        event = await event_crud.get_by_event_id(session, event_id, current_tenant.id)
        
        if not event:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Event not found"
            )
        
        # Convert to dict
        event_dict = {
            "id": str(event.id),
            "event_type": event.event_type,
            "source": event.source,
            "source_version": event.source_version,
            "event_timestamp": event.event_timestamp.isoformat() if event.event_timestamp else None,
            "ingested_at": event.ingested_at.isoformat() if event.ingested_at else None,
            "payload": event.payload,
            "event_metadata": event.event_metadata,
            "external_id": event.external_id,
            "correlation_id": event.correlation_id,
            "processing_status": event.processing_status.value,
            "processed_at": event.processed_at.isoformat() if event.processed_at else None,
            "duration_ms": event.duration_ms,
            "status_code": event.status_code,
            "error_message": event.error_message,
            "geo_country": event.geo_country,
            "geo_city": event.geo_city,
            "user_agent": event.user_agent,
            "device_type": event.device_type,
            "alert_processed": event.alert_processed,
            "alerts_triggered": event.alerts_triggered,
            "tenant_id": str(event.tenant_id)
        }
        
        return event_dict
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get event {event_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve event"
        )


@router.get("/stats", response_model=EventIngestionStats)
async def get_ingestion_stats(
    current_tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_async_session),
    redis_client: Redis = Depends(get_redis_client)
):
    """Get event ingestion statistics for the current tenant."""
    try:
        # Get ingestion service
        ingestion_service = get_event_ingestion_service(redis_client)
        
        # Get stats
        stats = await ingestion_service.get_ingestion_stats(session, str(current_tenant.id))
        
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get ingestion stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve ingestion statistics"
        )


@router.get("/health", response_model=EventHealthCheck)
async def health_check(
    redis_client: Redis = Depends(get_redis_client)
):
    """Health check for event ingestion service."""
    try:
        # Get queue size
        queue_size = redis_client.llen("event_processing_queue")
        
        # Get worker status (simplified for now)
        worker_status = "healthy"
        
        # Calculate ingestion rate (simplified)
        ingestion_rate = 0.0  # This would be calculated from actual metrics
        
        # Get errors in last hour (simplified)
        errors_last_hour = 0  # This would be calculated from actual metrics
        
        # Calculate uptime (simplified)
        uptime_seconds = 3600  # This would be calculated from actual start time
        
        return EventHealthCheck(
            status="healthy",
            timestamp=datetime.utcnow(),
            ingestion_rate=ingestion_rate,
            queue_size=queue_size,
            worker_status=worker_status,
            last_event_received=None,  # This would be retrieved from actual data
            errors_last_hour=errors_last_hour,
            uptime_seconds=uptime_seconds
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return EventHealthCheck(
            status="unhealthy",
            timestamp=datetime.utcnow(),
            ingestion_rate=0.0,
            queue_size=0,
            worker_status="unknown",
            last_event_received=None,
            errors_last_hour=0,
            uptime_seconds=0
        )


@router.get("/rate-limit", response_model=RateLimitInfo)
async def get_rate_limit_info(
    current_tenant = Depends(get_current_tenant),
    redis_client: Redis = Depends(get_redis_client)
):
    """Get current rate limit information for the tenant."""
    try:
        # Get ingestion service
        ingestion_service = get_event_ingestion_service(redis_client)
        
        # Check rate limit
        rate_limit_info = ingestion_service.rate_limit_service.check_rate_limit(
            str(current_tenant.id)
        )
        
        return rate_limit_info
        
    except Exception as e:
        logger.error(f"Failed to get rate limit info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve rate limit information"
        )


@router.delete("/events/{event_id}")
async def delete_event(
    event_id: str,
    current_tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_async_session)
):
    """Delete a specific event by ID."""
    try:
        from apps.storage.crud import event_crud
        
        # Get event
        event = await event_crud.get_by_event_id(session, event_id, current_tenant.id)
        
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found"
            )
        
        # Delete event
        await event_crud.delete(session, event.id)
        
        logger.info(f"Event {event_id} deleted for tenant {current_tenant.id}")
        
        return {"message": "Event deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete event {event_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete event"
        )


@router.post("/events/{event_id}/retry")
async def retry_event_processing(
    event_id: str,
    current_tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_async_session),
    redis_client: Redis = Depends(get_redis_client)
):
    """Retry processing for a specific event."""
    try:
        from apps.storage.crud import event_crud
        
        # Get event
        event = await event_crud.get_by_event_id(session, event_id, current_tenant.id)
        
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found"
            )
        
        # Get ingestion service
        ingestion_service = get_event_ingestion_service(redis_client)
        
        # Queue for reprocessing
        await ingestion_service._queue_for_processing(event)
        
        logger.info(f"Event {event_id} queued for reprocessing for tenant {current_tenant.id}")
        
        return {"message": "Event queued for reprocessing"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retry event {event_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retry event processing"
        )


@router.get("/events/types", response_model=List[str])
async def get_event_types():
    """Get available event types."""
    try:
        from core.constants import EventType
        return [event_type.value for event_type in EventType]
        
    except Exception as e:
        logger.error(f"Failed to get event types: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve event types"
        )


@router.get("/events/severities", response_model=List[str])
async def get_event_severities():
    """Get available event severity levels."""
    try:
        from core.constants import EventSeverity
        return [severity.value for severity in EventSeverity]
        
    except Exception as e:
        logger.error(f"Failed to get event severities: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve event severities"
        )
