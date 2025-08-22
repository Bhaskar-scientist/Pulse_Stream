"""Alert models for rule-based alerting system."""

from typing import Any, Dict, List, Optional

from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from core.database import Base, TenantMixin
from core.constants import AlertSeverity, AlertStatus, NotificationChannel, TIME_WINDOWS


class AlertRule(Base, TenantMixin):
    """Alert rule model for defining alerting conditions."""
    
    __tablename__ = "alert_rules"
    
    # Rule Information
    name = Column(
        String(255),
        nullable=False,
        doc="Human-readable alert rule name"
    )
    
    description = Column(
        Text,
        nullable=True,
        doc="Detailed description of what this rule monitors"
    )
    
    # Rule Configuration
    event_type = Column(
        String(50),
        nullable=True,
        index=True,
        doc="Event type to monitor (null = all types)"
    )
    
    condition = Column(
        JSONB,
        nullable=False,
        doc="JSON condition definition for rule evaluation"
    )
    
    # Threshold Configuration
    threshold_value = Column(
        Float,
        nullable=True,
        doc="Numerical threshold for comparison"
    )
    
    threshold_operator = Column(
        String(10),
        nullable=True,
        doc="Comparison operator (>, <, >=, <=, ==, !=)"
    )
    
    # Time Window Configuration
    time_window = Column(
        String(10),
        nullable=False,
        default="5m",
        doc="Time window for evaluation (1m, 5m, 15m, 1h, etc.)"
    )
    
    evaluation_interval = Column(
        Integer,
        nullable=False,
        default=60,
        doc="How often to evaluate this rule (seconds)"
    )
    
    # Alert Configuration
    severity = Column(
        String(20),
        nullable=False,
        default=AlertSeverity.MEDIUM,
        doc="Alert severity level"
    )
    
    # Notification Configuration
    notification_channels = Column(
        JSONB,
        nullable=True,
        doc="JSON array of notification channels (email, slack, etc.)"
    )
    
    notification_template = Column(
        Text,
        nullable=True,
        doc="Custom notification message template"
    )
    
    # Rule State
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        doc="Whether this rule is active"
    )
    
    # Cooldown and Rate Limiting
    cooldown_minutes = Column(
        Integer,
        default=5,
        nullable=False,
        doc="Minimum time between alerts for this rule"
    )
    
    max_alerts_per_hour = Column(
        Integer,
        default=10,
        nullable=False,
        doc="Maximum alerts per hour for this rule"
    )
    
    # Tracking
    last_evaluated_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="When this rule was last evaluated"
    )
    
    last_triggered_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="When this rule last triggered an alert"
    )
    
    total_triggers = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Total number of times this rule has triggered"
    )
    
    # Relationships
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Tenant this rule belongs to"
    )
    
    tenant = relationship(
        "Tenant",
        back_populates="alert_rules",
        lazy="select"
    )
    
    alerts = relationship(
        "Alert",
        back_populates="alert_rule",
        lazy="select",
        order_by="Alert.created_at.desc()"
    )
    
    # Database optimizations
    __table_args__ = (
        Index('idx_alert_rules_tenant_active', 'tenant_id', 'is_active'),
        Index('idx_alert_rules_evaluation', 'is_active', 'last_evaluated_at'),
        Index('idx_alert_rules_event_type', 'tenant_id', 'event_type'),
    )
    
    def get_time_window_seconds(self) -> int:
        """Get time window in seconds."""
        return TIME_WINDOWS.get(self.time_window, 300)  # Default 5 minutes
    
    def is_in_cooldown(self) -> bool:
        """Check if rule is in cooldown period."""
        if not self.last_triggered_at:
            return False
        
        cooldown_end = self.last_triggered_at + func.interval(f'{self.cooldown_minutes} minutes')
        return func.now() < cooldown_end
    
    def can_trigger_alert(self, recent_alerts_count: int) -> bool:
        """Check if rule can trigger an alert."""
        if not self.is_active:
            return False
        
        if self.is_in_cooldown():
            return False
        
        if recent_alerts_count >= self.max_alerts_per_hour:
            return False
        
        return True
    
    def get_notification_channels(self) -> List[str]:
        """Get list of notification channels."""
        if not self.notification_channels:
            return ["email"]  # Default to email
        
        if isinstance(self.notification_channels, list):
            return self.notification_channels
        
        return list(self.notification_channels.keys()) if isinstance(self.notification_channels, dict) else []
    
    def get_channel_config(self, channel: str) -> Dict[str, Any]:
        """Get configuration for a specific notification channel."""
        if not self.notification_channels:
            return {}
        
        if isinstance(self.notification_channels, dict):
            return self.notification_channels.get(channel, {})
        
        return {}
    
    def record_trigger(self) -> None:
        """Record that this rule triggered an alert."""
        self.last_triggered_at = func.now()
        self.total_triggers += 1
    
    def record_evaluation(self) -> None:
        """Record that this rule was evaluated."""
        self.last_evaluated_at = func.now()
    
    def __str__(self) -> str:
        """String representation."""
        return f"AlertRule({self.name})"
    
    def __repr__(self) -> str:
        """Detailed representation."""
        return (
            f"<AlertRule(id={self.id}, name='{self.name}', "
            f"severity='{self.severity}', active={self.is_active})>"
        )


class Alert(Base, TenantMixin):
    """Alert model for storing triggered alerts."""
    
    __tablename__ = "alerts"
    
    # Alert Information
    title = Column(
        String(255),
        nullable=False,
        doc="Alert title/summary"
    )
    
    message = Column(
        Text,
        nullable=False,
        doc="Detailed alert message"
    )
    
    severity = Column(
        String(20),
        nullable=False,
        index=True,
        doc="Alert severity level"
    )
    
    # Alert Status
    status = Column(
        String(20),
        nullable=False,
        default=AlertStatus.ACTIVE,
        index=True,
        doc="Alert status (active, resolved, suppressed)"
    )
    
    # Timing
    triggered_at = Column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        doc="When the alert was triggered"
    )
    
    resolved_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="When the alert was resolved"
    )
    
    # Context Data
    trigger_data = Column(
        JSONB,
        nullable=True,
        doc="Data that triggered the alert (metrics, events, etc.)"
    )
    
    alert_metadata = Column(
        JSONB,
        nullable=True,
        doc="Additional alert metadata"
    )
    
    # Related Event
    event_id = Column(
        UUID(as_uuid=True),
        ForeignKey("events.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Event that triggered this alert (if applicable)"
    )
    
    # Notification Tracking
    notifications_sent = Column(
        JSONB,
        nullable=True,
        doc="Record of notifications sent for this alert"
    )
    
    notification_failures = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Number of failed notification attempts"
    )
    
    # Resolution Information
    resolved_by = Column(
        String(255),
        nullable=True,
        doc="Who or what resolved this alert"
    )
    
    resolution_note = Column(
        Text,
        nullable=True,
        doc="Note about how alert was resolved"
    )
    
    # Relationships
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Tenant this alert belongs to"
    )
    
    alert_rule_id = Column(
        UUID(as_uuid=True),
        ForeignKey("alert_rules.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Alert rule that triggered this alert"
    )
    
    tenant = relationship(
        "Tenant",
        back_populates="alerts",
        lazy="select"
    )
    
    alert_rule = relationship(
        "AlertRule",
        back_populates="alerts",
        lazy="select"
    )
    
    event = relationship(
        "Event",
        lazy="select"
    )
    
    # Database optimizations
    __table_args__ = (
        Index('idx_alerts_tenant_status', 'tenant_id', 'status'),
        Index('idx_alerts_tenant_severity', 'tenant_id', 'severity'),
        Index('idx_alerts_triggered_at', 'tenant_id', 'triggered_at'),
        Index('idx_alerts_rule_status', 'alert_rule_id', 'status'),
    )
    
    @property
    def is_active(self) -> bool:
        """Check if alert is currently active."""
        return self.status == AlertStatus.ACTIVE
    
    @property
    def is_resolved(self) -> bool:
        """Check if alert is resolved."""
        return self.status == AlertStatus.RESOLVED
    
    @property
    def duration_minutes(self) -> Optional[int]:
        """Get alert duration in minutes."""
        if not self.resolved_at:
            # Calculate time since triggered
            return int((func.now() - self.triggered_at).total_seconds() / 60)
        
        return int((self.resolved_at - self.triggered_at).total_seconds() / 60)
    
    def resolve(self, resolved_by: str = "system", note: Optional[str] = None) -> None:
        """Resolve the alert."""
        self.status = AlertStatus.RESOLVED
        self.resolved_at = func.now()
        self.resolved_by = resolved_by
        if note:
            self.resolution_note = note
    
    def suppress(self) -> None:
        """Suppress the alert."""
        self.status = AlertStatus.SUPPRESSED
    
    def reactivate(self) -> None:
        """Reactivate a suppressed alert."""
        self.status = AlertStatus.ACTIVE
        self.resolved_at = None
        self.resolved_by = None
        self.resolution_note = None
    
    def record_notification_sent(self, channel: str, success: bool, details: Optional[Dict] = None) -> None:
        """Record a notification attempt."""
        if not self.notifications_sent:
            self.notifications_sent = {}
        
        if channel not in self.notifications_sent:
            self.notifications_sent[channel] = []
        
        notification_record = {
            'timestamp': func.now().isoformat(),
            'success': success,
            'details': details or {}
        }
        
        self.notifications_sent[channel].append(notification_record)
        
        if not success:
            self.notification_failures += 1
    
    def get_trigger_value(self, key: str, default: Any = None) -> Any:
        """Get a value from trigger data."""
        if not self.trigger_data:
            return default
        return self.trigger_data.get(key, default)
    
    def set_trigger_value(self, key: str, value: Any) -> None:
        """Set a value in trigger data."""
        if not self.trigger_data:
            self.trigger_data = {}
        self.trigger_data[key] = value
    
    def to_dict_summary(self) -> Dict[str, Any]:
        """Convert to dictionary with summary information."""
        return {
            'id': str(self.id),
            'title': self.title,
            'severity': self.severity,
            'status': self.status,
            'triggered_at': self.triggered_at.isoformat() if self.triggered_at else None,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'duration_minutes': self.duration_minutes,
            'alert_rule_id': str(self.alert_rule_id),
        }
    
    def __str__(self) -> str:
        """String representation."""
        return f"Alert({self.title})"
    
    def __repr__(self) -> str:
        """Detailed representation."""
        return (
            f"<Alert(id={self.id}, title='{self.title}', "
            f"severity='{self.severity}', status='{self.status}')>"
        )
