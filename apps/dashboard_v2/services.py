"""Dashboard v2 service - Built alongside existing dashboard using working APIs."""

import asyncio
import httpx
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import logging

from .schemas import (
    AlertSummaryResponse, RealTimeMetricsResponse, DashboardOverviewResponse,
    SystemHealth, AlertSummary, AlertTrends, PerformanceMetric
)

logger = logging.getLogger(__name__)


class DashboardServiceV2:
    """Dashboard service v2 - Uses existing working APIs for data."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.http_client = httpx.AsyncClient(timeout=30.0)
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.http_client.aclose()
    
    async def get_alert_summary(self, tenant_id: str, api_key: str) -> AlertSummaryResponse:
        """Get alert summary using existing working APIs."""
        try:
            # Use existing working APIs to get data
            headers = {"X-API-Key": api_key}
            
            # Get recent events to analyze for alerts
            events_response = await self.http_client.get(
                f"{self.base_url}/api/v1/ingestion/events/search",
                headers=headers,
                params={"tenant_id": tenant_id, "limit": 100}
            )
            
            if events_response.status_code != 200:
                logger.error(f"Failed to get events: {events_response.status_code}")
                raise Exception("Failed to retrieve event data")
            
            events_data = events_response.json()
            events = events_data.get("events", [])
            
            # Analyze events to create alert summary
            alert_summary = await self._analyze_events_for_alerts(events)
            
            return alert_summary
            
        except Exception as e:
            logger.error(f"Error getting alert summary: {e}")
            # Return empty summary instead of failing
            return await self._get_empty_alert_summary()
    
    async def get_real_time_metrics(self, tenant_id: str, api_key: str) -> RealTimeMetricsResponse:
        """Get real-time metrics using existing working APIs."""
        try:
            headers = {"X-API-Key": api_key}
            
            # Get event statistics from working API
            stats_response = await self.http_client.get(
                f"{self.base_url}/api/v1/ingestion/events/statistics",
                headers=headers,
                params={"tenant_id": tenant_id}
            )
            
            if stats_response.status_code != 200:
                logger.error(f"Failed to get event statistics: {stats_response.status_code}")
                raise Exception("Failed to retrieve event statistics")
            
            stats_data = stats_response.json()
            
            # Transform existing data into new format
            metrics = await self._transform_stats_to_metrics(stats_data)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error getting real-time metrics: {e}")
            # Return empty metrics instead of failing
            return await self._get_empty_real_time_metrics()
    
    async def get_dashboard_overview(self, tenant_id: str, api_key: str) -> DashboardOverviewResponse:
        """Get comprehensive dashboard overview using existing APIs."""
        try:
            # Get data from multiple working APIs
            alert_summary = await self.get_alert_summary(tenant_id, api_key)
            real_time_metrics = await self.get_real_time_metrics(tenant_id, api_key)
            system_health = await self._get_system_health(tenant_id, api_key)
            
            # Combine into overview response
            overview = DashboardOverviewResponse(
                system_health=system_health,
                alert_summary=alert_summary,
                performance_summary={
                    "total_events": real_time_metrics.event_volume.get("total", 0),
                    "avg_response_time": self._calculate_avg_response_time(real_time_metrics.response_times),
                    "error_rate": self._calculate_overall_error_rate(real_time_metrics.error_rates)
                },
                last_updated=datetime.utcnow()
            )
            
            return overview
            
        except Exception as e:
            logger.error(f"Error getting dashboard overview: {e}")
            # Return minimal overview instead of failing
            return await self._get_empty_dashboard_overview()
    
    async def _analyze_events_for_alerts(self, events: List[Dict[str, Any]]) -> AlertSummaryResponse:
        """Analyze events to create alert summary."""
        try:
            # Count events by status code to identify potential issues
            status_counts = {}
            error_events = []
            
            for event in events:
                status = event.get("status_code", 200)
                status_counts[status] = status_counts.get(status, 0) + 1
                
                # Consider 4xx and 5xx as potential alerts
                if status >= 400:
                    error_events.append(event)
            
            # Create alert summary from event analysis
            total_alerts = len(error_events)
            critical_count = len([e for e in error_events if e.get("status_code", 200) >= 500])
            warning_count = len([e for e in error_events if 400 <= e.get("status_code", 200) < 500])
            info_count = total_alerts - critical_count - warning_count
            
            # Create recent alerts from error events
            recent_alerts = []
            for event in error_events[:10]:  # Top 10 errors
                alert = AlertSummary(
                    id=str(event.get("id", "unknown")),
                    title=f"HTTP {event.get('status_code', 'Unknown')} Error",
                    severity="critical" if event.get("status_code", 200) >= 500 else "warning",
                    status="active",
                    triggered_at=datetime.fromisoformat(event.get("timestamp", datetime.utcnow().isoformat())),
                    message=f"Error occurred in {event.get('source', 'unknown service')}",
                    rule_name="Event Analysis"
                )
                recent_alerts.append(alert)
            
            # Create alert trends
            trends = AlertTrends(
                total_alerts=total_alerts,
                critical_count=critical_count,
                warning_count=warning_count,
                info_count=info_count,
                alerts_today=total_alerts,  # Simplified for now
                alerts_this_week=total_alerts,
                alerts_this_month=total_alerts,
                trend_direction="stable" if total_alerts == 0 else "increasing"
            )
            
            return AlertSummaryResponse(
                total_alerts=total_alerts,
                critical_count=critical_count,
                warning_count=warning_count,
                info_count=info_count,
                recent_alerts=recent_alerts,
                alert_trends=trends,
                last_updated=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"Error analyzing events for alerts: {e}")
            return await self._get_empty_alert_summary()
    
    async def _transform_stats_to_metrics(self, stats_data: Dict[str, Any]) -> RealTimeMetricsResponse:
        """Transform existing event statistics to new metrics format."""
        try:
            # Extract data from existing statistics
            events = stats_data.get("events", [])
            
            # Calculate event volume by time periods
            now = datetime.utcnow()
            event_volume = {
                "total": len(events),
                "last_hour": len([e for e in events if self._is_within_hours(e, 1)]),
                "last_24h": len([e for e in events if self._is_within_hours(e, 24)]),
                "last_7d": len([e for e in events if self._is_within_hours(e, 24*7)])
            }
            
            # Calculate response times by endpoint
            response_times = {}
            for event in events:
                source = event.get("source", "unknown")
                duration = event.get("duration_ms", 0)
                if source not in response_times:
                    response_times[source] = []
                response_times[source].append(duration)
            
            # Calculate averages
            avg_response_times = {}
            for source, times in response_times.items():
                if times:
                    avg_response_times[source] = sum(times) / len(times)
            
            # Calculate error rates by service
            error_rates = {}
            for event in events:
                source = event.get("source", "unknown")
                status = event.get("status_code", 200)
                is_error = status >= 400
                
                if source not in error_rates:
                    error_rates[source] = {"total": 0, "errors": 0}
                
                error_rates[source]["total"] += 1
                if is_error:
                    error_rates[source]["errors"] += 1
            
            # Convert to percentages
            final_error_rates = {}
            for source, counts in error_rates.items():
                if counts["total"] > 0:
                    final_error_rates[source] = (counts["errors"] / counts["total"]) * 100
                else:
                    final_error_rates[source] = 0.0
            
            # Calculate throughput
            throughput = {
                "current": event_volume["last_hour"],
                "last_hour": event_volume["last_hour"],
                "daily_avg": event_volume["last_24h"]
            }
            
            return RealTimeMetricsResponse(
                event_volume=event_volume,
                response_times=avg_response_times,
                error_rates=final_error_rates,
                throughput=throughput,
                last_updated=now
            )
            
        except Exception as e:
            logger.error(f"Error transforming stats to metrics: {e}")
            return await self._get_empty_real_time_metrics()
    
    async def _get_system_health(self, tenant_id: str, api_key: str) -> SystemHealth:
        """Get system health status."""
        try:
            headers = {"X-API-Key": api_key}
            
            # Check health of existing APIs
            health_checks = {}
            
            # Check auth health
            try:
                auth_response = await self.http_client.get(
                    f"{self.base_url}/api/v1/auth/health",
                    headers=headers
                )
                health_checks["authentication"] = "healthy" if auth_response.status_code == 200 else "unhealthy"
            except:
                health_checks["authentication"] = "unhealthy"
            
            # Check ingestion health
            try:
                ingestion_response = await self.http_client.get(
                    f"{self.base_url}/api/v1/ingestion/health",
                    headers=headers
                )
                health_checks["event_ingestion"] = "healthy" if ingestion_response.status_code == 200 else "unhealthy"
            except:
                health_checks["event_ingestion"] = "unhealthy"
            
            # Check storage health
            try:
                storage_response = await self.http_client.get(
                    f"{self.base_url}/api/v1/storage/health",
                    headers=headers
                )
                health_checks["storage"] = "healthy" if storage_response.status_code == 200 else "unhealthy"
            except:
                health_checks["storage"] = "unhealthy"
            
            # Determine overall status
            unhealthy_count = sum(1 for status in health_checks.values() if status == "unhealthy")
            if unhealthy_count == 0:
                overall_status = "healthy"
            elif unhealthy_count <= 1:
                overall_status = "warning"
            else:
                overall_status = "critical"
            
            # Create performance metrics
            performance_metrics = [
                PerformanceMetric(
                    metric_name="API Response Time",
                    current_value=0.1,  # Placeholder
                    previous_value=0.1,
                    change_percentage=0.0,
                    trend="stable",
                    unit="seconds",
                    timestamp=datetime.utcnow()
                )
            ]
            
            return SystemHealth(
                overall_status=overall_status,
                services=health_checks,
                performance_metrics=performance_metrics,
                last_check=datetime.utcnow(),
                uptime_seconds=3600  # Placeholder
            )
            
        except Exception as e:
            logger.error(f"Error getting system health: {e}")
            # Return minimal health status
            return SystemHealth(
                overall_status="unknown",
                services={},
                performance_metrics=[],
                last_check=datetime.utcnow(),
                uptime_seconds=0
            )
    
    def _is_within_hours(self, event: Dict[str, Any], hours: int) -> bool:
        """Check if event is within specified hours."""
        try:
            event_time = datetime.fromisoformat(event.get("timestamp", datetime.utcnow().isoformat()))
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            return event_time >= cutoff_time
        except:
            return False
    
    def _calculate_avg_response_time(self, response_times: Dict[str, float]) -> float:
        """Calculate average response time across all endpoints."""
        if not response_times:
            return 0.0
        return sum(response_times.values()) / len(response_times)
    
    def _calculate_overall_error_rate(self, error_rates: Dict[str, float]) -> float:
        """Calculate overall error rate across all services."""
        if not error_rates:
            return 0.0
        return sum(error_rates.values()) / len(error_rates)
    
    async def _get_empty_alert_summary(self) -> AlertSummaryResponse:
        """Get empty alert summary for fallback."""
        empty_trends = AlertTrends(
            total_alerts=0,
            critical_count=0,
            warning_count=0,
            info_count=0,
            alerts_today=0,
            alerts_this_week=0,
            alerts_this_month=0,
            trend_direction="stable"
        )
        
        return AlertSummaryResponse(
            total_alerts=0,
            critical_count=0,
            warning_count=0,
            info_count=0,
            recent_alerts=[],
            alert_trends=empty_trends,
            last_updated=datetime.utcnow()
        )
    
    async def _get_empty_real_time_metrics(self) -> RealTimeMetricsResponse:
        """Get empty real-time metrics for fallback."""
        return RealTimeMetricsResponse(
            event_volume={},
            response_times={},
            error_rates={},
            throughput={},
            last_updated=datetime.utcnow()
        )
    
    async def _get_empty_dashboard_overview(self) -> DashboardOverviewResponse:
        """Get empty dashboard overview for fallback."""
        empty_health = SystemHealth(
            overall_status="unknown",
            services={},
            performance_metrics=[],
            last_check=datetime.utcnow(),
            uptime_seconds=0
        )
        
        empty_alerts = await self._get_empty_alert_summary()
        empty_metrics = await self._get_empty_real_time_metrics()
        
        return DashboardOverviewResponse(
            system_health=empty_health,
            alert_summary=empty_alerts,
            performance_summary={},
            last_updated=datetime.utcnow()
        )
