"""Alert management API endpoints for PulseStream."""

from datetime import datetime
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status, Request, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from core.auth import get_current_tenant
from core.database import get_async_session
from core.logging import get_logger
from apps.alerting.services import AlertManagementService, AlertRuleEngine
from apps.alerting.notifications import NotificationService
from apps.storage.models.alert import AlertRule, Alert
from apps.storage.models.tenant import Tenant

logger = get_logger(__name__)

# Create router
router = APIRouter(prefix="/alerting", tags=["Alert Management"])

# Global service instances
notification_service = NotificationService()
rule_engine = AlertRuleEngine(notification_service)
alert_service = AlertManagementService(rule_engine)


@router.post("/rules", response_model=Dict[str, Any])
async def create_alert_rule(
    rule_data: Dict[str, Any],
    current_tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_async_session)
):
    """Create a new alert rule."""
    try:
        # Validate required fields
        required_fields = ["name", "condition", "severity"]
        for field in required_fields:
            if field not in rule_data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Missing required field: {field}"
                )
        
        # Create rule
        rule = await alert_service.create_alert_rule(
            session, rule_data, current_tenant.id
        )
        
        if not rule:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create alert rule"
            )
        
        logger.info(f"Alert rule created: {rule.name} for tenant {current_tenant.id}")
        
        return {
            "success": True,
            "rule_id": str(rule.id),
            "message": "Alert rule created successfully",
            "rule": {
                "id": str(rule.id),
                "name": rule.name,
                "description": rule.description,
                "severity": rule.severity,
                "is_active": rule.is_active
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating alert rule: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create alert rule"
        )


@router.get("/rules", response_model=Dict[str, Any])
async def list_alert_rules(
    current_tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_async_session),
    active_only: bool = Query(True, description="Show only active rules"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of rules"),
    offset: int = Query(0, ge=0, description="Number of rules to skip")
):
    """List alert rules for the current tenant."""
    try:
        from apps.storage.crud import alert_rule_crud
        
        # Get rules
        if active_only:
            rules = await alert_rule_crud.get_active_rules(session, current_tenant.id)
        else:
            rules = await alert_rule_crud.get_by_tenant(session, current_tenant.id, limit, offset)
        
        # Convert to response format
        rule_list = []
        for rule in rules:
            rule_list.append({
                "id": str(rule.id),
                "name": rule.name,
                "description": rule.description,
                "event_type": rule.event_type,
                "severity": rule.severity,
                "is_active": rule.is_active,
                "time_window": rule.time_window,
                "evaluation_interval": rule.evaluation_interval,
                "cooldown_minutes": rule.cooldown_minutes,
                "max_alerts_per_hour": rule.max_alerts_per_hour,
                "last_evaluated_at": rule.last_evaluated_at.isoformat() if rule.last_evaluated_at else None,
                "last_triggered_at": rule.last_triggered_at.isoformat() if rule.last_triggered_at else None,
                "total_triggers": rule.total_triggers,
                "created_at": rule.created_at.isoformat() if rule.created_at else None
            })
        
        return {
            "success": True,
            "rules": rule_list,
            "total_count": len(rule_list),
            "tenant_id": str(current_tenant.id)
        }
        
    except Exception as e:
        logger.error(f"Error listing alert rules: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve alert rules"
        )


@router.get("/rules/{rule_id}", response_model=Dict[str, Any])
async def get_alert_rule(
    rule_id: UUID,
    current_tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_async_session)
):
    """Get a specific alert rule."""
    try:
        from apps.storage.crud import alert_rule_crud
        
        rule = await alert_rule_crud.get_by_id(session, rule_id)
        if not rule or rule.tenant_id != current_tenant.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alert rule not found"
            )
        
        return {
            "success": True,
            "rule": {
                "id": str(rule.id),
                "name": rule.name,
                "description": rule.description,
                "event_type": rule.event_type,
                "condition": rule.condition,
                "threshold_value": rule.threshold_value,
                "threshold_operator": rule.threshold_operator,
                "severity": rule.severity,
                "is_active": rule.is_active,
                "time_window": rule.time_window,
                "evaluation_interval": rule.evaluation_interval,
                "cooldown_minutes": rule.cooldown_minutes,
                "max_alerts_per_hour": rule.max_alerts_per_hour,
                "notification_channels": rule.notification_channels,
                "notification_template": rule.notification_template,
                "last_evaluated_at": rule.last_evaluated_at.isoformat() if rule.last_evaluated_at else None,
                "last_triggered_at": rule.last_triggered_at.isoformat() if rule.last_triggered_at else None,
                "total_triggers": rule.total_triggers,
                "created_at": rule.created_at.isoformat() if rule.created_at else None,
                "updated_at": rule.updated_at.isoformat() if rule.updated_at else None
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting alert rule {rule_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve alert rule"
        )


@router.put("/rules/{rule_id}", response_model=Dict[str, Any])
async def update_alert_rule(
    rule_id: UUID,
    rule_data: Dict[str, Any],
    current_tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_async_session)
):
    """Update an alert rule."""
    try:
        rule = await alert_service.update_alert_rule(
            session, rule_id, rule_data, current_tenant.id
        )
        
        if not rule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alert rule not found"
            )
        
        logger.info(f"Alert rule updated: {rule.name}")
        
        return {
            "success": True,
            "message": "Alert rule updated successfully",
            "rule_id": str(rule.id)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating alert rule {rule_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update alert rule"
        )


@router.delete("/rules/{rule_id}", response_model=Dict[str, Any])
async def delete_alert_rule(
    rule_id: UUID,
    current_tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_async_session)
):
    """Delete an alert rule."""
    try:
        success = await alert_service.delete_alert_rule(
            session, rule_id, current_tenant.id
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alert rule not found"
            )
        
        logger.info(f"Alert rule deleted: {rule_id}")
        
        return {
            "success": True,
            "message": "Alert rule deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting alert rule {rule_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete alert rule"
        )


@router.get("/alerts", response_model=Dict[str, Any])
async def list_alerts(
    current_tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_async_session),
    status_filter: Optional[str] = Query(None, description="Filter by alert status"),
    severity_filter: Optional[str] = Query(None, description="Filter by alert severity"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of alerts"),
    offset: int = Query(0, ge=0, description="Number of alerts to skip")
):
    """List alerts for the current tenant."""
    try:
        from apps.storage.crud import alert_crud
        
        # Get alerts based on filters
        if status_filter:
            alerts = await alert_crud.get_by_status(session, current_tenant.id, status_filter, limit, offset)
        elif severity_filter:
            alerts = await alert_crud.get_by_severity(session, current_tenant.id, severity_filter, limit, offset)
        else:
            alerts = await alert_service.get_active_alerts(session, current_tenant.id, limit)
        
        # Convert to response format
        alert_list = []
        for alert in alerts:
            alert_list.append({
                "id": str(alert.id),
                "title": alert.title,
                "message": alert.message,
                "severity": alert.severity,
                "status": alert.status,
                "triggered_at": alert.triggered_at.isoformat() if alert.triggered_at else None,
                "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
                "duration_minutes": alert.duration_minutes,
                "alert_rule_id": str(alert.alert_rule_id),
                "rule_name": alert.alert_metadata.get("rule_name") if alert.alert_metadata else None,
                "notifications_sent": alert.notifications_sent,
                "notification_failures": alert.notification_failures
            })
        
        return {
            "success": True,
            "alerts": alert_list,
            "total_count": len(alert_list),
            "tenant_id": str(current_tenant.id)
        }
        
    except Exception as e:
        logger.error(f"Error listing alerts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve alerts"
        )


@router.get("/alerts/{alert_id}", response_model=Dict[str, Any])
async def get_alert(
    alert_id: UUID,
    current_tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_async_session)
):
    """Get a specific alert."""
    try:
        from apps.storage.crud import alert_crud
        
        alert = await alert_crud.get_by_id(session, alert_id)
        if not alert or alert.tenant_id != current_tenant.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alert not found"
            )
        
        return {
            "success": True,
            "alert": {
                "id": str(alert.id),
                "title": alert.title,
                "message": alert.message,
                "severity": alert.severity,
                "status": alert.status,
                "triggered_at": alert.triggered_at.isoformat() if alert.triggered_at else None,
                "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
                "duration_minutes": alert.duration_minutes,
                "trigger_data": alert.trigger_data,
                "alert_metadata": alert.alert_metadata,
                "alert_rule_id": str(alert.alert_rule_id),
                "notifications_sent": alert.notifications_sent,
                "notification_failures": alert.notification_failures,
                "resolved_by": alert.resolved_by,
                "resolution_note": alert.resolution_note,
                "created_at": alert.created_at.isoformat() if alert.created_at else None,
                "updated_at": alert.updated_at.isoformat() if alert.updated_at else None
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting alert {alert_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve alert"
        )


@router.post("/alerts/{alert_id}/resolve", response_model=Dict[str, Any])
async def resolve_alert(
    alert_id: UUID,
    resolution_data: Dict[str, Any],
    current_tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_async_session)
):
    """Resolve an alert."""
    try:
        resolved_by = resolution_data.get("resolved_by", "system")
        note = resolution_data.get("note")
        
        alert = await alert_service.resolve_alert(
            session, alert_id, current_tenant.id, resolved_by, note
        )
        
        if not alert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alert not found"
            )
        
        logger.info(f"Alert {alert_id} resolved by {resolved_by}")
        
        return {
            "success": True,
            "message": "Alert resolved successfully",
            "alert_id": str(alert_id),
            "resolved_by": resolved_by,
            "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resolving alert {alert_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resolve alert"
        )


@router.post("/rules/{rule_id}/test", response_model=Dict[str, Any])
async def test_alert_rule(
    rule_id: UUID,
    current_tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_async_session)
):
    """Test an alert rule by evaluating it immediately."""
    try:
        from apps.storage.crud import alert_rule_crud
        
        # Get the rule
        rule = await alert_rule_crud.get_by_id(session, rule_id)
        if not rule or rule.tenant_id != current_tenant.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alert rule not found"
            )
        
        # Test the rule
        alert = await rule_engine.evaluate_rule(session, rule, current_tenant.id)
        
        if alert:
            return {
                "success": True,
                "message": "Alert rule triggered an alert",
                "alert_id": str(alert.id),
                "alert_title": alert.title,
                "triggered_at": alert.triggered_at.isoformat()
            }
        else:
            return {
                "success": True,
                "message": "Alert rule did not trigger (condition not met)",
                "alert_id": None,
                "triggered_at": None
            }
        
    except Exception as e:
        logger.error(f"Error testing alert rule {rule_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to test alert rule"
        )


@router.post("/evaluate", response_model=Dict[str, Any])
async def evaluate_all_rules(
    current_tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_async_session)
):
    """Manually evaluate all active alert rules for the tenant."""
    try:
        # Evaluate all rules
        triggered_alerts = await alert_service.evaluate_all_rules(
            session, current_tenant.id
        )
        
        logger.info(f"Evaluated all rules for tenant {current_tenant.id}: {len(triggered_alerts)} alerts triggered")
        
        return {
            "success": True,
            "message": f"Evaluated all alert rules",
            "total_rules_evaluated": len(triggered_alerts),
            "alerts_triggered": len(triggered_alerts),
            "alerts": [
                {
                    "id": str(alert.id),
                    "title": alert.title,
                    "severity": alert.severity,
                    "triggered_at": alert.triggered_at.isoformat()
                }
                for alert in triggered_alerts
            ]
        }
        
    except Exception as e:
        logger.error(f"Error evaluating all rules: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to evaluate alert rules"
        )


@router.get("/stats", response_model=Dict[str, Any])
async def get_alert_stats(
    current_tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_async_session)
):
    """Get alert statistics for the current tenant."""
    try:
        from apps.storage.crud import alert_crud, alert_rule_crud
        
        # Get counts
        total_alerts = await alert_crud.count_by_tenant(session, current_tenant.id)
        active_alerts = await alert_crud.count_by_status(session, current_tenant.id, "active")
        resolved_alerts = await alert_crud.count_by_status(session, current_tenant.id, "resolved")
        total_rules = await alert_rule_crud.count_by_tenant(session, current_tenant.id)
        active_rules = await alert_rule_crud.count_active_by_tenant(session, current_tenant.id)
        
        # Get recent activity
        recent_alerts = await alert_crud.get_recent_alerts(session, current_tenant.id, limit=5)
        
        return {
            "success": True,
            "stats": {
                "total_alerts": total_alerts,
                "active_alerts": active_alerts,
                "resolved_alerts": resolved_alerts,
                "total_rules": total_rules,
                "active_rules": active_rules,
                "alert_resolution_rate": (resolved_alerts / total_alerts * 100) if total_alerts > 0 else 0
            },
            "recent_alerts": [
                {
                    "id": str(alert.id),
                    "title": alert.title,
                    "severity": alert.severity,
                    "status": alert.status,
                    "triggered_at": alert.triggered_at.isoformat() if alert.triggered_at else None
                }
                for alert in recent_alerts
            ],
            "tenant_id": str(current_tenant.id)
        }
        
    except Exception as e:
        logger.error(f"Error getting alert stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve alert statistics"
        )
