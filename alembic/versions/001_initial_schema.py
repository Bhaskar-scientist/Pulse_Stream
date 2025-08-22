"""Initial database schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2025-08-20 21:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create initial database schema."""
    
    # Create tenants table
    op.create_table(
        'tenants',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, default=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('slug', sa.String(length=100), nullable=False),
        sa.Column('api_key', sa.String(length=64), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('rate_limit_per_minute', sa.Integer(), nullable=False, default=100),
        sa.Column('rate_limit_burst', sa.Integer(), nullable=False, default=200),
        sa.Column('subscription_tier', sa.String(length=50), nullable=False, default='free'),
        sa.Column('max_events_per_month', sa.Integer(), nullable=False, default=10000),
        sa.Column('max_alert_rules', sa.Integer(), nullable=False, default=10),
        sa.Column('contact_email', sa.String(length=255), nullable=True),
        sa.Column('billing_email', sa.String(length=255), nullable=True),
        sa.Column('notification_settings', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('tenant_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('current_month_events', sa.Integer(), nullable=False, default=0),
        sa.Column('last_activity_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('timezone', sa.String(length=50), nullable=False, default='UTC'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('api_key', name='uq_tenant_api_key'),
        sa.UniqueConstraint('slug', name='uq_tenant_slug')
    )
    
    # Create indexes for tenants
    op.create_index('ix_tenants_id', 'tenants', ['id'])
    op.create_index('ix_tenants_slug', 'tenants', ['slug'])
    op.create_index('ix_tenants_api_key', 'tenants', ['api_key'])
    op.create_index('ix_tenants_is_active', 'tenants', ['is_active'])
    op.create_index('ix_tenants_is_deleted', 'tenants', ['is_deleted'])
    
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, default=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('username', sa.String(length=100), nullable=True),
        sa.Column('full_name', sa.String(length=255), nullable=True),
        sa.Column('hashed_password', sa.String(length=128), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False, default='viewer'),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('is_verified', sa.Boolean(), nullable=False, default=False),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_active_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('login_count', sa.String(length=20), nullable=False, default='0'),
        sa.Column('password_changed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('preferences', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('notification_preferences', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('failed_login_attempts', sa.String(length=10), nullable=False, default='0'),
        sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('api_access_enabled', sa.Boolean(), nullable=False, default=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for users
    op.create_index('ix_users_id', 'users', ['id'])
    op.create_index('ix_users_tenant_id', 'users', ['tenant_id'])
    op.create_index('ix_users_email', 'users', ['email'])
    op.create_index('ix_users_is_active', 'users', ['is_active'])
    op.create_index('ix_users_is_deleted', 'users', ['is_deleted'])
    
    # Create events table
    op.create_table(
        'events',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, default=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('source', sa.String(length=255), nullable=True),
        sa.Column('source_version', sa.String(length=50), nullable=True),
        sa.Column('event_timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ingested_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('event_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('external_id', sa.String(length=255), nullable=True),
        sa.Column('correlation_id', sa.String(length=255), nullable=True),
        sa.Column('processing_status', sa.String(length=20), nullable=False, default='pending'),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('status_code', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('geo_country', sa.String(length=3), nullable=True),
        sa.Column('geo_city', sa.String(length=100), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('device_type', sa.String(length=50), nullable=True),
        sa.Column('alert_processed', sa.String(length=10), nullable=False, default='false'),
        sa.Column('alerts_triggered', sa.Integer(), nullable=False, default=0),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for events
    op.create_index('ix_events_id', 'events', ['id'])
    op.create_index('ix_events_tenant_id', 'events', ['tenant_id'])
    op.create_index('ix_events_event_type', 'events', ['event_type'])
    op.create_index('ix_events_source', 'events', ['source'])
    op.create_index('ix_events_event_timestamp', 'events', ['event_timestamp'])
    op.create_index('ix_events_ingested_at', 'events', ['ingested_at'])
    op.create_index('ix_events_external_id', 'events', ['external_id'])
    op.create_index('ix_events_correlation_id', 'events', ['correlation_id'])
    op.create_index('ix_events_processing_status', 'events', ['processing_status'])
    op.create_index('ix_events_duration_ms', 'events', ['duration_ms'])
    op.create_index('ix_events_status_code', 'events', ['status_code'])
    op.create_index('ix_events_geo_country', 'events', ['geo_country'])
    op.create_index('ix_events_device_type', 'events', ['device_type'])
    op.create_index('ix_events_alert_processed', 'events', ['alert_processed'])
    op.create_index('ix_events_is_deleted', 'events', ['is_deleted'])
    
    # Create composite indexes for events
    op.create_index('idx_events_tenant_timestamp', 'events', ['tenant_id', 'event_timestamp'])
    op.create_index('idx_events_tenant_type_timestamp', 'events', ['tenant_id', 'event_type', 'event_timestamp'])
    op.create_index('idx_events_processing_status', 'events', ['processing_status', 'tenant_id'])
    op.create_index('idx_events_alert_processing', 'events', ['alert_processed', 'tenant_id'])
    op.create_index('idx_events_status_code', 'events', ['tenant_id', 'status_code'])
    op.create_index('idx_events_duration', 'events', ['tenant_id', 'duration_ms'])
    op.create_index('idx_events_correlation', 'events', ['tenant_id', 'correlation_id'])
    
    # Create alert_rules table
    op.create_table(
        'alert_rules',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, default=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('event_type', sa.String(length=50), nullable=True),
        sa.Column('condition', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('threshold_value', sa.Float(), nullable=True),
        sa.Column('threshold_operator', sa.String(length=10), nullable=True),
        sa.Column('time_window', sa.String(length=10), nullable=False, default='5m'),
        sa.Column('evaluation_interval', sa.Integer(), nullable=False, default=60),
        sa.Column('severity', sa.String(length=20), nullable=False, default='medium'),
        sa.Column('notification_channels', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('notification_template', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('cooldown_minutes', sa.Integer(), nullable=False, default=5),
        sa.Column('max_alerts_per_hour', sa.Integer(), nullable=False, default=10),
        sa.Column('last_evaluated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_triggered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('total_triggers', sa.Integer(), nullable=False, default=0),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for alert_rules
    op.create_index('ix_alert_rules_id', 'alert_rules', ['id'])
    op.create_index('ix_alert_rules_tenant_id', 'alert_rules', ['tenant_id'])
    op.create_index('ix_alert_rules_event_type', 'alert_rules', ['event_type'])
    op.create_index('ix_alert_rules_is_active', 'alert_rules', ['is_active'])
    op.create_index('ix_alert_rules_is_deleted', 'alert_rules', ['is_deleted'])
    op.create_index('idx_alert_rules_tenant_active', 'alert_rules', ['tenant_id', 'is_active'])
    op.create_index('idx_alert_rules_evaluation', 'alert_rules', ['is_active', 'last_evaluated_at'])
    op.create_index('idx_alert_rules_event_type', 'alert_rules', ['tenant_id', 'event_type'])
    
    # Create alerts table
    op.create_table(
        'alerts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, default=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('alert_rule_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('event_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, default='active'),
        sa.Column('triggered_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('trigger_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('alert_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('notifications_sent', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('notification_failures', sa.Integer(), nullable=False, default=0),
        sa.Column('resolved_by', sa.String(length=255), nullable=True),
        sa.Column('resolution_note', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['alert_rule_id'], ['alert_rules.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['event_id'], ['events.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for alerts
    op.create_index('ix_alerts_id', 'alerts', ['id'])
    op.create_index('ix_alerts_tenant_id', 'alerts', ['tenant_id'])
    op.create_index('ix_alerts_alert_rule_id', 'alerts', ['alert_rule_id'])
    op.create_index('ix_alerts_event_id', 'alerts', ['event_id'])
    op.create_index('ix_alerts_severity', 'alerts', ['severity'])
    op.create_index('ix_alerts_status', 'alerts', ['status'])
    op.create_index('ix_alerts_triggered_at', 'alerts', ['triggered_at'])
    op.create_index('ix_alerts_is_deleted', 'alerts', ['is_deleted'])
    op.create_index('idx_alerts_tenant_status', 'alerts', ['tenant_id', 'status'])
    op.create_index('idx_alerts_tenant_severity', 'alerts', ['tenant_id', 'severity'])
    op.create_index('idx_alerts_triggered_at', 'alerts', ['tenant_id', 'triggered_at'])
    op.create_index('idx_alerts_rule_status', 'alerts', ['alert_rule_id', 'status'])


def downgrade() -> None:
    """Drop all tables."""
    op.drop_table('alerts')
    op.drop_table('alert_rules')
    op.drop_table('events')
    op.drop_table('users')
    op.drop_table('tenants')
