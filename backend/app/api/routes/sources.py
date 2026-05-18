import os
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import FetchRun, RawItem, Source
from app.db.session import get_db
from app.services.clustering import run_event_clustering
from app.services.connector_runner import run_source_fetch
from app.services.default_sources import ensure_default_sources
from app.services.editorial import edit_event_clusters
from app.services.industry_classifier import classify_event_clusters
from app.services.industry_taxonomy import industry_values_from_config, normalize_industry_key
from app.services.radar_refresh import RadarRefreshResult, refresh_all_sources, refresh_single_source
from app.services.scoring import recompute_hot_scores
from app.services.translation import translate_event_clusters


router = APIRouter(prefix="/api/sources", tags=["sources"])


class SourceBase(BaseModel):
    type: str
    name: str
    url: str | None = None
    enabled: bool = True
    weight: int = 1
    poll_interval_minutes: int = Field(default=60, alias="pollIntervalMinutes")
    config_json: dict[str, Any] = Field(default_factory=dict, alias="configJson")

    model_config = ConfigDict(populate_by_name=True)


class SourceCreate(SourceBase):
    pass


class SourceUpdate(BaseModel):
    type: str | None = None
    name: str | None = None
    url: str | None = None
    enabled: bool | None = None
    weight: int | None = None
    poll_interval_minutes: int | None = Field(default=None, alias="pollIntervalMinutes")
    config_json: dict[str, Any] | None = Field(default=None, alias="configJson")
    last_error: str | None = Field(default=None, alias="lastError")

    model_config = ConfigDict(populate_by_name=True)


class SourceRead(BaseModel):
    id: str
    type: str
    name: str
    url: str | None
    enabled: bool
    weight: int
    poll_interval_minutes: int = Field(alias="pollIntervalMinutes")
    config_json: dict[str, Any] = Field(alias="configJson")
    last_fetched_at: datetime | None = Field(alias="lastFetchedAt")
    latest_published_at: datetime | None = Field(default=None, alias="latestPublishedAt")
    last_error: str | None = Field(alias="lastError")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class FetchRunRead(BaseModel):
    id: str
    source_id: str = Field(alias="sourceId")
    status: str
    items_found: int = Field(alias="itemsFound")
    items_created: int = Field(alias="itemsCreated")
    error_message: str | None = Field(alias="errorMessage")
    rate_limit_remaining: int | None = Field(alias="rateLimitRemaining")
    cost_estimate: int | None = Field(alias="costEstimate")
    started_at: datetime = Field(alias="startedAt")
    finished_at: datetime | None = Field(alias="finishedAt")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ClusterRunRead(BaseModel):
    status: str
    candidates_created: int = Field(alias="candidatesCreated")
    clusters_created: int = Field(alias="clustersCreated")
    clusters_updated: int = Field(alias="clustersUpdated")
    evidence_created: int = Field(alias="evidenceCreated")
    ai_runs_created: int = Field(alias="aiRunsCreated")
    errors: list[str]

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class EditorialRunRead(BaseModel):
    status: str
    clusters_edited: int = Field(alias="clustersEdited")
    clusters_skipped: int = Field(alias="clustersSkipped")
    ai_runs_created: int = Field(alias="aiRunsCreated")
    errors: list[str]

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class TranslationRunRead(BaseModel):
    status: str
    clusters_translated: int = Field(alias="clustersTranslated")
    clusters_skipped: int = Field(alias="clustersSkipped")
    ai_runs_created: int = Field(alias="aiRunsCreated")
    errors: list[str]

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class IndustryClassificationRunRead(BaseModel):
    status: str
    clusters_classified: int = Field(alias="clustersClassified")
    clusters_skipped: int = Field(alias="clustersSkipped")
    ai_runs_created: int = Field(alias="aiRunsCreated")
    errors: list[str]

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ScoreRunRead(BaseModel):
    clusters_scored: int = Field(alias="clustersScored")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class SourceRefreshRead(BaseModel):
    status: str
    fetch_runs: list[FetchRunRead] = Field(alias="fetchRuns")
    clustering: ClusterRunRead
    classification: IndustryClassificationRunRead
    translation: TranslationRunRead
    editorial: EditorialRunRead
    scoring: ScoreRunRead
    errors: list[str]

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class RetryFailedSourcesCreate(BaseModel):
    industry: str | None = None
    include_credentialed: bool = Field(default=False, alias="includeCredentialed")
    run_pipeline: bool = Field(default=True, alias="runPipeline")
    limit: int = Field(default=5, ge=1, le=50)

    model_config = ConfigDict(populate_by_name=True)


class RetrySkippedSourceRead(BaseModel):
    source_id: str = Field(alias="sourceId")
    name: str
    type: str
    reason: str

    model_config = ConfigDict(populate_by_name=True)


class RetryFailedSourcesRead(BaseModel):
    requested_industry: str | None = Field(alias="requestedIndustry")
    attempted_count: int = Field(alias="attemptedCount")
    skipped_count: int = Field(alias="skippedCount")
    success_count: int = Field(alias="successCount")
    failed_count: int = Field(alias="failedCount")
    fetch_runs: list[FetchRunRead] = Field(alias="fetchRuns")
    skipped_sources: list[RetrySkippedSourceRead] = Field(alias="skippedSources")
    clustering: ClusterRunRead | None = None
    classification: IndustryClassificationRunRead | None = None
    translation: TranslationRunRead | None = None
    editorial: EditorialRunRead | None = None
    scoring: ScoreRunRead | None = None
    errors: list[str]

    model_config = ConfigDict(populate_by_name=True)


@router.get("", response_model=list[SourceRead])
def list_sources(db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    return [_source_read(db, source) for source in db.scalars(select(Source).order_by(Source.created_at.desc())).all()]


@router.post("", response_model=SourceRead, status_code=status.HTTP_201_CREATED)
def create_source(payload: SourceCreate, db: Session = Depends(get_db)) -> dict[str, Any]:
    source = Source(
        type=payload.type,
        name=payload.name,
        url=payload.url,
        enabled=payload.enabled,
        weight=payload.weight,
        poll_interval_minutes=payload.poll_interval_minutes,
        config_json=payload.config_json,
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return _source_read(db, source)


@router.post("/refresh", response_model=SourceRefreshRead)
def refresh_enabled_sources(db: Session = Depends(get_db)) -> RadarRefreshResult:
    return refresh_all_sources(db)


@router.post("/defaults", response_model=list[SourceRead])
def configure_default_sources(db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    return [_source_read(db, source) for source in ensure_default_sources(db)]


@router.post("/retry-failed", response_model=RetryFailedSourcesRead)
def retry_failed_sources(
    payload: RetryFailedSourcesCreate,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    sources = [
        source
        for source in db.scalars(select(Source).where(Source.enabled.is_(True))).all()
        if source.last_error and _source_matches_retry_industry(source, payload.industry)
    ][: payload.limit]
    skipped_sources: list[dict[str, str]] = []
    retry_sources: list[Source] = []
    for source in sources:
        skip_reason = _credential_skip_reason(source) if not payload.include_credentialed else None
        if skip_reason:
            skipped_sources.append(
                {"sourceId": source.id, "name": source.name, "type": source.type, "reason": skip_reason}
            )
            continue
        retry_sources.append(source)

    fetch_runs: list[FetchRun] = []
    retry_errors: list[str] = []
    for source in retry_sources:
        try:
            fetch_runs.append(run_source_fetch(db, source))
        except Exception as exc:  # noqa: BLE001 - a retry batch should expose per-source failures instead of returning 500.
            db.rollback()
            retry_errors.append(f"{source.name}: {exc}")
    clustering = classification = translation = editorial = scoring = None
    errors = [*retry_errors, *[run.error_message for run in fetch_runs if run.error_message]]
    if payload.run_pipeline and fetch_runs:
        clustering = run_event_clustering(db, limit=100)
        classification = classify_event_clusters(db, limit=100)
        translation = translate_event_clusters(db, limit=100)
        editorial = edit_event_clusters(db, limit=100)
        scoring = recompute_hot_scores(db)
        errors.extend(clustering.errors)
        errors.extend(classification.errors)
        errors.extend(translation.errors)
        errors.extend(editorial.errors)

    return {
        "requestedIndustry": payload.industry,
        "attemptedCount": len(fetch_runs),
        "skippedCount": len(skipped_sources),
        "successCount": sum(1 for run in fetch_runs if run.status == "success"),
        "failedCount": sum(1 for run in fetch_runs if run.status == "failed"),
        "fetchRuns": fetch_runs,
        "skippedSources": skipped_sources,
        "clustering": clustering,
        "classification": classification,
        "translation": translation,
        "editorial": editorial,
        "scoring": scoring,
        "errors": errors,
    }


@router.get("/{source_id}", response_model=SourceRead)
def get_source(source_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    source = db.get(Source, source_id)
    if source is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")
    return _source_read(db, source)


@router.patch("/{source_id}", response_model=SourceRead)
def update_source(source_id: str, payload: SourceUpdate, db: Session = Depends(get_db)) -> dict[str, Any]:
    source = db.get(Source, source_id)
    if source is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")

    updates = payload.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(source, key, value)

    db.add(source)
    db.commit()
    db.refresh(source)
    return _source_read(db, source)


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_source(source_id: str, db: Session = Depends(get_db)) -> Response:
    source = db.get(Source, source_id)
    if source is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")

    db.delete(source)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{source_id}/refresh", response_model=SourceRefreshRead)
def refresh_source(source_id: str, db: Session = Depends(get_db)) -> RadarRefreshResult:
    source = db.get(Source, source_id)
    if source is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")
    return refresh_single_source(db, source)


def _source_read(db: Session, source: Source) -> dict[str, Any]:
    latest_published_at = db.scalar(
        select(func.max(RawItem.published_at)).where(RawItem.source_id == source.id)
    )
    return {
        "id": source.id,
        "type": source.type,
        "name": source.name,
        "url": source.url,
        "enabled": source.enabled,
        "weight": source.weight,
        "pollIntervalMinutes": source.poll_interval_minutes,
        "configJson": source.config_json,
        "lastFetchedAt": _ensure_aware_or_none(source.last_fetched_at),
        "latestPublishedAt": _ensure_aware_or_none(latest_published_at),
        "lastError": source.last_error,
        "createdAt": source.created_at,
        "updatedAt": source.updated_at,
    }


def _ensure_aware_or_none(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _source_matches_retry_industry(source: Source, industry: str | None) -> bool:
    if not industry or industry == "all":
        return True
    industry = normalize_industry_key(industry) or industry
    return industry in industry_values_from_config(source.config_json)


def _credential_skip_reason(source: Source) -> str | None:
    config = source.config_json or {}
    if not config.get("requiresCredential"):
        return None
    for key in ("bearerTokenEnv", "apiKeyEnv", "accessTokenEnv", "botTokenEnv"):
        env_name = config.get(key)
        if isinstance(env_name, str) and env_name and os.getenv(env_name):
            return None
    return "missing credential"
