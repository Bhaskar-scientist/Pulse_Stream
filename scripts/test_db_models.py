#!/usr/bin/env python3
"""Test script to validate database models and connections."""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, Any

from core.database import get_async_session, init_database
from core.logging import configure_logging, get_logger
from apps.storage.crud import tenant_crud, user_crud, event_crud, alert_rule_crud

# Configure logging
configure_logging("DEBUG", "console")
logger = get_logger(__name__)


async def test_tenant_operations():
    """Test tenant CRUD operations."""
    logger.info("Testing tenant operations")
    
    async for session in get_async_session():
        # Create test tenant
        tenant = await tenant_crud.create_tenant(
            session,
            name="Test Company",
            slug="test-company",
            contact_email="admin@test-company.com"
        )
        logger.info(f"Created tenant: {tenant}")
        
        # Get by API key
        found_tenant = await tenant_crud.get_by_api_key(
            session, api_key=tenant.api_key
        )
        assert found_tenant is not None
        assert found_tenant.id == tenant.id
        logger.info("✅ Tenant lookup by API key works")
        
        # Get by slug
        found_tenant = await tenant_crud.get_by_slug(
            session, slug="test-company"
        )
        assert found_tenant is not None
        assert found_tenant.id == tenant.id
        logger.info("✅ Tenant lookup by slug works")
        
        return tenant


async def test_user_operations(tenant):
    """Test user CRUD operations."""
    logger.info("Testing user operations")
    
    async for session in get_async_session():
        # Create test user
        user = await user_crud.create_user(
            session,
            tenant_id=tenant.id,
            email="admin@test-company.com",
            password="secure_password_123",
            full_name="Test Admin",
            role="admin"
        )
        logger.info(f"Created user: {user}")
        
        # Test authentication
        auth_user = await user_crud.authenticate(
            session,
            tenant_id=tenant.id,
            email="admin@test-company.com",
            password="secure_password_123"
        )
        assert auth_user is not None
        assert auth_user.id == user.id
        logger.info("✅ User authentication works")
        
        # Test wrong password
        auth_user = await user_crud.authenticate(
            session,
            tenant_id=tenant.id,
            email="admin@test-company.com",
            password="wrong_password"
        )
        assert auth_user is None
        logger.info("✅ Wrong password rejected")
        
        return user


async def test_event_operations(tenant):
    """Test event CRUD operations."""
    logger.info("Testing event operations")
    
    async for session in get_async_session():
        # Create test events
        event1 = await event_crud.create_event(
            session,
            tenant_id=tenant.id,
            event_type="api_call",
            payload={
                "endpoint": "/api/users",
                "method": "GET",
                "status_code": 200,
                "response_time": 150
            },
            source="web-api",
            correlation_id="req-123"
        )
        logger.info(f"Created event 1: {event1}")
        
        event2 = await event_crud.create_event(
            session,
            tenant_id=tenant.id,
            event_type="api_call",
            payload={
                "endpoint": "/api/orders",
                "method": "POST",
                "status_code": 500,
                "response_time": 2500,
                "error": "Database connection timeout"
            },
            source="web-api",
            correlation_id="req-124"
        )
        logger.info(f"Created event 2: {event2}")
        
        # Test metric extraction
        assert event1.status_code == 200
        assert event1.duration_ms == 150
        assert event2.status_code == 500
        assert event2.duration_ms == 2500
        assert event2.is_error
        assert event2.is_slow
        logger.info("✅ Event metric extraction works")
        
        # Test tenant isolation
        events = await event_crud.get_multi_by_tenant(
            session, tenant_id=tenant.id
        )
        assert len(events) == 2
        logger.info("✅ Event tenant isolation works")
        
        return [event1, event2]


async def test_alert_rule_operations(tenant):
    """Test alert rule CRUD operations."""
    logger.info("Testing alert rule operations")
    
    async for session in get_async_session():
        # Create test alert rule
        alert_rule = await alert_rule_crud.create_for_tenant(
            session,
            tenant_id=tenant.id,
            obj_in={
                "name": "High Error Rate",
                "description": "Alert when error rate > 5%",
                "event_type": "api_call",
                "condition": {
                    "field": "status_code",
                    "operator": ">=",
                    "value": 400
                },
                "threshold_value": 5.0,
                "threshold_operator": ">",
                "time_window": "5m",
                "severity": "high",
                "notification_channels": ["email", "slack"]
            }
        )
        logger.info(f"Created alert rule: {alert_rule}")
        
        # Test getting active rules
        active_rules = await alert_rule_crud.get_active_rules(
            session, tenant_id=tenant.id
        )
        assert len(active_rules) == 1
        assert active_rules[0].id == alert_rule.id
        logger.info("✅ Alert rule creation and retrieval works")
        
        return alert_rule


async def test_multi_tenant_isolation():
    """Test that multi-tenant isolation works correctly."""
    logger.info("Testing multi-tenant isolation")
    
    async for session in get_async_session():
        # Create two tenants
        tenant1 = await tenant_crud.create_tenant(
            session,
            name="Company A",
            slug="company-a",
            contact_email="admin@company-a.com"
        )
        
        tenant2 = await tenant_crud.create_tenant(
            session,
            name="Company B", 
            slug="company-b",
            contact_email="admin@company-b.com"
        )
        
        # Create events for each tenant
        event1 = await event_crud.create_event(
            session,
            tenant_id=tenant1.id,
            event_type="test",
            payload={"data": "tenant1"}
        )
        
        event2 = await event_crud.create_event(
            session,
            tenant_id=tenant2.id,
            event_type="test",
            payload={"data": "tenant2"}
        )
        
        # Test isolation - tenant1 should only see their events
        tenant1_events = await event_crud.get_multi_by_tenant(
            session, tenant_id=tenant1.id
        )
        assert len(tenant1_events) == 1
        assert tenant1_events[0].id == event1.id
        
        # Test isolation - tenant2 should only see their events
        tenant2_events = await event_crud.get_multi_by_tenant(
            session, tenant_id=tenant2.id
        )
        assert len(tenant2_events) == 1
        assert tenant2_events[0].id == event2.id
        
        logger.info("✅ Multi-tenant isolation works correctly")


async def main():
    """Main test function."""
    logger.info("🧪 Starting database model tests")
    
    try:
        # Initialize database (this would normally be done on app startup)
        await init_database()
        logger.info("✅ Database initialized")
        
        # Test tenant operations
        tenant = await test_tenant_operations()
        
        # Test user operations
        user = await test_user_operations(tenant)
        
        # Test event operations
        events = await test_event_operations(tenant)
        
        # Test alert rule operations
        alert_rule = await test_alert_rule_operations(tenant)
        
        # Test multi-tenant isolation
        await test_multi_tenant_isolation()
        
        logger.info("🎉 All database model tests passed!")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())
