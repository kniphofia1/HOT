from datetime import datetime
from typing import Any, TypeVar

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    MonitoringAlertRule,
    Organization,
    OrganizationMembership,
    OrganizationSubscription,
    QuotaUsage,
    SaasAuditLog,
    SubscriptionPlan,
    TaskQueueEntry,
    TeamUser,
    TenantDataScope,
)
from app.db.session import get_db


router = APIRouter(prefix="/api/saas", tags=["saas"])
ModelT = TypeVar("ModelT")


class OrganizationCreate(BaseModel):
    name: str
    slug: str
    status: str = "active"
    actor_user_id: str | None = Field(default=None, alias="actorUserId")

    model_config = ConfigDict(populate_by_name=True)


class OrganizationRead(BaseModel):
    id: str
    name: str
    slug: str
    status: str
    created_at: datetime = Field(alias="createdAt")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class OrganizationMembershipCreate(BaseModel):
    organization_id: str = Field(alias="organizationId")
    user_id: str = Field(alias="userId")
    role: str
    permissions_json: list[str] = Field(default_factory=list, alias="permissionsJson")
    actor_user_id: str | None = Field(default=None, alias="actorUserId")

    model_config = ConfigDict(populate_by_name=True)


class OrganizationMembershipRead(BaseModel):
    id: str
    organization_id: str = Field(alias="organizationId")
    user_id: str = Field(alias="userId")
    role: str
    permissions_json: list[str] = Field(alias="permissionsJson")
    created_at: datetime = Field(alias="createdAt")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class SubscriptionPlanCreate(BaseModel):
    name: str
    code: str
    price_cents: int = Field(default=0, alias="priceCents")
    quota_json: dict[str, int] = Field(default_factory=dict, alias="quotaJson")
    actor_user_id: str | None = Field(default=None, alias="actorUserId")

    model_config = ConfigDict(populate_by_name=True)


class SubscriptionPlanRead(BaseModel):
    id: str
    name: str
    code: str
    price_cents: int = Field(alias="priceCents")
    quota_json: dict[str, int] = Field(alias="quotaJson")
    created_at: datetime = Field(alias="createdAt")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class OrganizationSubscriptionCreate(BaseModel):
    organization_id: str = Field(alias="organizationId")
    plan_id: str = Field(alias="planId")
    status: str = "active"
    actor_user_id: str | None = Field(default=None, alias="actorUserId")

    model_config = ConfigDict(populate_by_name=True)


class OrganizationSubscriptionRead(BaseModel):
    id: str
    organization_id: str = Field(alias="organizationId")
    plan_id: str = Field(alias="planId")
    status: str
    created_at: datetime = Field(alias="createdAt")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class QuotaUsageCreate(BaseModel):
    organization_id: str = Field(alias="organizationId")
    metric: str
    used: int
    limit: int
    actor_user_id: str | None = Field(default=None, alias="actorUserId")

    model_config = ConfigDict(populate_by_name=True)


class QuotaUsageRead(BaseModel):
    id: str
    organization_id: str = Field(alias="organizationId")
    metric: str
    used: int
    limit: int
    over_limit: bool = Field(alias="overLimit")
    window_start: datetime = Field(alias="windowStart")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class TaskQueueCreate(BaseModel):
    organization_id: str | None = Field(default=None, alias="organizationId")
    task_type: str = Field(alias="taskType")
    priority: int = 0
    payload_json: dict[str, Any] = Field(default_factory=dict, alias="payloadJson")
    actor_user_id: str | None = Field(default=None, alias="actorUserId")

    model_config = ConfigDict(populate_by_name=True)


class TaskQueueUpdate(BaseModel):
    status: str | None = None
    attempts: int | None = None
    last_error: str | None = Field(default=None, alias="lastError")
    actor_user_id: str | None = Field(default=None, alias="actorUserId")

    model_config = ConfigDict(populate_by_name=True)


class TaskQueueRead(BaseModel):
    id: str
    organization_id: str | None = Field(alias="organizationId")
    task_type: str = Field(alias="taskType")
    status: str
    priority: int
    attempts: int
    payload_json: dict[str, Any] = Field(alias="payloadJson")
    last_error: str | None = Field(alias="lastError")
    created_at: datetime = Field(alias="createdAt")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class MonitoringAlertCreate(BaseModel):
    organization_id: str = Field(alias="organizationId")
    name: str
    metric: str
    threshold: int
    actor_user_id: str | None = Field(default=None, alias="actorUserId")

    model_config = ConfigDict(populate_by_name=True)


class MonitoringAlertRead(BaseModel):
    id: str
    organization_id: str = Field(alias="organizationId")
    name: str
    metric: str
    threshold: int
    status: str
    created_at: datetime = Field(alias="createdAt")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class TenantDataScopeCreate(BaseModel):
    organization_id: str = Field(alias="organizationId")
    entity_type: str = Field(alias="entityType")
    entity_id: str = Field(alias="entityId")
    access_level: str = Field(default="owned", alias="accessLevel")
    actor_user_id: str | None = Field(default=None, alias="actorUserId")

    model_config = ConfigDict(populate_by_name=True)


class TenantDataScopeRead(BaseModel):
    id: str
    organization_id: str = Field(alias="organizationId")
    entity_type: str = Field(alias="entityType")
    entity_id: str = Field(alias="entityId")
    access_level: str = Field(alias="accessLevel")
    created_at: datetime = Field(alias="createdAt")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class SaasAuditLogRead(BaseModel):
    id: str
    organization_id: str | None = Field(alias="organizationId")
    actor_user_id: str | None = Field(alias="actorUserId")
    action: str
    entity_type: str = Field(alias="entityType")
    entity_id: str = Field(alias="entityId")
    detail_json: dict[str, Any] = Field(alias="detailJson")
    created_at: datetime = Field(alias="createdAt")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class SaasSummaryRead(BaseModel):
    organizations: list[OrganizationRead]
    memberships: list[OrganizationMembershipRead]
    plans: list[SubscriptionPlanRead]
    subscriptions: list[OrganizationSubscriptionRead]
    quota_usage: list[QuotaUsageRead] = Field(alias="quotaUsage")
    tasks: list[TaskQueueRead]
    alerts: list[MonitoringAlertRead]
    data_scopes: list[TenantDataScopeRead] = Field(alias="dataScopes")
    audit_logs: list[SaasAuditLogRead] = Field(alias="auditLogs")

    model_config = ConfigDict(populate_by_name=True)


@router.get("/summary", response_model=SaasSummaryRead)
def saas_summary(db: Session = Depends(get_db)) -> dict[str, list]:
    return {
        "organizations": list(db.scalars(select(Organization).order_by(Organization.created_at.desc())).all()),
        "memberships": list(db.scalars(select(OrganizationMembership).order_by(OrganizationMembership.created_at.desc())).all()),
        "plans": list(db.scalars(select(SubscriptionPlan).order_by(SubscriptionPlan.created_at.desc())).all()),
        "subscriptions": list(db.scalars(select(OrganizationSubscription).order_by(OrganizationSubscription.created_at.desc())).all()),
        "quotaUsage": [_quota_read(item) for item in db.scalars(select(QuotaUsage).order_by(QuotaUsage.created_at.desc())).all()],
        "tasks": list(db.scalars(select(TaskQueueEntry).order_by(TaskQueueEntry.created_at.desc())).all()),
        "alerts": list(db.scalars(select(MonitoringAlertRule).order_by(MonitoringAlertRule.created_at.desc())).all()),
        "dataScopes": list(db.scalars(select(TenantDataScope).order_by(TenantDataScope.created_at.desc())).all()),
        "auditLogs": list(db.scalars(select(SaasAuditLog).order_by(SaasAuditLog.created_at.desc()).limit(100)).all()),
    }


@router.post("/organizations", response_model=OrganizationRead, status_code=status.HTTP_201_CREATED)
def create_organization(payload: OrganizationCreate, db: Session = Depends(get_db)) -> Organization:
    if payload.actor_user_id:
        _require(db, TeamUser, payload.actor_user_id, "TeamUser")
    organization = Organization(name=payload.name.strip(), slug=payload.slug.strip(), status=payload.status)
    db.add(organization)
    db.flush()
    _audit(db, organization.id, payload.actor_user_id, "organization.created", "Organization", organization.id, {})
    db.commit()
    db.refresh(organization)
    return organization


@router.post("/memberships", response_model=OrganizationMembershipRead, status_code=status.HTTP_201_CREATED)
def create_membership(payload: OrganizationMembershipCreate, db: Session = Depends(get_db)) -> OrganizationMembership:
    _require(db, Organization, payload.organization_id, "Organization")
    _require(db, TeamUser, payload.user_id, "TeamUser")
    membership = OrganizationMembership(
        organization_id=payload.organization_id,
        user_id=payload.user_id,
        role=payload.role,
        permissions_json=payload.permissions_json,
    )
    db.add(membership)
    db.flush()
    _audit(db, payload.organization_id, payload.actor_user_id, "organization_membership.created", "OrganizationMembership", membership.id, {})
    db.commit()
    db.refresh(membership)
    return membership


@router.post("/plans", response_model=SubscriptionPlanRead, status_code=status.HTTP_201_CREATED)
def create_plan(payload: SubscriptionPlanCreate, db: Session = Depends(get_db)) -> SubscriptionPlan:
    plan = SubscriptionPlan(
        name=payload.name.strip(),
        code=payload.code.strip(),
        price_cents=payload.price_cents,
        quota_json=payload.quota_json,
    )
    db.add(plan)
    db.flush()
    _audit(db, None, payload.actor_user_id, "subscription_plan.created", "SubscriptionPlan", plan.id, {"code": plan.code})
    db.commit()
    db.refresh(plan)
    return plan


@router.post("/subscriptions", response_model=OrganizationSubscriptionRead, status_code=status.HTTP_201_CREATED)
def create_subscription(
    payload: OrganizationSubscriptionCreate,
    db: Session = Depends(get_db),
) -> OrganizationSubscription:
    _require(db, Organization, payload.organization_id, "Organization")
    _require(db, SubscriptionPlan, payload.plan_id, "SubscriptionPlan")
    subscription = OrganizationSubscription(
        organization_id=payload.organization_id,
        plan_id=payload.plan_id,
        status=payload.status,
    )
    db.add(subscription)
    db.flush()
    _audit(db, payload.organization_id, payload.actor_user_id, "subscription.created", "OrganizationSubscription", subscription.id, {})
    db.commit()
    db.refresh(subscription)
    return subscription


@router.post("/quota-usage", response_model=QuotaUsageRead, status_code=status.HTTP_201_CREATED)
def create_quota_usage(payload: QuotaUsageCreate, db: Session = Depends(get_db)) -> dict[str, Any]:
    _require(db, Organization, payload.organization_id, "Organization")
    usage = QuotaUsage(
        organization_id=payload.organization_id,
        metric=payload.metric,
        used=payload.used,
        limit=payload.limit,
    )
    db.add(usage)
    db.flush()
    _audit(db, payload.organization_id, payload.actor_user_id, "quota_usage.recorded", "QuotaUsage", usage.id, {"metric": usage.metric})
    db.commit()
    db.refresh(usage)
    return _quota_read(usage)


@router.post("/tasks", response_model=TaskQueueRead, status_code=status.HTTP_201_CREATED)
def create_task(payload: TaskQueueCreate, db: Session = Depends(get_db)) -> TaskQueueEntry:
    if payload.organization_id:
        _require(db, Organization, payload.organization_id, "Organization")
    task = TaskQueueEntry(
        organization_id=payload.organization_id,
        task_type=payload.task_type,
        status="queued",
        priority=payload.priority,
        attempts=0,
        payload_json=payload.payload_json,
    )
    db.add(task)
    db.flush()
    _audit(db, payload.organization_id, payload.actor_user_id, "task.queued", "TaskQueueEntry", task.id, {"taskType": task.task_type})
    db.commit()
    db.refresh(task)
    return task


@router.patch("/tasks/{task_id}", response_model=TaskQueueRead)
def update_task(task_id: str, payload: TaskQueueUpdate, db: Session = Depends(get_db)) -> TaskQueueEntry:
    task = _require(db, TaskQueueEntry, task_id, "TaskQueueEntry")
    if payload.status:
        task.status = payload.status
    if payload.attempts is not None:
        task.attempts = payload.attempts
    if payload.last_error is not None:
        task.last_error = payload.last_error
    db.add(task)
    _audit(db, task.organization_id, payload.actor_user_id, "task.updated", "TaskQueueEntry", task.id, {"status": task.status})
    db.commit()
    db.refresh(task)
    return task


@router.post("/alerts", response_model=MonitoringAlertRead, status_code=status.HTTP_201_CREATED)
def create_alert(payload: MonitoringAlertCreate, db: Session = Depends(get_db)) -> MonitoringAlertRule:
    _require(db, Organization, payload.organization_id, "Organization")
    alert = MonitoringAlertRule(
        organization_id=payload.organization_id,
        name=payload.name,
        metric=payload.metric,
        threshold=payload.threshold,
        status="active",
    )
    db.add(alert)
    db.flush()
    _audit(db, payload.organization_id, payload.actor_user_id, "alert.created", "MonitoringAlertRule", alert.id, {"metric": alert.metric})
    db.commit()
    db.refresh(alert)
    return alert


@router.post("/data-scopes", response_model=TenantDataScopeRead, status_code=status.HTTP_201_CREATED)
def create_data_scope(payload: TenantDataScopeCreate, db: Session = Depends(get_db)) -> TenantDataScope:
    _require(db, Organization, payload.organization_id, "Organization")
    scope = TenantDataScope(
        organization_id=payload.organization_id,
        entity_type=payload.entity_type,
        entity_id=payload.entity_id,
        access_level=payload.access_level,
    )
    db.add(scope)
    db.flush()
    _audit(db, payload.organization_id, payload.actor_user_id, "tenant_scope.created", "TenantDataScope", scope.id, {"entityType": scope.entity_type})
    db.commit()
    db.refresh(scope)
    return scope


def _quota_read(usage: QuotaUsage) -> dict[str, Any]:
    return {
        "id": usage.id,
        "organizationId": usage.organization_id,
        "metric": usage.metric,
        "used": usage.used,
        "limit": usage.limit,
        "overLimit": usage.used > usage.limit,
        "windowStart": usage.window_start,
    }


def _require(db: Session, model: type[ModelT], item_id: str, label: str) -> ModelT:
    item = db.get(model, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{label} not found")
    return item


def _audit(
    db: Session,
    organization_id: str | None,
    actor_user_id: str | None,
    action: str,
    entity_type: str,
    entity_id: str,
    detail: dict[str, Any],
) -> None:
    db.add(
        SaasAuditLog(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            detail_json=detail,
        )
    )
