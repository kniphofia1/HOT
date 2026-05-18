from datetime import datetime
from typing import Any, TypeVar

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    AuditLog,
    BriefExport,
    BriefReview,
    EventAnnotation,
    EventBookmark,
    EventCluster,
    Source,
    SourceSpaceLink,
    TeamMembership,
    TeamSpace,
    TeamUser,
)
from app.db.session import get_db


router = APIRouter(prefix="/api/team", tags=["team"])
ModelT = TypeVar("ModelT")


class TeamUserCreate(BaseModel):
    display_name: str = Field(alias="displayName")
    email: str | None = None
    role: str = "analyst"

    model_config = ConfigDict(populate_by_name=True)


class TeamUserRead(BaseModel):
    id: str
    display_name: str = Field(alias="displayName")
    email: str | None
    role: str
    created_at: datetime = Field(alias="createdAt")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class TeamSpaceCreate(BaseModel):
    name: str
    description: str | None = None
    actor_user_id: str | None = Field(default=None, alias="actorUserId")

    model_config = ConfigDict(populate_by_name=True)


class TeamSpaceRead(BaseModel):
    id: str
    name: str
    description: str | None
    created_at: datetime = Field(alias="createdAt")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class TeamMembershipCreate(BaseModel):
    space_id: str = Field(alias="spaceId")
    user_id: str = Field(alias="userId")
    role: str = "member"
    actor_user_id: str | None = Field(default=None, alias="actorUserId")

    model_config = ConfigDict(populate_by_name=True)


class TeamMembershipRead(BaseModel):
    id: str
    space_id: str = Field(alias="spaceId")
    user_id: str = Field(alias="userId")
    role: str
    created_at: datetime = Field(alias="createdAt")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class SourceSpaceLinkCreate(BaseModel):
    space_id: str = Field(alias="spaceId")
    source_id: str = Field(alias="sourceId")
    actor_user_id: str | None = Field(default=None, alias="actorUserId")

    model_config = ConfigDict(populate_by_name=True)


class SourceSpaceLinkRead(BaseModel):
    id: str
    space_id: str = Field(alias="spaceId")
    source_id: str = Field(alias="sourceId")
    created_by_user_id: str | None = Field(alias="createdByUserId")
    created_at: datetime = Field(alias="createdAt")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class EventBookmarkCreate(BaseModel):
    space_id: str = Field(alias="spaceId")
    user_id: str = Field(alias="userId")
    event_cluster_id: str = Field(alias="eventClusterId")
    note: str | None = None

    model_config = ConfigDict(populate_by_name=True)


class EventBookmarkRead(BaseModel):
    id: str
    space_id: str = Field(alias="spaceId")
    user_id: str = Field(alias="userId")
    event_cluster_id: str = Field(alias="eventClusterId")
    note: str | None
    created_at: datetime = Field(alias="createdAt")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class EventAnnotationCreate(BaseModel):
    space_id: str = Field(alias="spaceId")
    user_id: str = Field(alias="userId")
    event_cluster_id: str = Field(alias="eventClusterId")
    label: str
    note: str
    status: str = "open"

    model_config = ConfigDict(populate_by_name=True)


class EventAnnotationRead(BaseModel):
    id: str
    space_id: str = Field(alias="spaceId")
    user_id: str = Field(alias="userId")
    event_cluster_id: str = Field(alias="eventClusterId")
    label: str
    note: str
    status: str
    created_at: datetime = Field(alias="createdAt")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class BriefReviewCreate(BaseModel):
    space_id: str = Field(alias="spaceId")
    brief_export_id: str = Field(alias="briefExportId")
    requested_by_user_id: str = Field(alias="requestedByUserId")
    reviewer_user_id: str | None = Field(default=None, alias="reviewerUserId")
    notes: str | None = None

    model_config = ConfigDict(populate_by_name=True)


class BriefReviewUpdate(BaseModel):
    actor_user_id: str | None = Field(default=None, alias="actorUserId")
    reviewer_user_id: str | None = Field(default=None, alias="reviewerUserId")
    status: str | None = None
    notes: str | None = None

    model_config = ConfigDict(populate_by_name=True)


class BriefReviewRead(BaseModel):
    id: str
    space_id: str = Field(alias="spaceId")
    brief_export_id: str = Field(alias="briefExportId")
    requested_by_user_id: str = Field(alias="requestedByUserId")
    reviewer_user_id: str | None = Field(alias="reviewerUserId")
    status: str
    notes: str | None
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class AuditLogRead(BaseModel):
    id: str
    actor_user_id: str | None = Field(alias="actorUserId")
    action: str
    entity_type: str = Field(alias="entityType")
    entity_id: str = Field(alias="entityId")
    detail_json: dict[str, Any] = Field(alias="detailJson")
    created_at: datetime = Field(alias="createdAt")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class TeamSummaryRead(BaseModel):
    users: list[TeamUserRead]
    spaces: list[TeamSpaceRead]
    memberships: list[TeamMembershipRead]
    source_links: list[SourceSpaceLinkRead] = Field(alias="sourceLinks")
    bookmarks: list[EventBookmarkRead]
    annotations: list[EventAnnotationRead]
    brief_reviews: list[BriefReviewRead] = Field(alias="briefReviews")
    audit_logs: list[AuditLogRead] = Field(alias="auditLogs")

    model_config = ConfigDict(populate_by_name=True)


@router.get("/summary", response_model=TeamSummaryRead)
def team_summary(db: Session = Depends(get_db)) -> dict[str, list]:
    return {
        "users": list(db.scalars(select(TeamUser).order_by(TeamUser.created_at.desc())).all()),
        "spaces": list(db.scalars(select(TeamSpace).order_by(TeamSpace.created_at.desc())).all()),
        "memberships": list(db.scalars(select(TeamMembership).order_by(TeamMembership.created_at.desc())).all()),
        "sourceLinks": list(db.scalars(select(SourceSpaceLink).order_by(SourceSpaceLink.created_at.desc())).all()),
        "bookmarks": list(db.scalars(select(EventBookmark).order_by(EventBookmark.created_at.desc())).all()),
        "annotations": list(db.scalars(select(EventAnnotation).order_by(EventAnnotation.created_at.desc())).all()),
        "briefReviews": list(db.scalars(select(BriefReview).order_by(BriefReview.created_at.desc())).all()),
        "auditLogs": list(db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(50)).all()),
    }


@router.post("/users", response_model=TeamUserRead, status_code=status.HTTP_201_CREATED)
def create_user(payload: TeamUserCreate, db: Session = Depends(get_db)) -> TeamUser:
    user = TeamUser(
        display_name=payload.display_name.strip(),
        email=payload.email.strip() if payload.email else None,
        role=payload.role.strip() or "analyst",
    )
    db.add(user)
    db.flush()
    _audit(db, user.id, "team_user.created", "TeamUser", user.id, {"displayName": user.display_name})
    db.commit()
    db.refresh(user)
    return user


@router.post("/spaces", response_model=TeamSpaceRead, status_code=status.HTTP_201_CREATED)
def create_space(payload: TeamSpaceCreate, db: Session = Depends(get_db)) -> TeamSpace:
    if payload.actor_user_id:
        _require(db, TeamUser, payload.actor_user_id, "TeamUser")
    space = TeamSpace(name=payload.name.strip(), description=payload.description)
    db.add(space)
    db.flush()
    _audit(db, payload.actor_user_id, "team_space.created", "TeamSpace", space.id, {"name": space.name})
    db.commit()
    db.refresh(space)
    return space


@router.post("/memberships", response_model=TeamMembershipRead, status_code=status.HTTP_201_CREATED)
def create_membership(payload: TeamMembershipCreate, db: Session = Depends(get_db)) -> TeamMembership:
    _require(db, TeamSpace, payload.space_id, "TeamSpace")
    _require(db, TeamUser, payload.user_id, "TeamUser")
    membership = TeamMembership(space_id=payload.space_id, user_id=payload.user_id, role=payload.role)
    db.add(membership)
    db.flush()
    _audit(db, payload.actor_user_id or payload.user_id, "team_membership.created", "TeamMembership", membership.id, {})
    db.commit()
    db.refresh(membership)
    return membership


@router.post("/source-links", response_model=SourceSpaceLinkRead, status_code=status.HTTP_201_CREATED)
def create_source_link(payload: SourceSpaceLinkCreate, db: Session = Depends(get_db)) -> SourceSpaceLink:
    _require(db, TeamSpace, payload.space_id, "TeamSpace")
    _require(db, Source, payload.source_id, "Source")
    if payload.actor_user_id:
        _require(db, TeamUser, payload.actor_user_id, "TeamUser")
    link = SourceSpaceLink(
        space_id=payload.space_id,
        source_id=payload.source_id,
        created_by_user_id=payload.actor_user_id,
    )
    db.add(link)
    db.flush()
    _audit(db, payload.actor_user_id, "source.shared", "SourceSpaceLink", link.id, {"sourceId": payload.source_id})
    db.commit()
    db.refresh(link)
    return link


@router.post("/bookmarks", response_model=EventBookmarkRead, status_code=status.HTTP_201_CREATED)
def create_bookmark(payload: EventBookmarkCreate, db: Session = Depends(get_db)) -> EventBookmark:
    _require(db, TeamSpace, payload.space_id, "TeamSpace")
    _require(db, TeamUser, payload.user_id, "TeamUser")
    _require(db, EventCluster, payload.event_cluster_id, "EventCluster")
    bookmark = EventBookmark(**payload.model_dump())
    db.add(bookmark)
    db.flush()
    _audit(db, payload.user_id, "event.bookmarked", "EventBookmark", bookmark.id, {"eventClusterId": payload.event_cluster_id})
    db.commit()
    db.refresh(bookmark)
    return bookmark


@router.post("/annotations", response_model=EventAnnotationRead, status_code=status.HTTP_201_CREATED)
def create_annotation(payload: EventAnnotationCreate, db: Session = Depends(get_db)) -> EventAnnotation:
    _require(db, TeamSpace, payload.space_id, "TeamSpace")
    _require(db, TeamUser, payload.user_id, "TeamUser")
    _require(db, EventCluster, payload.event_cluster_id, "EventCluster")
    annotation = EventAnnotation(**payload.model_dump())
    db.add(annotation)
    db.flush()
    _audit(db, payload.user_id, "event.annotated", "EventAnnotation", annotation.id, {"label": annotation.label})
    db.commit()
    db.refresh(annotation)
    return annotation


@router.post("/brief-reviews", response_model=BriefReviewRead, status_code=status.HTTP_201_CREATED)
def create_brief_review(payload: BriefReviewCreate, db: Session = Depends(get_db)) -> BriefReview:
    _require(db, TeamSpace, payload.space_id, "TeamSpace")
    _require(db, BriefExport, payload.brief_export_id, "BriefExport")
    _require(db, TeamUser, payload.requested_by_user_id, "TeamUser")
    if payload.reviewer_user_id:
        _require(db, TeamUser, payload.reviewer_user_id, "TeamUser")
    review = BriefReview(
        space_id=payload.space_id,
        brief_export_id=payload.brief_export_id,
        requested_by_user_id=payload.requested_by_user_id,
        reviewer_user_id=payload.reviewer_user_id,
        status="pending",
        notes=payload.notes,
    )
    db.add(review)
    db.flush()
    _audit(db, payload.requested_by_user_id, "brief_review.requested", "BriefReview", review.id, {})
    db.commit()
    db.refresh(review)
    return review


@router.patch("/brief-reviews/{review_id}", response_model=BriefReviewRead)
def update_brief_review(
    review_id: str,
    payload: BriefReviewUpdate,
    db: Session = Depends(get_db),
) -> BriefReview:
    review = _require(db, BriefReview, review_id, "BriefReview")
    if payload.reviewer_user_id:
        _require(db, TeamUser, payload.reviewer_user_id, "TeamUser")
        review.reviewer_user_id = payload.reviewer_user_id
    if payload.status:
        review.status = payload.status
    if payload.notes is not None:
        review.notes = payload.notes
    db.add(review)
    _audit(db, payload.actor_user_id or review.reviewer_user_id, "brief_review.updated", "BriefReview", review.id, {"status": review.status})
    db.commit()
    db.refresh(review)
    return review


@router.get("/audit-logs", response_model=list[AuditLogRead])
def list_audit_logs(db: Session = Depends(get_db)) -> list[AuditLog]:
    return list(db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(100)).all())


def _require(db: Session, model: type[ModelT], item_id: str, label: str) -> ModelT:
    item = db.get(model, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{label} not found")
    return item


def _audit(
    db: Session,
    actor_user_id: str | None,
    action: str,
    entity_type: str,
    entity_id: str,
    detail: dict[str, Any],
) -> None:
    db.add(
        AuditLog(
            actor_user_id=actor_user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            detail_json=detail,
        )
    )
