from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.public_feed import (
    get_daily_digest,
    get_industry_digest,
    list_daily_archives,
    list_industry_reports,
    list_public_items,
)
from app.services.industry_taxonomy import INDUSTRY_QUERY_PATTERN


router = APIRouter(prefix="/api/public", tags=["public"])


class TimelineItemRead(BaseModel):
    id: str
    display_title: str = Field(alias="displayTitle")
    display_summary: str | None = Field(alias="displaySummary")
    source_name: str = Field(alias="sourceName")
    source_type: str | None = Field(alias="sourceType")
    source_names: list[str] = Field(alias="sourceNames")
    source_types: list[str] = Field(alias="sourceTypes")
    industries: list[str]
    industry_labels: list[str] = Field(alias="industryLabels")
    primary_industry: str | None = Field(alias="primaryIndustry")
    primary_industry_label: str | None = Field(alias="primaryIndustryLabel")
    related_industries: list[str] = Field(alias="relatedIndustries")
    related_industry_labels: list[str] = Field(alias="relatedIndustryLabels")
    author: str | None
    published_at: datetime | None = Field(alias="publishedAt")
    displayed_at: datetime = Field(alias="displayedAt")
    time_basis: str = Field(alias="timeBasis")
    last_seen_at: datetime | None = Field(alias="lastSeenAt")
    seen_at: datetime | None = Field(alias="seenAt")
    score: int
    selected: bool
    category: str
    category_label: str = Field(alias="categoryLabel")
    tags: list[str]
    reason: str
    url: str | None
    avatar_url: str | None = Field(alias="avatarUrl")
    media_urls: list[str] = Field(alias="mediaUrls")
    evidence_count: int = Field(alias="evidenceCount")
    confidence: int

    model_config = ConfigDict(populate_by_name=True)


class TimelinePageRead(BaseModel):
    items: list[TimelineItemRead]
    total: int
    page: int
    take: int


class DailyArchiveRead(BaseModel):
    date: str
    title: str
    story_count: int = Field(alias="storyCount")
    generated_at: datetime = Field(alias="generatedAt")

    model_config = ConfigDict(populate_by_name=True)


class DailySectionRead(BaseModel):
    key: str
    index: str
    label: str
    english_label: str = Field(alias="englishLabel")
    items: list[TimelineItemRead]

    model_config = ConfigDict(populate_by_name=True)


class DailyDigestRead(BaseModel):
    date: str
    title: str
    generated_at: datetime = Field(alias="generatedAt")
    story_count: int = Field(alias="storyCount")
    sections: list[DailySectionRead]
    markdown: str
    archive: list[DailyArchiveRead]

    model_config = ConfigDict(populate_by_name=True)


class IndustryReportRead(BaseModel):
    domain: str
    label: str
    english_label: str = Field(alias="englishLabel")
    description: str
    title: str
    story_count: int = Field(alias="storyCount")
    latest_date: str | None = Field(alias="latestDate")
    generated_at: datetime | None = Field(alias="generatedAt")
    archive: list[DailyArchiveRead]

    model_config = ConfigDict(populate_by_name=True)


class IndustryDigestRead(BaseModel):
    domain: str
    label: str
    english_label: str = Field(alias="englishLabel")
    description: str
    date: str
    title: str
    generated_at: datetime = Field(alias="generatedAt")
    story_count: int = Field(alias="storyCount")
    sections: list[DailySectionRead]
    markdown: str
    archive: list[DailyArchiveRead]

    model_config = ConfigDict(populate_by_name=True)


@router.get("/items", response_model=TimelinePageRead)
def public_items(
    mode: str = Query(default="selected", pattern="^(selected|all)$"),
    category: str | None = Query(default=None, pattern="^(ai-models|ai-products|industry|paper|tip)$"),
    industry: str | None = Query(default=None, pattern=INDUSTRY_QUERY_PATTERN),
    source_kind: str | None = Query(default=None, alias="sourceKind", pattern="^(first_party|news|social)$"),
    q: str | None = Query(default=None, max_length=200),
    since: datetime | None = None,
    page: int = Query(default=1, ge=1),
    take: int = Query(default=40, ge=1, le=100),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    result = list_public_items(
        db,
        mode=mode,
        category=category,
        industry=industry,
        source_kind=source_kind,
        query=q,
        since=since,
        page=page,
        take=take,
    )
    return {"items": result.items, "total": result.total, "page": result.page, "take": result.take}


@router.get("/dailies", response_model=list[DailyArchiveRead])
def public_dailies(
    take: int = Query(default=30, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    return list_daily_archives(db, take=take)


@router.get("/daily", response_model=DailyDigestRead)
def public_daily(
    target_date: date | None = Query(default=None, alias="date"),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    return get_daily_digest(db, target_date=target_date)


@router.get("/industries", response_model=list[IndustryReportRead])
def public_industries(
    take: int = Query(default=10, ge=1, le=30),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    return list_industry_reports(db, take=take)


@router.get("/industries/{domain}", response_model=IndustryDigestRead)
def public_industry(
    domain: str,
    target_date: date | None = Query(default=None, alias="date"),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    return get_industry_digest(db, domain=domain, target_date=target_date)
