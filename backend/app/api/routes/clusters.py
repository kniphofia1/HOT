from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import EventCluster, Evidence, RawItem, Source
from app.db.session import get_db
from app.services.clustering import ClusterRunResult, run_event_clustering
from app.services.editorial import EditorialRunResult, edit_event_cluster, edit_event_clusters
from app.services.industry_classifier import IndustryClassificationRunResult, classify_event_clusters
from app.services.radar_refresh import RadarRefreshResult, refresh_all_sources
from app.services.scoring import ScoreRunResult, recompute_hot_scores
from app.services.translation import TranslationRunResult, translate_event_cluster, translate_event_clusters


router = APIRouter(prefix="/api/clusters", tags=["clusters"])


class ClusterRunRead(BaseModel):
    status: str
    candidates_created: int = Field(alias="candidatesCreated")
    clusters_created: int = Field(alias="clustersCreated")
    clusters_updated: int = Field(alias="clustersUpdated")
    evidence_created: int = Field(alias="evidenceCreated")
    ai_runs_created: int = Field(alias="aiRunsCreated")
    errors: list[str]

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class EventClusterRead(BaseModel):
    id: str
    title: str
    summary: str | None
    translated_title: str | None = Field(alias="translatedTitle")
    translated_summary: str | None = Field(alias="translatedSummary")
    translated_at: datetime | None = Field(alias="translatedAt")
    editorial_title: str | None = Field(alias="editorialTitle")
    editorial_summary: str | None = Field(alias="editorialSummary")
    editorial_category: str | None = Field(alias="editorialCategory")
    editorial_tags_json: list[str] = Field(alias="editorialTagsJson")
    editorial_priority: int = Field(alias="editorialPriority")
    editorial_at: datetime | None = Field(alias="editorialAt")
    display_title: str = Field(alias="displayTitle")
    display_summary: str | None = Field(alias="displaySummary")
    hot_score: int = Field(alias="hotScore")
    score_reason_json: list = Field(alias="scoreReasonJson")
    confidence: int
    event_phase: str | None = Field(alias="eventPhase")
    credibility_score: int = Field(alias="credibilityScore")
    propagation_score: int = Field(alias="propagationScore")
    primary_industry: str | None = Field(alias="primaryIndustry")
    related_industries_json: list[str] = Field(alias="relatedIndustriesJson")
    industry_confidence: int = Field(alias="industryConfidence")
    industry_reason: str | None = Field(alias="industryReason")
    industry_classified_at: datetime | None = Field(alias="industryClassifiedAt")
    impact_domains_json: list[str] = Field(alias="impactDomainsJson")
    entities_json: list[str] = Field(alias="entitiesJson")
    historical_matches_json: list = Field(alias="historicalMatchesJson")
    intelligence_reason_json: list = Field(alias="intelligenceReasonJson")
    first_seen_at: datetime | None = Field(alias="firstSeenAt")
    last_seen_at: datetime | None = Field(alias="lastSeenAt")
    evidence_count: int = Field(alias="evidenceCount")
    source_names: list[str] = Field(alias="sourceNames")
    source_types: list[str] = Field(alias="sourceTypes")
    primary_source_name: str | None = Field(alias="primarySourceName")
    primary_source_type: str | None = Field(alias="primarySourceType")
    other_source_type_count: int = Field(alias="otherSourceTypeCount")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class EvidenceRead(BaseModel):
    id: str
    raw_item_id: str = Field(alias="rawItemId")
    source_name: str = Field(alias="sourceName")
    source_url: str = Field(alias="sourceUrl")
    quote: str | None
    confidence: int
    raw_title: str = Field(alias="rawTitle")
    raw_content_text: str | None = Field(alias="rawContentText")
    raw_published_at: datetime | None = Field(alias="rawPublishedAt")
    raw_fetched_at: datetime = Field(alias="rawFetchedAt")

    model_config = ConfigDict(populate_by_name=True)


class EventClusterDetailRead(EventClusterRead):
    evidence: list[EvidenceRead]


class ScoreRunRead(BaseModel):
    clusters_scored: int = Field(alias="clustersScored")

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


class EditorialRunRead(BaseModel):
    status: str
    clusters_edited: int = Field(alias="clustersEdited")
    clusters_skipped: int = Field(alias="clustersSkipped")
    ai_runs_created: int = Field(alias="aiRunsCreated")
    errors: list[str]

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class FetchRunSummaryRead(BaseModel):
    status: str
    items_found: int = Field(alias="itemsFound")
    items_created: int = Field(alias="itemsCreated")
    error_message: str | None = Field(alias="errorMessage")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class FullRefreshRead(BaseModel):
    status: str
    fetch_runs: list[FetchRunSummaryRead] = Field(alias="fetchRuns")
    clustering: ClusterRunRead
    classification: IndustryClassificationRunRead
    translation: TranslationRunRead
    editorial: EditorialRunRead
    scoring: ScoreRunRead
    errors: list[str]

    model_config = ConfigDict(populate_by_name=True)


@router.post("/run", response_model=ClusterRunRead)
def run_clustering(limit: int = 100, db: Session = Depends(get_db)) -> ClusterRunResult:
    return run_event_clustering(db, limit=limit)


@router.post("/score", response_model=ScoreRunRead)
def score_clusters(db: Session = Depends(get_db)) -> ScoreRunResult:
    return recompute_hot_scores(db)


@router.post("/classify", response_model=IndustryClassificationRunRead)
def classify_clusters(
    force: bool = False,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> IndustryClassificationRunResult:
    return classify_event_clusters(db, force=force, limit=limit)


@router.post("/editorial", response_model=EditorialRunRead)
def edit_clusters(
    force: bool = False,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> EditorialRunResult:
    return edit_event_clusters(db, force=force, limit=limit)


@router.post("/refresh", response_model=FullRefreshRead)
def refresh_radar(
    cluster_limit: int = Query(default=100, ge=1, le=500, alias="clusterLimit"),
    editorial_limit: int = Query(default=100, ge=1, le=500, alias="editorialLimit"),
    db: Session = Depends(get_db),
) -> RadarRefreshResult:
    return refresh_all_sources(db, cluster_limit=cluster_limit, editorial_limit=editorial_limit)


@router.post("/translate", response_model=TranslationRunRead)
def translate_clusters(
    force: bool = False,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> TranslationRunResult:
    return translate_event_clusters(db, force=force, limit=limit)


@router.get("", response_model=list[EventClusterRead])
def list_clusters(
    hours: int | None = Query(default=None, ge=1),
    source_id: str | None = Query(default=None, alias="sourceId"),
    source_type: str | None = Query(default=None, alias="sourceType"),
    editorial_category: str | None = Query(default=None, alias="editorialCategory"),
    min_score: int | None = Query(default=None, ge=0, le=100, alias="minScore"),
    sort: str = Query(default="editorial", pattern="^(editorial|score|time)$"),
    db: Session = Depends(get_db),
) -> list[dict]:
    clusters = list(db.scalars(select(EventCluster)).all())
    if min_score is not None:
        clusters = [cluster for cluster in clusters if cluster.hot_score >= min_score]
    if editorial_category:
        clusters = [cluster for cluster in clusters if cluster.editorial_category == editorial_category]
    if hours is not None:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        clusters = [
            cluster
            for cluster in clusters
            if cluster.last_seen_at is not None and _ensure_aware(cluster.last_seen_at) >= cutoff
        ]
    if source_id is not None or source_type is not None:
        clusters = [
            cluster
            for cluster in clusters
            if _cluster_has_source(db, cluster.id, source_id=source_id, source_type=source_type)
        ]
    clusters = _sort_clusters(clusters, sort)
    return [_cluster_read(db, cluster) for cluster in clusters]


@router.post("/{cluster_id}/translate", response_model=TranslationRunRead)
def translate_cluster(
    cluster_id: str,
    force: bool = False,
    db: Session = Depends(get_db),
) -> TranslationRunResult:
    cluster = db.get(EventCluster, cluster_id)
    if cluster is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="EventCluster not found")
    return translate_event_cluster(db, cluster, force=force)


@router.post("/{cluster_id}/editorial", response_model=EditorialRunRead)
def edit_single_cluster(
    cluster_id: str,
    force: bool = False,
    db: Session = Depends(get_db),
) -> EditorialRunResult:
    cluster = db.get(EventCluster, cluster_id)
    if cluster is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="EventCluster not found")
    return edit_event_cluster(db, cluster, force=force)


@router.get("/{cluster_id}", response_model=EventClusterDetailRead)
def get_cluster(cluster_id: str, db: Session = Depends(get_db)) -> dict:
    cluster = db.get(EventCluster, cluster_id)
    if cluster is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="EventCluster not found")

    evidence_rows = db.execute(
        select(Evidence, RawItem)
        .join(RawItem, RawItem.id == Evidence.raw_item_id)
        .where(Evidence.event_cluster_id == cluster_id)
        .order_by(Evidence.id.asc())
    ).all()
    payload = _cluster_read(db, cluster)
    payload["evidence"] = [
        {
            "id": evidence.id,
            "rawItemId": evidence.raw_item_id,
            "sourceName": evidence.source_name,
            "sourceUrl": evidence.source_url,
            "quote": evidence.quote,
            "confidence": evidence.confidence,
            "rawTitle": raw_item.title,
            "rawContentText": raw_item.content_text,
            "rawPublishedAt": raw_item.published_at,
            "rawFetchedAt": raw_item.fetched_at,
        }
        for evidence, raw_item in evidence_rows
    ]
    return payload


def _cluster_read(db: Session, cluster: EventCluster) -> dict:
    source_rows = db.execute(
        select(Source.name, Source.type, Source.weight, RawItem.published_at, RawItem.fetched_at)
        .join(RawItem, RawItem.source_id == Source.id)
        .join(Evidence, Evidence.raw_item_id == RawItem.id)
        .where(Evidence.event_cluster_id == cluster.id)
    ).all()
    source_names = sorted({name for name, _, _, _, _ in source_rows})
    source_types = sorted({source_type for _, source_type, _, _, _ in source_rows})
    primary_source = _primary_source(source_rows)
    primary_source_name = primary_source[0] if primary_source is not None else None
    primary_source_type = primary_source[1] if primary_source is not None else None
    other_source_type_count = len(
        {source_type for source_type in source_types if source_type != primary_source_type}
    )
    evidence_count = db.scalar(
        select(func.count(Evidence.id)).where(Evidence.event_cluster_id == cluster.id)
    )
    return {
        "id": cluster.id,
        "title": cluster.title,
        "summary": cluster.summary,
        "translatedTitle": cluster.translated_title,
        "translatedSummary": cluster.translated_summary,
        "translatedAt": cluster.translated_at,
        "editorialTitle": cluster.editorial_title,
        "editorialSummary": cluster.editorial_summary,
        "editorialCategory": cluster.editorial_category,
        "editorialTagsJson": cluster.editorial_tags_json,
        "editorialPriority": cluster.editorial_priority,
        "editorialAt": cluster.editorial_at,
        "displayTitle": cluster.editorial_title or cluster.translated_title or cluster.title,
        "displaySummary": cluster.editorial_summary or cluster.translated_summary or cluster.summary,
        "hotScore": cluster.hot_score,
        "scoreReasonJson": cluster.score_reason_json,
        "confidence": cluster.confidence,
        "eventPhase": cluster.event_phase,
        "credibilityScore": cluster.credibility_score,
        "propagationScore": cluster.propagation_score,
        "primaryIndustry": cluster.primary_industry,
        "relatedIndustriesJson": cluster.related_industries_json,
        "industryConfidence": cluster.industry_confidence,
        "industryReason": cluster.industry_reason,
        "industryClassifiedAt": cluster.industry_classified_at,
        "impactDomainsJson": cluster.impact_domains_json,
        "entitiesJson": cluster.entities_json,
        "historicalMatchesJson": cluster.historical_matches_json,
        "intelligenceReasonJson": cluster.intelligence_reason_json,
        "firstSeenAt": cluster.first_seen_at,
        "lastSeenAt": cluster.last_seen_at,
        "evidenceCount": evidence_count or 0,
        "sourceNames": source_names,
        "sourceTypes": source_types,
        "primarySourceName": primary_source_name,
        "primarySourceType": primary_source_type,
        "otherSourceTypeCount": other_source_type_count,
    }


def _primary_source(source_rows: list) -> tuple[str, str] | None:
    if not source_rows:
        return None

    def sort_key(row: tuple) -> tuple[int, float, str]:
        name, _, weight, published_at, fetched_at = row
        seen_at = published_at or fetched_at
        timestamp = _ensure_aware(seen_at).timestamp() if seen_at is not None else 0.0
        return (-(weight or 0), -timestamp, name)

    name, source_type, _, _, _ = sorted(source_rows, key=sort_key)[0]
    return name, source_type


def _cluster_has_source(
    db: Session,
    cluster_id: str,
    *,
    source_id: str | None,
    source_type: str | None,
) -> bool:
    query = (
        select(Source.id)
        .join(RawItem, RawItem.source_id == Source.id)
        .join(Evidence, Evidence.raw_item_id == RawItem.id)
        .where(Evidence.event_cluster_id == cluster_id)
    )
    if source_id is not None:
        query = query.where(Source.id == source_id)
    if source_type is not None:
        query = query.where(Source.type == source_type)
    return db.scalar(query.limit(1)) is not None


def _sort_clusters(clusters: list[EventCluster], sort: str) -> list[EventCluster]:
    if sort == "time":
        return sorted(
            clusters,
            key=lambda cluster: _ensure_aware(cluster.last_seen_at or cluster.created_at),
            reverse=True,
        )
    return sorted(
        clusters,
        key=lambda cluster: (
            cluster.hot_score,
            _ensure_aware(cluster.last_seen_at or cluster.created_at),
        ),
        reverse=True,
    )


def _ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value
