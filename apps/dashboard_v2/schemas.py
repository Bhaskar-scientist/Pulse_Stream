"""Dashboard v2 schemas - Built alongside existing dashboard."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class AlertSummary(BaseModel):
    """Alert summary for dashboard."""
    id: str
    title: str
    severity: str
    status: str
    triggered_at: datetime
    rule_name: Optional[str] = None
    message: Optional[str] = None


class AlertTrends(BaseModel):
    """Alert trends for dashboard."""
    total_alerts: int
    critical_count: int
    warning_count: int
    info_count: int
    alerts_today: int
    alerts_this_week: int
    alerts_this_month: int
    trend_direction: str  # "increasing", "decreasing", "stable"


class AlertSummaryResponse(BaseModel):
    """Response for alert summary API."""
    total_alerts: int
    critical_count: int
    warning_count: int
    info_count: int
    recent_alerts: List[AlertSummary]
    alert_trends: AlertTrends
    last_updated: datetime


class PerformanceMetric(BaseModel):
    """Performance metric for dashboard."""
    metric_name: str
    current_value: float
    previous_value: float
    change_percentage: float
    trend: str  # "up", "down", "stable"
    unit: str
    timestamp: datetime


class SystemHealth(BaseModel):
    """System health status for dashboard."""
    overall_status: str  # "healthy", "warning", "critical"
    services: Dict[str, str]  # service_name: status
    performance_metrics: List[PerformanceMetric]
    last_check: datetime
    uptime_seconds: int


class DashboardOverviewResponse(BaseModel):
    """Response for dashboard overview API."""
    system_health: SystemHealth
    alert_summary: AlertSummaryResponse
    performance_summary: Dict[str, Any]
    last_updated: datetime


class RealTimeMetricsResponse(BaseModel):
    """Response for real-time metrics API."""
    event_volume: Dict[str, int]  # time_period: count
    response_times: Dict[str, float]  # endpoint: avg_response_time
    error_rates: Dict[str, float]  # service: error_percentage
    throughput: Dict[str, int]  # time_period: requests_per_second
    last_updated: datetime


class DashboardConfig(BaseModel):
    """Dashboard configuration."""
    refresh_interval: int = Field(default=30, description="Refresh interval in seconds")
    auto_refresh: bool = Field(default=True, description="Enable auto-refresh")
    theme: str = Field(default="light", description="Dashboard theme")
    layout: Dict[str, Any] = Field(default_factory=dict, description="Widget layout")


class DashboardConfigResponse(BaseModel):
    """Response for dashboard configuration."""
    config: DashboardConfig
    user_preferences: Dict[str, Any]
    last_updated: datetime
