"""Real-time dashboard services for PulseStream."""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Callable
from uuid import UUID
from collections import defaultdict

from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc
from sqlalchemy.orm import selectinload

from core.logging import get_logger
from core.constants import EventType, EventSeverity, TIME_WINDOWS
from apps.storage.models.event import Event
from apps.storage.models.alert import Alert, AlertRule
from apps.storage.crud import event_crud, alert_crud, alert_rule_crud

logger = get_logger(__name__)


class DashboardConnectionManager:
    """Manages WebSocket connections for real-time dashboard updates."""
    
    def __init__(self):
        self.active_connections: Dict[UUID, Set[WebSocket]] = defaultdict(set)
        self.connection_metadata: Dict[WebSocket, Dict[str, Any]] = {}
    
    async def connect(self, websocket: WebSocket, tenant_id: UUID, user_id: Optional[UUID] = None):
        """Connect a new WebSocket client."""
        try:
            await websocket.accept()
            
            # Store connection
            self.active_connections[tenant_id].add(websocket)
            self.connection_metadata[websocket] = {
                "tenant_id": tenant_id,
                "user_id": user_id,
                "connected_at": datetime.utcnow(),
                "subscriptions": set(),
                "last_heartbeat": datetime.utcnow()
            }
            
            logger.info(f"WebSocket connected for tenant {tenant_id}")
            
            # Send welcome message
            await self.send_personal_message(websocket, {
                "type": "connection_established",
                "tenant_id": str(tenant_id),
                "timestamp": datetime.utcnow().isoformat(),
                "message": "Connected to PulseStream Real-time Dashboard"
            })
            
        except Exception as e:
            logger.error(f"Error connecting WebSocket: {e}")
            raise
    
    def disconnect(self, websocket: WebSocket):
        """Disconnect a WebSocket client."""
        try:
            # Find tenant_id for this connection
            tenant_id = None
            for tid, connections in self.active_connections.items():
                if websocket in connections:
                    tenant_id = tid
                    connections.remove(websocket)
                    break
            
            if tenant_id:
                # Remove from metadata
                if websocket in self.connection_metadata:
                    del self.connection_metadata[websocket]
                
                logger.info(f"WebSocket disconnected from tenant {tenant_id}")
                
        except Exception as e:
            logger.error(f"Error disconnecting WebSocket: {e}")
    
    async def send_personal_message(self, websocket: WebSocket, message: Dict[str, Any]):
        """Send a message to a specific WebSocket client."""
        try:
            if websocket in self.connection_metadata:
                await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            self.disconnect(websocket)
    
    async def broadcast_to_tenant(self, tenant_id: UUID, message: Dict[str, Any]):
        """Broadcast a message to all connections for a specific tenant."""
        if tenant_id not in self.active_connections:
            return
        
        disconnected = set()
        for websocket in self.active_connections[tenant_id]:
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error broadcasting to WebSocket: {e}")
                disconnected.add(websocket)
        
        # Remove disconnected connections
        for websocket in disconnected:
            self.disconnect(websocket)
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics."""
        total_connections = sum(len(connections) for connections in self.active_connections.values())
        tenant_connections = {str(tid): len(connections) for tid, connections in self.active_connections.items()}
        
        return {
            "total_connections": total_connections,
            "tenant_connections": tenant_connections,
            "active_tenants": len(self.active_connections)
        }


class DashboardDataService:
    """Service for aggregating and providing dashboard data."""
    
    def __init__(self, connection_manager: DashboardConnectionManager):
        self.connection_manager = connection_manager
        self.cache: Dict[str, Any] = {}
        self.cache_ttl: Dict[str, datetime] = {}
        self.cache_duration = timedelta(seconds=30)  # 30 seconds cache
    
    async def get_dashboard_overview(
        self, 
        session: AsyncSession, 
        tenant_id: UUID
    ) -> Dict[str, Any]:
        """Get dashboard overview data."""
        try:
            # Check cache first
            cache_key = f"dashboard_overview_{tenant_id}"
            if self._is_cache_valid(cache_key):
                return self.cache[cache_key]
            
            # Get real-time data
            current_time = datetime.utcnow()
            
            # Event counts by type (last 24 hours)
            event_counts = await self._get_event_counts_by_type(session, tenant_id, current_time)
            
            # Error rate (last hour)
            error_rate = await self._get_error_rate(session, tenant_id, current_time)
            
            # Response time statistics (last hour)
            response_time_stats = await self._get_response_time_stats(session, tenant_id, current_time)
            
            # Active alerts count
            active_alerts_count = await self._get_active_alerts_count(session, tenant_id)
            
            # Recent events (last 10)
            recent_events = await self._get_recent_events(session, tenant_id, limit=10)
            
            # System health indicators
            system_health = await self._get_system_health(session, tenant_id, current_time)
            
            overview_data = {
                "tenant_id": str(tenant_id),
                "timestamp": current_time.isoformat(),
                "event_counts": event_counts,
                "error_rate": error_rate,
                "response_time_stats": response_time_stats,
                "active_alerts_count": active_alerts_count,
                "recent_events": recent_events,
                "system_health": system_health
            }
            
            # Cache the result
            self._cache_data(cache_key, overview_data)
            
            return overview_data
            
        except Exception as e:
            logger.error(f"Error getting dashboard overview: {e}")
            return {}
    
    async def _get_event_counts_by_type(
        self, 
        session: AsyncSession, 
        tenant_id: UUID, 
        current_time: datetime
    ) -> Dict[str, int]:
        """Get event counts by type for the last 24 hours."""
        try:
            since_time = current_time - timedelta(hours=24)
            
            # Get counts by event type
            query = select(
                Event.event_type,
                func.count(Event.id).label('count')
            ).where(
                and_(
                    Event.tenant_id == tenant_id,
                    Event.event_timestamp >= since_time,
                    Event.is_deleted == False
                )
            ).group_by(Event.event_type)
            
            result = await session.execute(query)
            counts = {row.event_type: row.count for row in result}
            
            # Ensure all event types are represented
            for event_type in EventType:
                if event_type.value not in counts:
                    counts[event_type.value] = 0
            
            return counts
            
        except Exception as e:
            logger.error(f"Error getting event counts by type: {e}")
            return {}
    
    async def _get_error_rate(
        self, 
        session: AsyncSession, 
        tenant_id: UUID, 
        current_time: datetime
    ) -> float:
        """Get error rate for the last hour."""
        try:
            since_time = current_time - timedelta(hours=1)
            
            # Total events
            total_query = select(func.count(Event.id)).where(
                and_(
                    Event.tenant_id == tenant_id,
                    Event.event_timestamp >= since_time,
                    Event.is_deleted == False
                )
            )
            total_result = await session.execute(total_query)
            total_events = total_result.scalar() or 0
            
            if total_events == 0:
                return 0.0
            
            # Error events (status code >= 400)
            error_query = select(func.count(Event.id)).where(
                and_(
                    Event.tenant_id == tenant_id,
                    Event.event_timestamp >= since_time,
                    Event.is_deleted == False,
                    Event.status_code >= 400
                )
            )
            error_result = await session.execute(error_query)
            error_events = error_result.scalar() or 0
            
            return (error_events / total_events) * 100
            
        except Exception as e:
            logger.error(f"Error getting error rate: {e}")
            return 0.0
    
    async def _get_response_time_stats(
        self, 
        session: AsyncSession, 
        tenant_id: UUID, 
        current_time: datetime
    ) -> Dict[str, float]:
        """Get response time statistics for the last hour."""
        try:
            since_time = current_time - timedelta(hours=1)
            
            query = select(
                func.avg(Event.duration_ms).label('avg'),
                func.min(Event.duration_ms).label('min'),
                func.max(Event.duration_ms).label('max')
            ).where(
                and_(
                    Event.tenant_id == tenant_id,
                    Event.event_timestamp >= since_time,
                    Event.is_deleted == False,
                    Event.duration_ms.isnot(None)
                )
            )
            
            result = await session.execute(query)
            row = result.first()
            
            if row and row.avg is not None:
                return {
                    "avg": float(row.avg),
                    "min": float(row.min) if row.min else 0.0,
                    "max": float(row.max) if row.max else 0.0
                }
            else:
                return {"avg": 0.0, "min": 0.0, "max": 0.0}
                
        except Exception as e:
            logger.error(f"Error getting response time stats: {e}")
            return {"avg": 0.0, "min": 0.0, "max": 0.0}
    
    async def _get_active_alerts_count(
        self, 
        session: AsyncSession, 
        tenant_id: UUID
    ) -> int:
        """Get count of active alerts."""
        try:
            return await alert_crud.count_by_status(session, tenant_id, "active")
        except Exception as e:
            logger.error(f"Error getting active alerts count: {e}")
            return 0
    
    async def _get_recent_events(
        self, 
        session: AsyncSession, 
        tenant_id: UUID, 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get recent events."""
        try:
            events = await event_crud.get_recent_by_tenant(session, tenant_id, limit)
            
            # Convert SQLAlchemy objects to dictionaries
            event_list = []
            for event in events:
                event_dict = {
                    "id": str(event.id),
                    "event_type": event.event_type,
                    "timestamp": event.event_timestamp.isoformat() if event.event_timestamp else None,
                    "status_code": event.status_code,
                    "duration_ms": event.duration_ms,
                    "source": event.source,
                    "payload": event.payload,
                    "event_metadata": event.event_metadata
                }
                event_list.append(event_dict)
            
            return event_list
        except Exception as e:
            logger.error(f"Error getting recent events: {e}")
            return []
    
    async def _get_system_health(
        self, 
        session: AsyncSession, 
        tenant_id: UUID, 
        current_time: datetime
    ) -> Dict[str, Any]:
        """Get system health indicators."""
        try:
            # Check for recent errors
            since_time = current_time - timedelta(minutes=5)
            recent_errors = await event_crud.count_by_conditions(
                session,
                [
                    Event.tenant_id == tenant_id,
                    Event.event_timestamp >= since_time,
                    Event.status_code >= 400
                ]
            )
            
            # Determine health status
            if recent_errors > 10:
                health_status = "critical"
            elif recent_errors > 5:
                health_status = "warning"
            elif recent_errors > 0:
                health_status = "degraded"
            else:
                health_status = "healthy"
            
            return {
                "status": health_status,
                "recent_errors": recent_errors,
                "last_check": current_time.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting system health: {e}")
            return {"status": "unknown", "last_check": current_time.isoformat()}
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached data is still valid."""
        if cache_key not in self.cache or cache_key not in self.cache_ttl:
            return False
        
        return datetime.utcnow() < self.cache_ttl[cache_key]
    
    def _cache_data(self, cache_key: str, data: Any):
        """Cache data with TTL."""
        self.cache[cache_key] = data
        self.cache_ttl[cache_key] = datetime.utcnow() + self.cache_duration


# Global instances
connection_manager = DashboardConnectionManager()
data_service = DashboardDataService(connection_manager)
