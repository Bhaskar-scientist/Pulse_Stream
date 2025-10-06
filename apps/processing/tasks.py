"""Background processing tasks for PulseStream."""

import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

from celery import Celery
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from core.config import settings
from core.logging import get_logger
from core.redis import get_redis_client_sync

logger = get_logger(__name__)

# Create Celery app
celery_app = Celery(
    "pulse_stream_processing",
    broker=str(settings.redis_url),
    backend=str(settings.redis_url),
    include=["apps.processing.tasks"]
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_always_eager=False,  # Set to True for testing
    result_expires=3600,  # 1 hour
    worker_send_task_events=True,
    task_send_sent_event=True,
    event_queue_expires=3600,
    worker_state_db=None,
    worker_disable_rate_limits=False,
     worker_max_memory_per_child=200000,  # 200MB
     worker_direct=False,
     worker_pool_restarts=True,
     worker_pool="prefork",
     worker_concurrency=4,
     worker_log_format="[%(asctime)s: %(levelname)s/%(processName)s] %(message)s",
     worker_task_log_format="[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s"
 )

# Database connection for background tasks
def get_db_session():
    """Get database session for background tasks."""
    try:
        # Use sync engine for Celery tasks
        sync_database_url = str(settings.database_url).replace("+asyncpg", "")
        engine = create_engine(sync_database_url)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        return SessionLocal()
    except Exception as e:
        logger.error(f"Failed to create database session: {e}")
        raise


@celery_app.task(bind=True, name="process_event")
def process_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process a single event in the background."""
    task_id = self.request.id
    logger.info(f"Starting event processing task {task_id} for event {event_data.get('event_id')}")
    
    try:
        # Extract event information
        event_id = event_data.get("event_id")
        tenant_id = event_data.get("tenant_id")
        event_type = event_data.get("event_type")
        timestamp = event_data.get("timestamp")
        
        # Update task status
        self.update_state(
            state="PROGRESS",
            meta={
                "current": 1,
                "total": 1,
                "status": "Processing event",
                "event_id": event_id
            }
        )
        
        # Process event based on type
        if event_type == "api_request":
            result = process_api_event(event_data)
        elif event_type == "error":
            result = process_error_event(event_data)
        elif event_type == "user_action":
            result = process_user_action_event(event_data)
        else:
            result = process_generic_event(event_data)
        
        # Update task status
        self.update_state(
            state="SUCCESS",
            meta={
                "current": 1,
                "total": 1,
                "status": "Event processed successfully",
                "result": result
            }
        )
        
        logger.info(f"Event processing task {task_id} completed successfully")
        return result
        
    except Exception as e:
        logger.error(f"Event processing task {task_id} failed: {e}")
        
        # Update task status
        self.update_state(
            state="FAILURE",
            meta={
                "current": 0,
                "total": 1,
                "status": f"Event processing failed: {str(e)}",
                "error": str(e)
            }
        )
        
        # Retry task if appropriate
        if self.request.retries < 3:
            raise self.retry(
                countdown=60 * (2 ** self.request.retries),  # Exponential backoff
                max_retries=3
            )
        
        raise


@celery_app.task(bind=True, name="process_batch_events")
def process_batch_events(self, batch_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process a batch of events in the background."""
    task_id = self.request.id
    batch_id = batch_data.get("batch_id")
    events = batch_data.get("events", [])
    
    logger.info(f"Starting batch processing task {task_id} for batch {batch_id} with {len(events)} events")
    
    try:
        results = []
        total_events = len(events)
        
        for i, event_data in enumerate(events):
            # Update task progress
            self.update_state(
                state="PROGRESS",
                meta={
                    "current": i + 1,
                    "total": total_events,
                    "status": f"Processing event {i + 1} of {total_events}",
                    "batch_id": batch_id
                }
            )
            
            # Process individual event
            try:
                result = process_event.delay(event_data)
                results.append({
                    "event_id": event_data.get("event_id"),
                    "task_id": result.id,
                    "status": "queued"
                })
            except Exception as e:
                logger.error(f"Failed to queue event {event_data.get('event_id')}: {e}")
                results.append({
                    "event_id": event_data.get("event_id"),
                    "status": "failed",
                    "error": str(e)
                })
        
        # Update task status
        self.update_state(
            state="SUCCESS",
            meta={
                "current": total_events,
                "total": total_events,
                "status": "Batch processing completed",
                "results": results
            }
        )
        
        logger.info(f"Batch processing task {task_id} completed successfully")
        return {
            "batch_id": batch_id,
            "total_events": total_events,
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Batch processing task {task_id} failed: {e}")
        
        # Update task status
        self.update_state(
            state="FAILURE",
            meta={
                "current": 0,
                "total": total_events,
                "status": f"Batch processing failed: {str(e)}",
                "error": str(e)
            }
        )
        
        raise


@celery_app.task(bind=True, name="enrich_event_data")
def enrich_event_data(self, event_id: str, tenant_id: str) -> Dict[str, Any]:
    """Enrich event data with additional context and analytics."""
    task_id = self.request.id
    logger.info(f"Starting event enrichment task {task_id} for event {event_id}")
    
    try:
        # Get database session
        session = get_db_session()
        
        # Get event from database
        event = session.execute(
            text("SELECT * FROM events WHERE id = :event_id AND tenant_id = :tenant_id"),
            {"event_id": event_id, "tenant_id": tenant_id}
        ).fetchone()
        
        if not event:
            raise ValueError(f"Event {event_id} not found")
        
        # Update task progress
        self.update_state(
            state="PROGRESS",
            meta={
                "current": 1,
                "total": 3,
                "status": "Retrieved event data"
            }
        )
        
        # Enrich with user context
        enriched_data = enrich_user_context(event, session)
        
        self.update_state(
            state="PROGRESS",
            meta={
                "current": 2,
                "total": 3,
                "status": "Enriched user context"
            }
        )
        
        # Enrich with service context
        enriched_data = enrich_service_context(enriched_data, session)
        
        self.update_state(
            state="PROGRESS",
            meta={
                "current": 3,
                "total": 3,
                "status": "Enriched service context"
            }
        )
        
        # Update event with enriched data
        session.execute(
            text("""
                UPDATE events 
                SET event_metadata = :metadata, updated_at = :updated_at
                WHERE id = :event_id
            """),
            {
                "metadata": json.dumps(enriched_data),
                "updated_at": datetime.utcnow(),
                "event_id": event_id
            }
        )
        
        session.commit()
        session.close()
        
        # Update task status
        self.update_state(
            state="SUCCESS",
            meta={
                "current": 3,
                "total": 3,
                "status": "Event enrichment completed",
                "enriched_data": enriched_data
            }
        )
        
        logger.info(f"Event enrichment task {task_id} completed successfully")
        return enriched_data
        
    except Exception as e:
        logger.error(f"Event enrichment task {task_id} failed: {e}")
        
        # Update task status
        self.update_state(
            state="FAILURE",
            meta={
                "current": 0,
                "total": 3,
                "status": f"Event enrichment failed: {str(e)}",
                "error": str(e)
            }
        )
        
        raise


@celery_app.task(bind=True, name="generate_event_analytics")
def generate_event_analytics(self, tenant_id: str, time_range: str = "1h") -> Dict[str, Any]:
    """Generate analytics for events in a given time range."""
    task_id = self.request.id
    logger.info(f"Starting analytics generation task {task_id} for tenant {tenant_id}")
    
    try:
        # Calculate time range
        end_time = datetime.utcnow()
        if time_range == "1h":
            start_time = end_time - timedelta(hours=1)
        elif time_range == "24h":
            start_time = end_time - timedelta(days=1)
        elif time_range == "7d":
            start_time = end_time - timedelta(days=7)
        elif time_range == "30d":
            start_time = end_time - timedelta(days=30)
        else:
            start_time = end_time - timedelta(hours=1)
        
        # Get database session
        session = get_db_session()
        
        # Update task progress
        self.update_state(
            state="PROGRESS",
            meta={
                "current": 1,
                "total": 4,
                "status": "Calculating time range"
            }
        )
        
        # Get event counts by type
        event_counts = session.execute(
            text("""
                SELECT event_type, COUNT(*) as count
                FROM events 
                WHERE tenant_id = :tenant_id 
                AND event_timestamp BETWEEN :start_time AND :end_time
                GROUP BY event_type
            """),
            {
                "tenant_id": tenant_id,
                "start_time": start_time,
                "end_time": end_time
            }
        ).fetchall()
        
        self.update_state(
            state="PROGRESS",
            meta={
                "current": 2,
                "total": 4,
                "status": "Calculated event counts"
            }
        )
        
        # Get event counts by severity
        severity_counts = session.execute(
            text("""
                SELECT severity, COUNT(*) as count
                FROM events 
                WHERE tenant_id = :tenant_id 
                AND event_timestamp BETWEEN :start_time AND :end_time
                GROUP BY severity
            """),
            {
                "tenant_id": tenant_id,
                "start_time": start_time,
                "end_time": end_time
            }
        ).fetchall()
        
        self.update_state(
            state="PROGRESS",
            meta={
                "current": 3,
                "total": 4,
                "status": "Calculated severity counts"
            }
        )
        
        # Get performance metrics
        performance_metrics = session.execute(
            text("""
                SELECT 
                    AVG(response_time_ms) as avg_response_time,
                    MAX(response_time_ms) as max_response_time,
                    MIN(response_time_ms) as min_response_time,
                    COUNT(*) as total_requests
                FROM events 
                WHERE tenant_id = :tenant_id 
                AND event_timestamp BETWEEN :start_time AND :end_time
                AND response_time_ms IS NOT NULL
            """),
            {
                "tenant_id": tenant_id,
                "start_time": start_time,
                "end_time": end_time
            }
        ).fetchone()
        
        self.update_state(
            state="PROGRESS",
            meta={
                "current": 4,
                "total": 4,
                "status": "Calculated performance metrics"
            }
        )
        
        # Compile analytics
        analytics = {
            "tenant_id": tenant_id,
            "time_range": time_range,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "event_counts": {row.event_type: row.count for row in event_counts},
            "severity_counts": {row.severity: row.count for row in severity_counts},
            "performance_metrics": {
                "avg_response_time_ms": float(performance_metrics.avg_response_time) if performance_metrics.avg_response_time else 0,
                "max_response_time_ms": float(performance_metrics.max_response_time) if performance_metrics.max_response_time else 0,
                "min_response_time_ms": float(performance_metrics.min_response_time) if performance_metrics.min_response_time else 0,
                "total_requests": performance_metrics.total_requests or 0
            },
            "generated_at": datetime.utcnow().isoformat()
        }
        
        # Store analytics in Redis for caching
        redis_client = get_redis_client_sync()
        cache_key = f"analytics:{tenant_id}:{time_range}"
        redis_client.setex(cache_key, 300, json.dumps(analytics))  # Cache for 5 minutes
        
        session.close()
        
        # Update task status
        self.update_state(
            state="SUCCESS",
            meta={
                "current": 4,
                "total": 4,
                "status": "Analytics generation completed",
                "analytics": analytics
            }
        )
        
        logger.info(f"Analytics generation task {task_id} completed successfully")
        return analytics
        
    except Exception as e:
        logger.error(f"Analytics generation task {task_id} failed: {e}")
        
        # Update task status
        self.update_state(
            state="FAILURE",
            meta={
                "current": 0,
                "total": 4,
                "status": f"Analytics generation failed: {str(e)}",
                "error": str(e)
            }
        )
        
        raise


@celery_app.task(bind=True, name="cleanup_old_events")
def cleanup_old_events(self, tenant_id: str, retention_days: int = 90) -> Dict[str, Any]:
    """Clean up old events based on retention policy."""
    task_id = self.request.id
    logger.info(f"Starting event cleanup task {task_id} for tenant {tenant_id}")
    
    try:
        # Calculate cutoff date
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
        
        # Get database session
        session = get_db_session()
        
        # Update task progress
        self.update_state(
            state="PROGRESS",
            meta={
                "current": 1,
                "total": 3,
                "status": "Calculated cutoff date"
            }
        )
        
        # Count events to be deleted
        count_result = session.execute(
            text("""
                SELECT COUNT(*) as count
                FROM events 
                WHERE tenant_id = :tenant_id 
                AND event_timestamp < :cutoff_date
            """),
            {
                "tenant_id": tenant_id,
                "cutoff_date": cutoff_date
            }
        ).fetchone()
        
        events_to_delete = count_result.count
        
        self.update_state(
            state="PROGRESS",
            meta={
                "current": 2,
                "total": 3,
                "status": f"Found {events_to_delete} events to delete"
            }
        )
        
        # Delete old events
        if events_to_delete > 0:
            delete_result = session.execute(
                text("""
                    DELETE FROM events 
                    WHERE tenant_id = :tenant_id 
                    AND event_timestamp < :cutoff_date
                """),
                {
                    "tenant_id": tenant_id,
                    "cutoff_date": cutoff_date
                }
            )
            
            session.commit()
            
            deleted_count = delete_result.rowcount
        else:
            deleted_count = 0
        
        self.update_state(
            state="PROGRESS",
            meta={
                "current": 3,
                "total": 3,
                "status": f"Deleted {deleted_count} events"
            }
        )
        
        session.close()
        
        # Update task status
        self.update_state(
            state="SUCCESS",
            meta={
                "current": 3,
                "total": 3,
                "status": "Event cleanup completed",
                "deleted_count": deleted_count,
                "retention_days": retention_days
            }
        )
        
        logger.info(f"Event cleanup task {task_id} completed successfully. Deleted {deleted_count} events.")
        return {
            "tenant_id": tenant_id,
            "deleted_count": deleted_count,
            "retention_days": retention_days,
            "cutoff_date": cutoff_date.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Event cleanup task {task_id} failed: {e}")
        
        # Update task status
        self.update_state(
            state="FAILURE",
            meta={
                "current": 0,
                "total": 3,
                "status": f"Event cleanup failed: {str(e)}",
                "error": str(e)
            }
        )
        
        raise


# Helper functions for event processing
def process_api_event(event_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process API request/response events."""
    # Extract API-specific data
    response_time = event_data.get("response_time_ms", 0)
    status_code = event_data.get("status_code", 200)
    
    # Categorize response
    if status_code >= 400:
        category = "error"
    elif status_code >= 300:
        category = "redirect"
    elif status_code >= 200:
        category = "success"
    else:
        category = "informational"
    
    # Performance analysis
    performance = "excellent"
    if response_time > 1000:
        performance = "poor"
    elif response_time > 500:
        performance = "fair"
    elif response_time > 200:
        performance = "good"
    
    return {
        "category": category,
        "performance": performance,
        "processed_at": datetime.utcnow().isoformat()
    }


def process_error_event(event_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process error events."""
    # Extract error information
    error_code = event_data.get("error_code", "unknown")
    error_message = event_data.get("error_message", "")
    
    # Categorize error
    if "timeout" in error_message.lower():
        category = "timeout"
    elif "validation" in error_message.lower():
        category = "validation"
    elif "authentication" in error_message.lower():
        category = "auth"
    elif "permission" in error_message.lower():
        category = "permission"
    else:
        category = "general"
    
    return {
        "category": category,
        "processed_at": datetime.utcnow().isoformat()
    }


def process_user_action_event(event_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process user action events."""
    # Extract user action information
    user_id = event_data.get("user_id", "unknown")
    action = event_data.get("action", "unknown")
    
    return {
        "user_id": user_id,
        "action": action,
        "processed_at": datetime.utcnow().isoformat()
    }


def process_generic_event(event_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process generic events."""
    return {
        "category": "generic",
        "processed_at": datetime.utcnow().isoformat()
    }


def enrich_user_context(event: Any, session) -> Dict[str, Any]:
    """Enrich event with user context information."""
    enriched = {}
    
    if event.user_id:
        # Get user information
        user_result = session.execute(
            text("SELECT role, is_active FROM users WHERE id = :user_id"),
            {"user_id": event.user_id}
        ).fetchone()
        
        if user_result:
            enriched["user_context"] = {
                "role": user_result.role,
                "is_active": user_result.is_active
            }
    
    return enriched


def enrich_service_context(event_data: Dict[str, Any], session) -> Dict[str, Any]:
    """Enrich event with service context information."""
    enriched = event_data.copy()
    
    # Add service metadata
    enriched["service_context"] = {
        "environment": event_data.get("source_environment", "unknown"),
        "version": event_data.get("source_version", "unknown"),
        "enriched_at": datetime.utcnow().isoformat()
    }
    
    return enriched


# Task routing
@celery_app.task(name="heartbeat")
def heartbeat():
    """Heartbeat task to check if workers are alive."""
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat(),
        "worker_id": uuid.uuid4().hex
    }


# Export Celery app
__all__ = ["celery_app", "process_event", "process_batch_events", "enrich_event_data", 
           "generate_event_analytics", "cleanup_old_events", "heartbeat"]
