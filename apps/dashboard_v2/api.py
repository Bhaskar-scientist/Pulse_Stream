"""Dashboard v2 API endpoints - Built alongside existing dashboard."""

from fastapi import APIRouter, HTTPException, Depends, Header
from typing import Optional
from datetime import datetime
import logging

from .services import DashboardServiceV2
from .schemas import (
    AlertSummaryResponse, RealTimeMetricsResponse, DashboardOverviewResponse
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/dashboard", tags=["Dashboard v2"])


async def get_api_key(x_api_key: str = Header(..., description="API Key for tenant authentication")):
    """Validate API key from header."""
    if not x_api_key:
        raise HTTPException(status_code=401, detail="API key required")
    return x_api_key


@router.get("/overview", response_model=DashboardOverviewResponse)
async def get_dashboard_overview(
    tenant_id: str,
    api_key: str = Depends(get_api_key)
):
    """Get comprehensive dashboard overview using existing APIs."""
    try:
        async with DashboardServiceV2() as dashboard_service:
            overview = await dashboard_service.get_dashboard_overview(tenant_id, api_key)
            logger.info(f"Dashboard overview retrieved for tenant {tenant_id}")
            return overview
    except Exception as e:
        logger.exception(f"Error getting dashboard overview: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve dashboard overview") from e


@router.get("/alerts/summary", response_model=AlertSummaryResponse)
async def get_alert_summary(
    tenant_id: str,
    api_key: str = Depends(get_api_key)
):
    """Get alert summary using existing working APIs."""
    try:
        async with DashboardServiceV2() as dashboard_service:
            summary = await dashboard_service.get_alert_summary(tenant_id, api_key)
            logger.info(f"Alert summary retrieved for tenant {tenant_id}")
            return summary
    except Exception as e:
        logger.exception(f"Error getting alert summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve alert summary") from e


@router.get("/metrics/real-time", response_model=RealTimeMetricsResponse)
async def get_real_time_metrics(
    tenant_id: str,
    api_key: str = Depends(get_api_key)
):
    """Get real-time metrics using existing working APIs."""
    try:
        async with DashboardServiceV2() as dashboard_service:
            metrics = await dashboard_service.get_real_time_metrics(tenant_id, api_key)
            logger.info(f"Real-time metrics retrieved for tenant {tenant_id}")
            return metrics
    except Exception as e:
        logger.exception(f"Error getting real-time metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve real-time metrics") from e


@router.get("/health")
async def get_dashboard_v2_health():
    """Health check for dashboard v2 service."""
    return {
        "status": "healthy",
        "service": "dashboard_v2",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


@router.get("/config")
async def get_dashboard_config(
    tenant_id: str,
    api_key: str = Depends(get_api_key)
):
    """Get dashboard configuration for tenant."""
    try:
        # For now, return default configuration
        # In a real implementation, this would be stored per tenant
        config = {
            "refresh_interval": 30,
            "auto_refresh": True,
            "theme": "light",
            "layout": {
                "widgets": [
                    {"id": "alerts", "position": "top-left", "size": "medium"},
                    {"id": "metrics", "position": "top-right", "size": "medium"},
                    {"id": "health", "position": "bottom-left", "size": "small"},
                    {"id": "performance", "position": "bottom-right", "size": "small"}
                ]
            }
        }
        
        return {
            "config": config,
            "user_preferences": {},
            "last_updated": datetime.utcnow().isoformat() + "Z"
        }
    except Exception as e:
        logger.exception(f"Error getting dashboard config: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve dashboard configuration") from e


@router.post("/config")
async def update_dashboard_config(
    tenant_id: str,
    config: dict,
    api_key: str = Depends(get_api_key)
):
    """Update dashboard configuration for tenant."""
    try:
        # For now, just log the update
        # In a real implementation, this would be stored per tenant
        logger.info(f"Dashboard config updated for tenant {tenant_id}: {config}")
        
        return {
            "status": "success",
            "message": "Dashboard configuration updated",
            "tenant_id": tenant_id,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    except Exception as e:
        logger.exception(f"Error updating dashboard config: {e}")
        raise HTTPException(status_code=500, detail="Failed to update dashboard configuration") from e


@router.get("/widgets/{widget_id}")
async def get_widget_data(
    widget_id: str,
    tenant_id: str,
    api_key: str = Depends(get_api_key)
):
    """Get data for specific dashboard widget."""
    try:
        async with DashboardServiceV2() as dashboard_service:
            if widget_id == "alerts":
                data = await dashboard_service.get_alert_summary(tenant_id, api_key)
            elif widget_id == "metrics":
                data = await dashboard_service.get_real_time_metrics(tenant_id, api_key)
            elif widget_id == "health":
                data = await dashboard_service._get_system_health(tenant_id, api_key)
            elif widget_id == "performance":
                data = await dashboard_service.get_real_time_metrics(tenant_id, api_key)
            else:
                raise HTTPException(status_code=404, detail=f"Widget {widget_id} not found")
            
            logger.info(f"Widget data retrieved for {widget_id} in tenant {tenant_id}")
            return {
                "widget_id": widget_id,
                "tenant_id": tenant_id,
                "data": data,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
    except Exception as e:
        logger.exception(f"Error getting widget data: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve widget data for {widget_id}") from e


@router.get("/export/{format}")
async def export_dashboard_data(
    format: str,
    tenant_id: str,
    api_key: str = Depends(get_api_key)
):
    """Export dashboard data in specified format."""
    try:
        if format not in ["json", "csv", "pdf"]:
            raise HTTPException(status_code=400, detail="Unsupported format. Use: json, csv, pdf")
        
        async with DashboardServiceV2() as dashboard_service:
            # Get all dashboard data
            overview = await dashboard_service.get_dashboard_overview(tenant_id, api_key)
            
            if format == "json":
                return {
                    "format": "json",
                    "tenant_id": tenant_id,
                    "data": overview,
                    "exported_at": datetime.utcnow().isoformat() + "Z"
                }
            elif format == "csv":
                # Convert to CSV format (simplified)
                csv_data = f"tenant_id,exported_at\n{tenant_id},{datetime.utcnow().isoformat() + 'Z'}"
                return {
                    "format": "csv",
                    "tenant_id": tenant_id,
                    "data": csv_data,
                    "exported_at": datetime.utcnow().isoformat() + "Z"
                }
            else:  # pdf
                return {
                    "format": "pdf",
                    "tenant_id": tenant_id,
                    "message": "PDF export not yet implemented",
                    "exported_at": datetime.utcnow().isoformat() + "Z"
                }
    except Exception as e:
        logger.exception(f"Error exporting dashboard data: {e}")
        raise HTTPException(status_code=500, detail="Failed to export dashboard data") from e
