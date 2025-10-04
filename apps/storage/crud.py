"""CRUD operations with tenant isolation for PulseStream."""

import uuid
from typing import Any, Dict, List, Optional, Type, TypeVar, Generic
from datetime import datetime, timedelta

from sqlalchemy import and_, desc, func, select, update, delete, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.database import Base, TenantMixin
from core.errors import TenantNotFoundError, ValidationError
from core.logging import get_logger
from apps.storage.models.tenant import Tenant
from apps.storage.models.user import User
from apps.storage.models.event import Event
from apps.storage.models.alert import AlertRule, Alert

logger = get_logger(__name__)

ModelType = TypeVar("ModelType", bound=Base)
TenantModelType = TypeVar("TenantModelType", bound=TenantMixin)


class BaseCRUD(Generic[ModelType]):
    """Base CRUD operations."""
    
    def __init__(self, model: Type[ModelType]):
        self.model = model
    
    async def create(
        self,
        session: AsyncSession,
        *,
        obj_in: Dict[str, Any]
    ) -> ModelType:
        """Create a new record."""
        db_obj = self.model(**obj_in)
        session.add(db_obj)
        await session.flush()
        await session.refresh(db_obj)
        return db_obj
    
    async def get(
        self,
        session: AsyncSession,
        id: uuid.UUID
    ) -> Optional[ModelType]:
        """Get record by ID."""
        result = await session.execute(
            select(self.model).where(
                and_(
                    self.model.id == id,
                    self.model.is_deleted == False
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def get_multi(
        self,
        session: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100
    ) -> List[ModelType]:
        """Get multiple records."""
        result = await session.execute(
            select(self.model)
            .where(self.model.is_deleted == False)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def update(
        self,
        session: AsyncSession,
        *,
        db_obj: ModelType,
        obj_in: Dict[str, Any]
    ) -> ModelType:
        """Update a record."""
        for field, value in obj_in.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        
        await session.flush()
        await session.refresh(db_obj)
        return db_obj
    
    async def delete(
        self,
        session: AsyncSession,
        *,
        id: uuid.UUID
    ) -> Optional[ModelType]:
        """Soft delete a record."""
        db_obj = await self.get(session, id)
        if db_obj:
            db_obj.is_deleted = True
            await session.flush()
        return db_obj
    
    async def count(self, session: AsyncSession) -> int:
        """Count records."""
        result = await session.execute(
            select(func.count())
            .select_from(self.model)
            .where(self.model.is_deleted == False)
        )
        return result.scalar()


class TenantCRUD(BaseCRUD[TenantModelType]):
    """CRUD operations with tenant isolation."""
    
    async def get_by_tenant(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        id: uuid.UUID
    ) -> Optional[TenantModelType]:
        """Get record by ID with tenant isolation."""
        result = await session.execute(
            select(self.model).where(
                and_(
                    self.model.id == id,
                    self.model.tenant_id == tenant_id,
                    self.model.is_deleted == False
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def get_multi_by_tenant(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[TenantModelType]:
        """Get multiple records with tenant isolation."""
        result = await session.execute(
            select(self.model)
            .where(
                and_(
                    self.model.tenant_id == tenant_id,
                    self.model.is_deleted == False
                )
            )
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def create_for_tenant(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        obj_in: Dict[str, Any]
    ) -> TenantModelType:
        """Create a new record for a specific tenant."""
        obj_in["tenant_id"] = tenant_id
        return await self.create(session, obj_in=obj_in)
    
    async def count_by_tenant(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID
    ) -> int:
        """Count records for a specific tenant."""
        result = await session.execute(
            select(func.count())
            .select_from(self.model)
            .where(
                and_(
                    self.model.tenant_id == tenant_id,
                    self.model.is_deleted == False
                )
            )
        )
        return result.scalar()


class TenantCRUDOperations(BaseCRUD[Tenant]):
    """CRUD operations for tenants."""
    
    async def get_by_slug(
        self,
        session: AsyncSession,
        *,
        slug: str
    ) -> Optional[Tenant]:
        """Get tenant by slug."""
        result = await session.execute(
            select(Tenant).where(
                and_(
                    Tenant.slug == slug,
                    Tenant.is_deleted == False
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def get_by_api_key(
        self,
        session: AsyncSession,
        *,
        api_key: str
    ) -> Optional[Tenant]:
        """Get tenant by API key."""
        result = await session.execute(
            select(Tenant).where(
                and_(
                    Tenant.api_key == api_key,
                    Tenant.is_active == True,
                    Tenant.is_deleted == False
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def get_by_contact_email(
        self,
        session: AsyncSession,
        *,
        email: str
    ) -> Optional[Tenant]:
        """Get tenant by contact email."""
        result = await session.execute(
            select(Tenant).where(
                and_(
                    Tenant.contact_email == email,
                    Tenant.is_deleted == False
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def create_tenant(
        self,
        session: AsyncSession,
        *,
        name: str,
        slug: str,
        contact_email: Optional[str] = None,
        billing_email: Optional[str] = None,
        subscription_tier: Optional[str] = None,
        timezone: Optional[str] = None,
        api_key: Optional[str] = None
    ) -> Tenant:
        """Create a new tenant with auto-generated API key."""
        # Check if slug already exists
        existing = await self.get_by_slug(session, slug=slug)
        if existing:
            raise ValidationError(f"Tenant with slug '{slug}' already exists")
        
        tenant_data = {
            "name": name,
            "slug": slug,
            "api_key": api_key or Tenant.generate_api_key(),
            "contact_email": contact_email,
            "billing_email": billing_email,
            "subscription_tier": subscription_tier,
            "timezone": timezone,
        }
        
        return await self.create(session, obj_in=tenant_data)
    
    async def update_activity(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID
    ) -> None:
        """Update tenant's last activity timestamp."""
        await session.execute(
            update(Tenant)
            .where(Tenant.id == tenant_id)
            .values(last_activity_at=func.now())
        )
    
    async def increment_monthly_events(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        count: int = 1
    ) -> None:
        """Increment tenant's monthly event counter."""
        await session.execute(
            update(Tenant)
            .where(Tenant.id == tenant_id)
            .values(current_month_events=Tenant.current_month_events + count)
        )


class UserCRUDOperations(TenantCRUD[User]):
    """CRUD operations for users."""
    
    async def get_by_email(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        email: str
    ) -> Optional[User]:
        """Get user by email within tenant."""
        result = await session.execute(
            select(User).where(
                and_(
                    User.tenant_id == tenant_id,
                    User.email == email,
                    User.is_deleted == False
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def create_user(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        email: str,
        password: str,
        full_name: Optional[str] = None,
        role: str = "viewer"
    ) -> User:
        """Create a new user."""
        # Check if email already exists for this tenant
        existing = await self.get_by_email(session, tenant_id=tenant_id, email=email)
        if existing:
            raise ValidationError(f"User with email '{email}' already exists for this tenant")
        
        user_data = {
            "tenant_id": tenant_id,
            "email": email,
            "full_name": full_name,
            "role": role,
            "hashed_password": User.get_password_hash(password),
            "password_changed_at": func.now(),
        }
        
        return await self.create(session, obj_in=user_data)
    
    async def authenticate(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        email: str,
        password: str
    ) -> Optional[User]:
        """Authenticate user."""
        user = await self.get_by_email(session, tenant_id=tenant_id, email=email)
        if not user:
            return None
        
        if not user.is_active:
            return None
        
        if user.is_account_locked():
            return None
        
        if not user.check_password(password):
            user.record_failed_login()
            await session.flush()
            return None
        
        user.record_login()
        await session.flush()
        return user


class EventCRUDOperations(TenantCRUD[Event]):
    """CRUD operations for events."""
    
    async def create_event(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        event_type: str,
        payload: Dict[str, Any],
        event_timestamp: Optional[datetime] = None,
        source: Optional[str] = None,
        external_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        event_metadata: Optional[Dict[str, Any]] = None
    ) -> Event:
        """Create a new event."""
        event_data = {
            "tenant_id": tenant_id,
            "event_type": event_type,
            "payload": payload,
            "event_timestamp": event_timestamp or func.now(),
            "source": source,
            "external_id": external_id,
            "correlation_id": correlation_id,
            "event_metadata": event_metadata,
        }
        
        event = await self.create(session, obj_in=event_data)
        
        # Extract common metrics
        event.extract_common_metrics()
        
        # Extract enrichment data
        event.enrich_from_metadata()
        
        await session.flush()
        return event
    
    async def get_events_by_time_range(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        start_time: datetime,
        end_time: datetime,
        event_type: Optional[str] = None,
        limit: int = 1000
    ) -> List[Event]:
        """Get events within a time range."""
        query = select(Event).where(
            and_(
                Event.tenant_id == tenant_id,
                Event.event_timestamp >= start_time,
                Event.event_timestamp <= end_time,
                Event.is_deleted == False
            )
        )
        
        if event_type:
            query = query.where(Event.event_type == event_type)
        
        query = query.order_by(desc(Event.event_timestamp)).limit(limit)
        
        result = await session.execute(query)
        return list(result.scalars().all())
    
    async def get_pending_events(
        self,
        session: AsyncSession,
        *,
        tenant_id: Optional[uuid.UUID] = None,
        limit: int = 100
    ) -> List[Event]:
        """Get events pending processing."""
        query = select(Event).where(
            and_(
                Event.processing_status == "pending",
                Event.is_deleted == False
            )
        )
        
        if tenant_id:
            query = query.where(Event.tenant_id == tenant_id)
        
        query = query.order_by(Event.ingested_at).limit(limit)
        
        result = await session.execute(query)
        return list(result.scalars().all())
    
    async def get_by_external_id(
        self,
        session: AsyncSession,
        *,
        external_id: str,
        tenant_id: uuid.UUID
    ) -> Optional[Event]:
        """Get event by external_id (for duplicate detection)."""
        result = await session.execute(
            select(Event).where(
                and_(
                    Event.external_id == external_id,
                    Event.tenant_id == tenant_id,
                    Event.is_deleted == False
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def get_by_event_id(
        self,
        session: AsyncSession,
        event_id: str,
        tenant_id: uuid.UUID
    ) -> Optional[Event]:
        """Get event by event_id (client-provided ID)."""
        # Note: event_id is stored in external_id field
        return await self.get_by_external_id(
            session,
            external_id=event_id,
            tenant_id=tenant_id
        )
    
    async def count_by_tenant_and_time(
        self,
        session: AsyncSession,
        tenant_id: str,
        since: datetime
    ) -> int:
        """Count events for a tenant since a specific time."""
        query = select(func.count()).select_from(Event).where(
            and_(
                Event.tenant_id == tenant_id,
                Event.event_timestamp >= since,
                Event.is_deleted == False
            )
        )
        result = await session.execute(query)
        return result.scalar()
    
    async def get_last_by_tenant(
        self,
        session: AsyncSession,
        tenant_id: str
    ) -> Optional[Event]:
        """Get the most recent event for a tenant."""
        query = select(Event).where(
            and_(
                Event.tenant_id == tenant_id,
                Event.is_deleted == False
            )
        ).order_by(desc(Event.event_timestamp)).limit(1)
        result = await session.execute(query)
        return result.scalar_one_or_none()
    
    async def count_by_tenant_and_severity(
        self,
        session: AsyncSession,
        tenant_id: str,
        severity: str,
        since: datetime
    ) -> int:
        """Count events for a tenant with specific severity since a time."""
        # Since Event model doesn't have severity field, we'll count by status_code >= 500
        # This is a reasonable approximation for error events
        query = select(func.count()).select_from(Event).where(
            and_(
                Event.tenant_id == tenant_id,
                Event.status_code >= 500,
                Event.event_timestamp >= since,
                Event.is_deleted == False
            )
        )
        result = await session.execute(query)
        return result.scalar()
    
    async def count_by_conditions(
        self,
        session: AsyncSession,
        *,
        conditions: List[Any]
    ) -> int:
        """Count events matching the given conditions."""
        query = select(func.count()).select_from(Event).where(and_(*conditions))
        result = await session.execute(query)
        return result.scalar()
    
    async def get_by_conditions(
        self,
        session: AsyncSession,
        *,
        conditions: List[Any],
        limit: int = 100,
        offset: int = 0,
        order_by: Optional[Any] = None
    ) -> List[Event]:
        """Get events matching the given conditions."""
        query = select(Event).where(and_(*conditions))
        
        if order_by is not None:
            query = query.order_by(order_by)
        
        query = query.offset(offset).limit(limit)
        result = await session.execute(query)
        return list(result.scalars().all())
    
    async def get_events_for_alert_processing(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        since: datetime,
        event_type: Optional[str] = None
    ) -> List[Event]:
        """Get events that need alert processing."""
        query = select(Event).where(
            and_(
                Event.tenant_id == tenant_id,
                Event.alert_processed == "false",
                Event.event_timestamp >= since,
                Event.is_deleted == False
            )
        )
        
        if event_type:
            query = query.where(Event.event_type == event_type)
        
        result = await session.execute(query)
        return list(result.scalars().all())
    
    async def get_recent_by_tenant(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        limit: int = 10
    ) -> List[Event]:
        """Get recent events for a tenant."""
        query = select(Event).where(
            and_(
                Event.tenant_id == tenant_id,
                Event.is_deleted == False
            )
        ).order_by(desc(Event.event_timestamp)).limit(limit)
        
        result = await session.execute(query)
        return list(result.scalars().all())


class AlertRuleCRUDOperations(TenantCRUD[AlertRule]):
    """CRUD operations for alert rules."""
    
    async def get_active_rules(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID
    ) -> List[AlertRule]:
        """Get all active alert rules for a tenant."""
        result = await session.execute(
            select(AlertRule).where(
                and_(
                    AlertRule.tenant_id == tenant_id,
                    AlertRule.is_active == True,
                    AlertRule.is_deleted == False
                )
            )
        )
        return list(result.scalars().all())
    
    async def get_rules_for_evaluation(
        self,
        session: AsyncSession,
        *,
        tenant_id: Optional[uuid.UUID] = None
    ) -> List[AlertRule]:
        """Get rules that need evaluation."""
        query = select(AlertRule).where(
            and_(
                AlertRule.is_active == True,
                AlertRule.is_deleted == False
            )
        )
        
        if tenant_id:
            query = query.where(AlertRule.tenant_id == tenant_id)
        
        # Rules that haven't been evaluated recently
        cutoff = func.now() - func.interval('1 minute') * AlertRule.evaluation_interval
        query = query.where(
            or_(
                AlertRule.last_evaluated_at.is_(None),
                AlertRule.last_evaluated_at < cutoff
            )
        )
        
        result = await session.execute(query)
        return list(result.scalars().all())


class AlertCRUDOperations(TenantCRUD[Alert]):
    """CRUD operations for alerts."""
    
    async def create_alert(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        alert_rule_id: uuid.UUID,
        title: str,
        message: str,
        severity: str,
        trigger_data: Optional[Dict[str, Any]] = None,
        event_id: Optional[uuid.UUID] = None
    ) -> Alert:
        """Create a new alert."""
        alert_data = {
            "tenant_id": tenant_id,
            "alert_rule_id": alert_rule_id,
            "title": title,
            "message": message,
            "severity": severity,
            "triggered_at": func.now(),
            "trigger_data": trigger_data,
            "event_id": event_id,
        }
        
        return await self.create(session, obj_in=alert_data)
    
    async def get_active_alerts(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        limit: int = 100
    ) -> List[Alert]:
        """Get active alerts for a tenant."""
        result = await session.execute(
            select(Alert)
            .options(selectinload(Alert.alert_rule))
            .where(
                and_(
                    Alert.tenant_id == tenant_id,
                    Alert.status == "active",
                    Alert.is_deleted == False
                )
            )
            .order_by(desc(Alert.triggered_at))
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_recent_alerts_for_rule(
        self,
        session: AsyncSession,
        *,
        alert_rule_id: uuid.UUID,
        hours: int = 1
    ) -> List[Alert]:
        """Get recent alerts for a specific rule."""
        cutoff = func.now() - func.interval(f'{hours} hours')
        
        result = await session.execute(
            select(Alert).where(
                and_(
                    Alert.alert_rule_id == alert_rule_id,
                    Alert.triggered_at >= cutoff,
                    Alert.is_deleted == False
                )
            )
        )
        return list(result.scalars().all())
    
    async def get_recent_alerts(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        limit: int = 10
    ) -> List[Alert]:
        """Get recent alerts for a tenant."""
        result = await session.execute(
            select(Alert)
            .options(selectinload(Alert.alert_rule))
            .where(
                and_(
                    Alert.tenant_id == tenant_id,
                    Alert.is_deleted == False
                )
            )
            .order_by(desc(Alert.triggered_at))
            .limit(limit)
        )
        return list(result.scalars().all())


# Create CRUD instances
tenant_crud = TenantCRUDOperations(Tenant)
user_crud = UserCRUDOperations(User)
event_crud = EventCRUDOperations(Event)
alert_rule_crud = AlertRuleCRUDOperations(AlertRule)
alert_crud = AlertCRUDOperations(Alert)
