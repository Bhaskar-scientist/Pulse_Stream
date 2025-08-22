"""Dashboard API endpoints for PulseStream."""

from datetime import datetime
from typing import Dict, Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import get_current_tenant
from core.database import get_async_session
from core.logging import get_logger
from apps.dashboard.services import data_service, connection_manager
from apps.dashboard.websocket import websocket_handler
from apps.storage.models.tenant import Tenant

logger = get_logger(__name__)

# Create router
router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/overview", response_model=Dict[str, Any])
async def get_dashboard_overview(
    current_tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_async_session)
):
    """Get dashboard overview data."""
    try:
        data = await data_service.get_dashboard_overview(session, current_tenant.id)
        
        if not data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve dashboard data"
            )
        
        return {
            "success": True,
            "data": data,
            "tenant_id": str(current_tenant.id)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting dashboard overview: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve dashboard overview"
        )


@router.get("/events/stream", response_model=Dict[str, Any])
async def get_event_stream(
    limit: int = 50,
    current_tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_async_session)
):
    """Get recent events for streaming display."""
    try:
        from apps.storage.crud import event_crud
        
        events = await event_crud.get_recent_by_tenant(session, current_tenant.id, limit)
        
        # Format for streaming
        stream_data = []
        for event in events:
            stream_data.append({
                "id": str(event.id),
                "event_type": event.event_type,
                "timestamp": event.event_timestamp.isoformat(),
                "status_code": event.status_code,
                "duration_ms": event.duration_ms,
                "source": event.source,
                "payload": event.payload,
                "event_metadata": event.event_metadata
            })
        
        return {
            "success": True,
            "events": stream_data,
            "total_count": len(stream_data),
            "tenant_id": str(current_tenant.id)
        }
        
    except Exception as e:
        logger.error(f"Error getting event stream: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve event stream"
        )


@router.get("/alerts/summary", response_model=Dict[str, Any])
async def get_alert_summary(
    current_tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_async_session)
):
    """Get alert summary for dashboard."""
    try:
        from apps.storage.crud import alert_crud, alert_rule_crud
        
        # Get active alerts
        active_alerts = await alert_crud.get_active_alerts(session, current_tenant.id, limit=20)
        
        # Get alert rules
        alert_rules = await alert_rule_crud.get_active_rules(session, current_tenant.id)
        
        # Count by severity
        severity_counts = {}
        for alert in active_alerts:
            severity = alert.severity
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        # Recent alert activity
        recent_alerts = await alert_crud.get_recent_alerts(session, current_tenant.id, limit=10)
        
        summary_data = {
            "tenant_id": str(current_tenant.id),
            "active_alerts_count": len(active_alerts),
            "severity_distribution": severity_counts,
            "total_rules": len(alert_rules),
            "recent_alerts": [
                {
                    "id": str(alert.id),
                    "title": alert.title,
                    "severity": alert.severity,
                    "triggered_at": alert.triggered_at.isoformat() if alert.triggered_at else None
                }
                for alert in recent_alerts
            ]
        }
        
        return {
            "success": True,
            "data": summary_data
        }
        
    except Exception as e:
        logger.error(f"Error getting alert summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve alert summary"
        )


@router.get("/metrics/real-time", response_model=Dict[str, Any])
async def get_real_time_metrics(
    time_window: str = "1h",
    current_tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_async_session)
):
    """Get real-time metrics for a specific time window."""
    try:
        from apps.storage.models.event import Event
        from apps.storage.crud import event_crud
        from sqlalchemy import select, and_, func
        from datetime import timedelta
        
        # Parse time window
        window_seconds = _parse_time_window(time_window)
        since_time = datetime.utcnow() - timedelta(seconds=window_seconds)
        
        # Get event volume
        event_volume_query = select(
            func.date_trunc('minute', Event.event_timestamp).label('minute'),
            func.count(Event.id).label('count')
        ).where(
            and_(
                Event.tenant_id == current_tenant.id,
                Event.event_timestamp >= since_time,
                Event.is_deleted == False
            )
        ).group_by(
            func.date_trunc('minute', Event.event_timestamp)
        ).order_by(
            func.date_trunc('minute', Event.event_timestamp)
        )
        
        event_volume_result = await session.execute(event_volume_query)
        event_volume = [
            {
                "timestamp": row.minute.isoformat(),
                "count": row.count
            }
            for row in event_volume_result
        ]
        
        # Get error trend
        error_trend_query = select(
            func.date_trunc('minute', Event.event_timestamp).label('minute'),
            func.count(Event.id).label('total'),
            func.sum(
                func.case((Event.status_code >= 400, 1), else_=0)
            ).label('errors')
        ).where(
            and_(
                Event.tenant_id == current_tenant.id,
                Event.event_timestamp >= since_time,
                Event.is_deleted == False
            )
        ).group_by(
            func.date_trunc('minute', Event.event_timestamp)
        ).order_by(
            func.date_trunc('minute', Event.event_timestamp)
        )
        
        error_trend_result = await session.execute(error_trend_query)
        error_trend = [
            {
                "timestamp": row.minute.isoformat(),
                "total": row.total,
                "errors": row.errors,
                "error_rate": round((row.errors / row.total * 100), 2) if row.total > 0 else 0
            }
            for row in error_trend_result
        ]
        
        # Get top endpoints
        top_endpoints_query = select(
            func.jsonb_extract_path_text(Event.payload, 'endpoint').label('endpoint'),
            func.count(Event.id).label('count'),
            func.avg(Event.duration_ms).label('avg_response_time'),
            func.sum(
                func.case((Event.status_code >= 400, 1), else_=0)
            ).label('error_count')
        ).where(
            and_(
                Event.tenant_id == current_tenant.id,
                Event.event_timestamp >= since_time,
                Event.is_deleted == False,
                func.jsonb_extract_path_text(Event.payload, 'endpoint').isnot(None)
            )
        ).group_by(
            func.jsonb_extract_path_text(Event.payload, 'endpoint')
        ).order_by(
            func.count(Event.id).desc()
        ).limit(10)
        
        top_endpoints_result = await session.execute(top_endpoints_query)
        top_endpoints = [
            {
                "endpoint": row.endpoint,
                "request_count": row.count,
                "avg_response_time": round(float(row.avg_response_time), 2) if row.avg_response_time else 0,
                "error_count": row.error_count,
                "error_rate": round((row.error_count / row.count * 100), 2) if row.count > 0 else 0
            }
            for row in top_endpoints_result
        ]
        
        metrics_data = {
            "tenant_id": str(current_tenant.id),
            "time_window": time_window,
            "since": since_time.isoformat(),
            "until": datetime.utcnow().isoformat(),
            "event_volume": event_volume,
            "error_trend": error_trend,
            "top_endpoints": top_endpoints
        }
        
        return {
            "success": True,
            "data": metrics_data
        }
        
    except Exception as e:
        logger.error(f"Error getting real-time metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve real-time metrics"
        )


@router.get("/connections/stats", response_model=Dict[str, Any])
async def get_connection_stats():
    """Get WebSocket connection statistics."""
    try:
        stats = connection_manager.get_connection_stats()
        
        return {
            "success": True,
            "data": stats,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting connection stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve connection statistics"
        )


@router.websocket("/ws/{tenant_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    tenant_id: UUID
):
    """WebSocket endpoint for real-time dashboard updates."""
    try:
        # For now, we'll use a default tenant ID
        # In production, this should be validated against the authenticated user
        await websocket_handler.handle_websocket(websocket, tenant_id)
        
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")


def _parse_time_window(time_window: str) -> int:
    """Parse time window string to seconds."""
    try:
        if time_window.endswith('s'):
            return int(time_window[:-1])
        elif time_window.endswith('m'):
            return int(time_window[:-1]) * 60
        elif time_window.endswith('h'):
            return int(time_window[:-1]) * 3600
        elif time_window.endswith('d'):
            return int(time_window[:-1]) * 86400
        else:
            return 3600  # Default to 1 hour
    except ValueError:
        return 3600
