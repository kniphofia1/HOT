from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import EventCluster, Evidence, RawItem, Source
from app.db.session import get_db
from app.services.clustering import ClusterRunResult, run_event_clustering
from app.services.scoring import ScoreRunResult, recompute_hot_scores


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
    hot_score: int = Field(alias="hotScore")
    score_reason_json: list = Field(alias="scoreReasonJson")
    confidence: int
    first_seen_at: datetime | None = Field(alias="firstSeenAt")
    last_seen_at: datetime | None = Field(alias="lastSeenAt")
    evidence_count: int = Field(alias="evidenceCount")
    source_names: list[str] = Field(alias="sourceNames")
    source_types: list[str] = Field(alias="sourceTypes")

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

    model_config = ConfigDict(populate_by_name=True)


class EventClusterDetailRead(EventClusterRead):
    evidence: list[EvidenceRead]


class ScoreRunRead(BaseModel):
    clusters_scored: int = Field(alias="clustersScored")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


@router.post("/run", response_model=ClusterRunRead)
def run_clustering(limit: int = 100, db: Session = Depends(get_db)) -> ClusterRunResult:
    return run_event_clustering(db, limit=limit)


@router.post("/score", response_model=ScoreRunRead)
def score_clusters(db: Session = Depends(get_db)) -> ScoreRunResult:
    return recompute_hot_scores(db)


@router.get("", response_model=list[EventClusterRead])
def list_clusters(
    hours: int | None = Query(default=None, ge=1),
    source_id: str | None = Query(default=None, alias="sourceId"),
    source_type: str | None = Query(default=None, alias="sourceType"),
    min_score: int | None = Query(default=None, ge=0, le=100, alias="minScore"),
    sort: str = Query(default="score", pattern="^(score|time)$"),
    db: Session = Depends(get_db),
) -> list[dict]:
    clusters = list(db.scalars(select(EventCluster)).all())
    if min_score is not None:
        clusters = [cluster for cluster in clusters if cluster.hot_score >= min_score]
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
        }
        for evidence, raw_item in evidence_rows
    ]
    return payload


def _cluster_read(db: Session, cluster: EventCluster) -> dict:
    source_rows = db.execute(
        select(Source.name, Source.type)
        .join(RawItem, RawItem.source_id == Source.id)
        .join(Evidence, Evidence.raw_item_id == RawItem.id)
        .where(Evidence.event_cluster_id == cluster.id)
    ).all()
    source_names = sorted({name for name, _ in source_rows})
    source_types = sorted({source_type for _, source_type in source_rows})
    evidence_count = db.scalar(
        select(func.count(Evidence.id)).where(Evidence.event_cluster_id == cluster.id)
    )
    return {
        "id": cluster.id,
        "title": cluster.title,
        "summary": cluster.summary,
        "hotScore": cluster.hot_score,
        "scoreReasonJson": cluster.score_reason_json,
        "confidence": cluster.confidence,
        "firstSeenAt": cluster.first_seen_at,
        "lastSeenAt": cluster.last_seen_at,
        "evidenceCount": evidence_count or 0,
        "sourceNames": source_names,
        "sourceTypes": source_types,
    }


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
