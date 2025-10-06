"""Alert management services for PulseStream."""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload

from core.logging import get_logger
from core.constants import AlertSeverity, AlertStatus, TIME_WINDOWS
from apps.storage.models.alert import AlertRule, Alert
from apps.storage.models.event import Event
from apps.storage.crud import alert_rule_crud, alert_crud
from apps.alerting.notifications import NotificationService

logger = get_logger(__name__)


class AlertRuleEngine:
    """Engine for evaluating alert rules against events."""
    
    def __init__(self, notification_service: NotificationService):
        self.notification_service = notification_service
    
    async def evaluate_rule(
        self, 
        session: AsyncSession, 
        rule: AlertRule, 
        tenant_id: UUID
    ) -> Optional[Alert]:
        """Evaluate a single alert rule against current events."""
        try:
            logger.info(f"Evaluating alert rule: {rule.name} for tenant {tenant_id}")
            
            # Check if rule can trigger
            if not rule.can_trigger_alert(0):  # We'll get actual count below
                logger.debug(f"Rule {rule.name} cannot trigger (inactive/cooldown)")
                return None
            
            # Get recent alerts count for rate limiting
            recent_alerts_count = await self._get_recent_alerts_count(
                session, rule.id, tenant_id
            )
            
            if not rule.can_trigger_alert(recent_alerts_count):
                logger.debug(f"Rule {rule.name} rate limited ({recent_alerts_count} recent alerts)")
                return None
            
            # Evaluate rule condition
            should_trigger, trigger_data = await self._evaluate_condition(
                session, rule, tenant_id
            )
            
            if not should_trigger:
                logger.debug(f"Rule {rule.name} condition not met")
                rule.record_evaluation()
                await session.flush()
                return None
            
            # Create alert
            alert = await self._create_alert(session, rule, trigger_data, tenant_id)
            
            # Record rule trigger
            rule.record_trigger()
            rule.record_evaluation()
            await session.flush()
            
            # Send notifications
            await self._send_notifications(alert, rule)
            
            logger.info(f"Alert rule {rule.name} triggered alert {alert.id}")
            return alert
            
        except Exception as e:
            logger.error(f"Error evaluating rule {rule.name}: {e}")
            return None
    
    async def _evaluate_condition(
        self, 
        session: AsyncSession, 
        rule: AlertRule, 
        tenant_id: UUID
    ) -> Tuple[bool, Dict[str, Any]]:
        """Evaluate the rule condition against current events."""
        try:
            # Parse condition
            condition = rule.condition
            if not condition:
                return False, {}
            
            # Get time window
            time_window_seconds = rule.get_time_window_seconds()
            since_time = datetime.utcnow() - timedelta(seconds=time_window_seconds)
            
            # Build base query
            query = select(Event).where(
                and_(
                    Event.tenant_id == tenant_id,
                    Event.event_timestamp >= since_time,
                    not Event.is_deleted
                )
            )
            
            # Apply event type filter
            if rule.event_type:
                query = query.where(Event.event_type == rule.event_type)
            
            # Execute query
            result = await session.execute(query)
            events = list(result.scalars().all())
            
            # Evaluate condition based on type
            condition_type = condition.get("type", "count")
            
            if condition_type == "count":
                return self._evaluate_count_condition(events, condition, rule)
            elif condition_type == "threshold":
                return self._evaluate_threshold_condition(events, condition, rule)
            elif condition_type == "pattern":
                return self._evaluate_pattern_condition(events, condition, rule)
            else:
                logger.warning(f"Unknown condition type: {condition_type}")
                return False, {}
                
        except Exception as e:
            logger.error(f"Error evaluating condition: {e}")
            return False, {}
    
    def _evaluate_count_condition(
        self, 
        events: List[Event], 
        condition: Dict[str, Any], 
        rule: AlertRule
    ) -> Tuple[bool, Dict[str, Any]]:
        """Evaluate count-based condition."""
        try:
            # Get count criteria
            min_count = condition.get("min_count", 0)
            max_count = condition.get("max_count", float('inf'))
            
            # Count events
            event_count = len(events)
            
            # Check if count is within bounds
            should_trigger = event_count >= min_count and event_count <= max_count
            
            trigger_data = {
                "condition_type": "count",
                "event_count": event_count,
                "min_count": min_count,
                "max_count": max_count,
                "time_window": rule.time_window,
                "events_sample": [
                    {
                        "id": str(event.id),
                        "event_type": event.event_type,
                        "timestamp": event.event_timestamp.isoformat(),
                        "source": event.source
                    }
                    for event in events[:5]  # Sample first 5 events
                ]
            }
            
            return should_trigger, trigger_data
            
        except Exception as e:
            logger.error(f"Error evaluating count condition: {e}")
            return False, {}
    
    def _evaluate_threshold_condition(
        self, 
        events: List[Event], 
        condition: Dict[str, Any], 
        rule: AlertRule
    ) -> Tuple[bool, Dict[str, Any]]:
        """Evaluate threshold-based condition."""
        try:
            if not rule.threshold_value or not rule.threshold_operator:
                return False, {}
            
            # Get threshold criteria
            threshold_value = rule.threshold_value
            operator = rule.threshold_operator
            metric_field = condition.get("metric_field", "status_code")
            
            # Calculate metric value
            metric_value = self._calculate_metric_value(events, metric_field)
            
            # Compare with threshold
            should_trigger = self._compare_values(metric_value, operator, threshold_value)
            
            trigger_data = {
                "condition_type": "threshold",
                "metric_field": metric_field,
                "metric_value": metric_value,
                "threshold_value": threshold_value,
                "operator": operator,
                "time_window": rule.time_window,
                "events_count": len(events)
            }
            
            return should_trigger, trigger_data
            
        except Exception as e:
            logger.error(f"Error evaluating threshold condition: {e}")
            return False, {}
    
    def _evaluate_pattern_condition(
        self, 
        events: List[Event], 
        condition: Dict[str, Any], 
        rule: AlertRule
    ) -> Tuple[bool, Dict[str, Any]]:
        """Evaluate pattern-based condition."""
        try:
            pattern = condition.get("pattern", {})
            pattern_type = pattern.get("type", "error_rate")
            
            if pattern_type == "error_rate":
                return self._evaluate_error_rate_pattern(events, pattern)
            elif pattern_type == "response_time":
                return self._evaluate_response_time_pattern(events, pattern)
            else:
                logger.warning(f"Unknown pattern type: {pattern_type}")
                return False, {}
                
        except Exception as e:
            logger.error(f"Error evaluating pattern condition: {e}")
            return False, {}
    
    def _evaluate_error_rate_pattern(
        self, 
        events: List[Event], 
        pattern: Dict[str, Any]
    ) -> Tuple[bool, Dict[str, Any]]:
        """Evaluate error rate pattern."""
        if not events:
            return False, {}
        
        # Count error events (status code >= 400)
        error_events = [e for e in events if e.status_code and e.status_code >= 400]
        error_rate = len(error_events) / len(events)
        
        # Get threshold
        max_error_rate = pattern.get("max_error_rate", 0.1)  # Default 10%
        
        should_trigger = error_rate > max_error_rate
        
        trigger_data = {
            "condition_type": "pattern",
            "pattern_type": "error_rate",
            "error_rate": error_rate,
            "max_error_rate": max_error_rate,
            "total_events": len(events),
            "error_events": len(error_events)
        }
        
        return should_trigger, trigger_data
    
    def _evaluate_response_time_pattern(
        self, 
        events: List[Event], 
        pattern: Dict[str, Any]
    ) -> Tuple[bool, Dict[str, Any]]:
        """Evaluate response time pattern."""
        if not events:
            return False, {}
        
        # Get response times
        response_times = [e.duration_ms for e in events if e.duration_ms is not None]
        if not response_times:
            return False, {}
        
        # Calculate average response time
        avg_response_time = sum(response_times) / len(response_times)
        
        # Get threshold
        max_avg_response_time = pattern.get("max_avg_response_time", 1000)  # Default 1s
        
        should_trigger = avg_response_time > max_avg_response_time
        
        trigger_data = {
            "condition_type": "pattern",
            "pattern_type": "response_time",
            "avg_response_time": avg_response_time,
            "max_avg_response_time": max_avg_response_time,
            "total_events": len(events),
            "response_time_sample": response_times[:10]  # Sample first 10
        }
        
        return should_trigger, trigger_data
    
    def _calculate_metric_value(self, events: List[Event], metric_field: str) -> float:
        """Calculate metric value from events."""
        if not events:
            return 0.0
        
        if metric_field == "status_code":
            # Return average status code
            status_codes = [e.status_code for e in events if e.status_code is not None]
            return sum(status_codes) / len(status_codes) if status_codes else 0.0
        
        elif metric_field == "duration_ms":
            # Return average response time
            durations = [e.duration_ms for e in events if e.duration_ms is not None]
            return sum(durations) / len(durations) if durations else 0.0
        
        elif metric_field == "count":
            # Return event count
            return len(events)
        
        else:
            logger.warning(f"Unknown metric field: {metric_field}")
            return 0.0
    
    def _compare_values(self, value: float, operator: str, threshold: float) -> bool:
        """Compare value with threshold using operator."""
        if operator == ">":
            return value > threshold
        elif operator == ">=":
            return value >= threshold
        elif operator == "<":
            return value < threshold
        elif operator == "<=":
            return value <= threshold
        elif operator == "==":
            return abs(value - threshold) < 0.001  # Float comparison
        elif operator == "!=":
            return abs(value - threshold) >= 0.001
        else:
            logger.warning(f"Unknown operator: {operator}")
            return False
    
    async def _get_recent_alerts_count(
        self, 
        session: AsyncSession, 
        rule_id: UUID, 
        tenant_id: UUID
    ) -> int:
        """Get count of recent alerts for this rule."""
        try:
            # Count alerts in the last hour
            since_time = datetime.utcnow() - timedelta(hours=1)
            
            query = select(func.count(Alert.id)).where(
                and_(
                    Alert.alert_rule_id == rule_id,
                    Alert.tenant_id == tenant_id,
                    Alert.triggered_at >= since_time
                )
            )
            
            result = await session.execute(query)
            return result.scalar() or 0
            
        except Exception as e:
            logger.error(f"Error getting recent alerts count: {e}")
            return 0
    
    async def _create_alert(
        self, 
        session: AsyncSession, 
        rule: AlertRule, 
        trigger_data: Dict[str, Any], 
        tenant_id: UUID
    ) -> Alert:
        """Create a new alert."""
        try:
            # Generate alert title and message
            title = self._generate_alert_title(rule, trigger_data)
            message = self._generate_alert_message(rule, trigger_data)
            
            # Create alert
            alert = Alert(
                title=title,
                message=message,
                severity=rule.severity,
                status=AlertStatus.ACTIVE,
                triggered_at=datetime.utcnow(),
                trigger_data=trigger_data,
                alert_metadata={
                    "rule_name": rule.name,
                    "rule_description": rule.description,
                    "evaluation_time": datetime.utcnow().isoformat()
                },
                tenant_id=tenant_id,
                alert_rule_id=rule.id
            )
            
            # Save to database
            session.add(alert)
            await session.flush()
            
            logger.info(f"Created alert {alert.id} for rule {rule.name}")
            return alert
            
        except Exception as e:
            logger.error(f"Error creating alert: {e}")
            raise
    
    def _generate_alert_title(self, rule: AlertRule, trigger_data: Dict[str, Any]) -> str:
        """Generate alert title."""
        condition_type = trigger_data.get("condition_type", "unknown")
        
        if condition_type == "count":
            count = trigger_data.get("event_count", 0)
            return f"High Event Count Alert: {count} events in {rule.time_window}"
        
        elif condition_type == "threshold":
            metric = trigger_data.get("metric_field", "unknown")
            value = trigger_data.get("metric_value", 0)
            return f"Threshold Exceeded: {metric} = {value}"
        
        elif condition_type == "pattern":
            pattern_type = trigger_data.get("pattern_type", "unknown")
            if pattern_type == "error_rate":
                rate = trigger_data.get("error_rate", 0)
                return f"High Error Rate: {rate:.1%} in {rule.time_window}"
            elif pattern_type == "response_time":
                time = trigger_data.get("avg_response_time", 0)
                return f"High Response Time: {time:.0f}ms average"
        
        return f"Alert: {rule.name}"
    
    def _generate_alert_message(self, rule: AlertRule, trigger_data: Dict[str, Any]) -> str:
        """Generate alert message."""
        condition_type = trigger_data.get("condition_type", "unknown")
        
        base_message = f"Alert rule '{rule.name}' has been triggered.\n\n"
        
        if condition_type == "count":
            count = trigger_data.get("event_count", 0)
            min_count = trigger_data.get("min_count", 0)
            max_count = trigger_data.get("max_count", "unlimited")
            base_message += f"Event count: {count}\n"
            base_message += f"Threshold: {min_count} - {max_count}\n"
            base_message += f"Time window: {rule.time_window}"
        
        elif condition_type == "threshold":
            metric = trigger_data.get("metric_field", "unknown")
            value = trigger_data.get("metric_value", 0)
            threshold = trigger_data.get("threshold_value", 0)
            operator = trigger_data.get("operator", "unknown")
            base_message += f"Metric: {metric}\n"
            base_message += f"Current value: {value}\n"
            base_message += f"Threshold: {operator} {threshold}"
        
        elif condition_type == "pattern":
            pattern_type = trigger_data.get("pattern_type", "unknown")
            if pattern_type == "error_rate":
                rate = trigger_data.get("error_rate", 0)
                max_rate = trigger_data.get("max_error_rate", 0)
                base_message += f"Error rate: {rate:.1%}\n"
                base_message += f"Maximum allowed: {max_rate:.1%}"
            elif pattern_type == "response_time":
                time = trigger_data.get("avg_response_time", 0)
                max_time = trigger_data.get("max_avg_response_time", 0)
                base_message += f"Average response time: {time:.0f}ms\n"
                base_message += f"Maximum allowed: {max_time:.0f}ms"
        
        if rule.description:
            base_message += f"\n\nRule description: {rule.description}"
        
        return base_message
    
    async def _send_notifications(self, alert: Alert, rule: AlertRule) -> None:
        """Send notifications for the alert."""
        try:
            await self.notification_service.send_alert_notifications(alert, rule)
        except Exception as e:
            logger.error(f"Error sending notifications for alert {alert.id}: {e}")


class AlertManagementService:
    """Service for managing alerts and alert rules."""
    
    def __init__(self, rule_engine: AlertRuleEngine):
        self.rule_engine = rule_engine
    
    async def evaluate_all_rules(
        self, 
        session: AsyncSession, 
        tenant_id: UUID
    ) -> List[Alert]:
        """Evaluate all active alert rules for a tenant."""
        try:
            # Get active rules
            rules = await alert_rule_crud.get_active_rules(session, tenant_id)
            
            logger.info(f"Evaluating {len(rules)} active rules for tenant {tenant_id}")
            
            # Evaluate each rule
            triggered_alerts = []
            for rule in rules:
                try:
                    alert = await self.rule_engine.evaluate_rule(session, rule, tenant_id)
                    if alert:
                        triggered_alerts.append(alert)
                except Exception as e:
                    logger.error(f"Error evaluating rule {rule.name}: {e}")
                    continue
            
            logger.info(f"Triggered {len(triggered_alerts)} alerts for tenant {tenant_id}")
            return triggered_alerts
            
        except Exception as e:
            logger.error(f"Error evaluating all rules: {e}")
            return []
    
    async def get_active_alerts(
        self, 
        session: AsyncSession, 
        tenant_id: UUID,
        limit: int = 100
    ) -> List[Alert]:
        """Get active alerts for a tenant."""
        try:
            return await alert_crud.get_active_alerts(session, tenant_id, limit)
        except Exception as e:
            logger.error(f"Error getting active alerts: {e}")
            return []
    
    async def resolve_alert(
        self, 
        session: AsyncSession, 
        alert_id: UUID, 
        tenant_id: UUID,
        resolved_by: str = "system",
        note: Optional[str] = None
    ) -> Optional[Alert]:
        """Resolve an alert."""
        try:
            alert = await alert_crud.get_by_id(session, alert_id)
            if not alert or alert.tenant_id != tenant_id:
                return None
            
            alert.resolve(resolved_by, note)
            await session.flush()
            
            logger.info(f"Alert {alert_id} resolved by {resolved_by}")
            return alert
            
        except Exception as e:
            logger.error(f"Error resolving alert {alert_id}: {e}")
            return None
    
    async def create_alert_rule(
        self, 
        session: AsyncSession, 
        rule_data: Dict[str, Any], 
        tenant_id: UUID
    ) -> Optional[AlertRule]:
        """Create a new alert rule."""
        try:
            rule = AlertRule(
                tenant_id=tenant_id,
                **rule_data
            )
            
            session.add(rule)
            await session.flush()
            
            logger.info(f"Created alert rule {rule.id}: {rule.name}")
            return rule
            
        except Exception as e:
            logger.error(f"Error creating alert rule: {e}")
            return None
    
    async def update_alert_rule(
        self, 
        session: AsyncSession, 
        rule_id: UUID, 
        rule_data: Dict[str, Any], 
        tenant_id: UUID
    ) -> Optional[AlertRule]:
        """Update an alert rule."""
        try:
            rule = await alert_rule_crud.get_by_id(session, rule_id)
            if not rule or rule.tenant_id != tenant_id:
                return None
            
            # Update fields
            for key, value in rule_data.items():
                if hasattr(rule, key):
                    setattr(rule, key, value)
            
            await session.flush()
            
            logger.info(f"Updated alert rule {rule_id}")
            return rule
            
        except Exception as e:
            logger.error(f"Error updating alert rule {rule_id}: {e}")
            return None
    
    async def delete_alert_rule(
        self, 
        session: AsyncSession, 
        rule_id: UUID, 
        tenant_id: UUID
    ) -> bool:
        """Delete an alert rule."""
        try:
            rule = await alert_rule_crud.get_by_id(session, rule_id)
            if not rule or rule.tenant_id != tenant_id:
                return False
            
            # Soft delete
            rule.is_deleted = True
            await session.flush()
            
            logger.info(f"Deleted alert rule {rule_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting alert rule {rule_id}: {e}")
            return False
