"""WebSocket handler for PulseStream real-time dashboard."""

import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from uuid import UUID

from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from core.logging import get_logger
from core.database import get_async_session
from apps.dashboard.services import connection_manager, data_service

logger = get_logger(__name__)


class DashboardWebSocketHandler:
    """Handles WebSocket connections and messages for the dashboard."""
    
    async def handle_websocket(
        self, 
        websocket: WebSocket, 
        tenant_id: UUID, 
        user_id: Optional[UUID] = None
    ):
        """Handle WebSocket connection and messages."""
        try:
            # Connect
            await connection_manager.connect(websocket, tenant_id, user_id)
            
            # Handle messages
            while True:
                try:
                    # Receive message
                    data = await websocket.receive_text()
                    message = json.loads(data)
                    
                    # Handle message type
                    await self._handle_message(websocket, message, tenant_id)
                    
                except WebSocketDisconnect:
                    logger.info("WebSocket disconnected")
                    break
                except json.JSONDecodeError:
                    logger.warning("Invalid JSON received")
                    await self._send_error(websocket, "Invalid JSON format")
                except Exception as e:
                    logger.error(f"Error handling WebSocket message: {e}")
                    await self._send_error(websocket, "Internal server error")
                    
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            connection_manager.disconnect(websocket)
    
    async def _handle_message(self, websocket: WebSocket, message: Dict[str, Any], tenant_id: UUID):
        """Handle different types of WebSocket messages."""
        message_type = message.get("type")
        
        if message_type == "subscribe":
            await self._handle_subscribe(websocket, message)
        elif message_type == "unsubscribe":
            await self._handle_unsubscribe(websocket, message)
        elif message_type == "get_data":
            await self._handle_get_data(websocket, message, tenant_id)
        elif message_type == "heartbeat":
            await self._handle_heartbeat(websocket)
        else:
            await self._send_error(websocket, f"Unknown message type: {message_type}")
    
    async def _handle_subscribe(self, websocket: WebSocket, message: Dict[str, Any]):
        """Handle subscription request."""
        try:
            if websocket in connection_manager.connection_metadata:
                metadata = connection_manager.connection_metadata[websocket]
                subscription_type = message.get("type")
                
                if subscription_type:
                    metadata["subscriptions"].add(subscription_type)
                    
                    # Send confirmation
                    await connection_manager.send_personal_message(websocket, {
                        "type": "subscription_confirmed",
                        "subscription_type": subscription_type,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    
                    logger.info(f"Client subscribed to {subscription_type} for tenant {metadata['tenant_id']}")
                    
        except Exception as e:
            logger.error(f"Error handling subscription: {e}")
    
    async def _handle_unsubscribe(self, websocket: WebSocket, message: Dict[str, Any]):
        """Handle unsubscription request."""
        try:
            if websocket in connection_manager.connection_metadata:
                metadata = connection_manager.connection_metadata[websocket]
                subscription_type = message.get("type")
                
                if subscription_type and subscription_type in metadata.get("subscriptions", set()):
                    metadata["subscriptions"].remove(subscription_type)
                    
                    # Send confirmation
                    await connection_manager.send_personal_message(websocket, {
                        "type": "unsubscription_confirmed",
                        "subscription_type": subscription_type,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    
                    logger.info(f"Client unsubscribed from {subscription_type}")
                    
        except Exception as e:
            logger.error(f"Error handling unsubscription: {e}")
    
    async def _handle_get_data(self, websocket: WebSocket, message: Dict[str, Any], tenant_id: UUID):
        """Handle data request."""
        try:
            data_type = message.get("data_type")
            
            # Get database session
            async with get_async_session() as session:
                if data_type == "overview":
                    data = await data_service.get_dashboard_overview(session, tenant_id)
                elif data_type == "events":
                    limit = message.get("limit", 50)
                    data = await self._get_event_stream_data(session, tenant_id, limit)
                elif data_type == "alerts":
                    data = await self._get_alert_summary(session, tenant_id)
                else:
                    await self._send_error(websocket, f"Unknown data type: {data_type}")
                    return
                
                # Send data response
                await connection_manager.send_personal_message(websocket, {
                    "type": "data_response",
                    "data_type": data_type,
                    "data": data,
                    "timestamp": datetime.utcnow().isoformat()
                })
                
        except Exception as e:
            logger.error(f"Error handling get_data: {e}")
            await self._send_error(websocket, "Failed to retrieve data")
    
    async def _handle_heartbeat(self, websocket: WebSocket):
        """Handle client heartbeat to keep connections alive."""
        try:
            if websocket in connection_manager.connection_metadata:
                metadata = connection_manager.connection_metadata[websocket]
                metadata["last_heartbeat"] = datetime.utcnow()
                
                # Send heartbeat response
                await connection_manager.send_personal_message(websocket, {
                    "type": "heartbeat_response",
                    "timestamp": datetime.utcnow().isoformat()
                })
                
        except Exception as e:
            logger.error(f"Error handling heartbeat: {e}")
    
    async def _get_event_stream_data(
        self, 
        session: AsyncSession, 
        tenant_id: UUID, 
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get recent events for streaming display."""
        try:
            from apps.storage.crud import event_crud
            
            events = await event_crud.get_recent_by_tenant(session, tenant_id, limit)
            
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
                    "payload_summary": self._summarize_payload(event.payload),
                    "severity": self._extract_severity(event.payload)
                })
            
            return stream_data
            
        except Exception as e:
            logger.error(f"Error getting event stream data: {e}")
            return []
    
    async def _get_alert_summary(
        self, 
        session: AsyncSession, 
        tenant_id: UUID
    ) -> Dict[str, Any]:
        """Get alert summary for dashboard."""
        try:
            from apps.storage.crud import alert_crud, alert_rule_crud
            
            # Get active alerts
            active_alerts = await alert_crud.get_active_alerts(session, tenant_id, limit=20)
            
            # Get alert rules
            alert_rules = await alert_rule_crud.get_active_rules(session, tenant_id)
            
            # Count by severity
            severity_counts = {}
            for alert in active_alerts:
                severity = alert.severity
                severity_counts[severity] = severity_counts.get(severity, 0) + 1
            
            # Recent alert activity
            recent_alerts = await alert_crud.get_recent_alerts(session, tenant_id, limit=10)
            
            return {
                "tenant_id": str(tenant_id),
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
            
        except Exception as e:
            logger.error(f"Error getting alert summary: {e}")
            return {}
    
    def _summarize_payload(self, payload: Dict[str, Any]) -> str:
        """Create a summary of the event payload."""
        if not payload:
            return "No payload"
        
        summary_parts = []
        
        if "service" in payload:
            summary_parts.append(f"Service: {payload['service']}")
        if "endpoint" in payload:
            summary_parts.append(f"Endpoint: {payload['endpoint']}")
        if "method" in payload:
            summary_parts.append(f"Method: {payload['method']}")
        
        if summary_parts:
            return " | ".join(summary_parts)
        else:
            return "Payload available"
    
    def _extract_severity(self, payload: Dict[str, Any]) -> str:
        """Extract severity from payload."""
        if not payload:
            return "info"
        
        severity = payload.get("severity", "info")
        if severity in ["error", "critical", "warning", "info", "debug"]:
            return severity
        else:
            return "info"
    
    async def _send_error(self, websocket: WebSocket, error_message: str):
        """Send error message to client."""
        try:
            await connection_manager.send_personal_message(websocket, {
                "type": "error",
                "message": error_message,
                "timestamp": datetime.utcnow().isoformat()
            })
        except Exception as e:
            logger.error(f"Error sending error message: {e}")


# Global instance
websocket_handler = DashboardWebSocketHandler()
