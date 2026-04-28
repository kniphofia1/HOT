from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import EventCluster, Evidence, RawItem
from app.db.session import get_db
from app.services.clustering import ClusterRunResult, run_event_clustering


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


@router.post("/run", response_model=ClusterRunRead)
def run_clustering(limit: int = 100, db: Session = Depends(get_db)) -> ClusterRunResult:
    return run_event_clustering(db, limit=limit)


@router.get("", response_model=list[EventClusterRead])
def list_clusters(db: Session = Depends(get_db)) -> list[dict]:
    rows = db.execute(
        select(EventCluster, func.count(Evidence.id).label("evidence_count"))
        .outerjoin(Evidence, Evidence.event_cluster_id == EventCluster.id)
        .group_by(EventCluster.id)
        .order_by(EventCluster.last_seen_at.desc().nullslast(), EventCluster.created_at.desc())
    ).all()
    return [_cluster_read(cluster, evidence_count) for cluster, evidence_count in rows]


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
    payload = _cluster_read(cluster, len(evidence_rows))
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


def _cluster_read(cluster: EventCluster, evidence_count: int) -> dict:
    return {
        "id": cluster.id,
        "title": cluster.title,
        "summary": cluster.summary,
        "hotScore": cluster.hot_score,
        "scoreReasonJson": cluster.score_reason_json,
        "confidence": cluster.confidence,
        "firstSeenAt": cluster.first_seen_at,
        "lastSeenAt": cluster.last_seen_at,
        "evidenceCount": evidence_count,
    }
