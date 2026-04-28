from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import EventCluster, Evidence, RawItem, Source


@dataclass(frozen=True)
class ScoreRunResult:
    clusters_scored: int


def recompute_hot_scores(db: Session, now: datetime | None = None) -> ScoreRunResult:
    now = now or datetime.now(timezone.utc)
    clusters = db.scalars(select(EventCluster)).all()
    scored_count = 0
    for cluster in clusters:
        evidence_items = list(
            db.scalars(select(Evidence).where(Evidence.event_cluster_id == cluster.id)).all()
        )
        score, reasons = calculate_hot_score(db, cluster, evidence_items, now)
        cluster.hot_score = score
        cluster.score_reason_json = reasons
        db.add(cluster)
        scored_count += 1
    db.commit()
    return ScoreRunResult(clusters_scored=scored_count)


def calculate_hot_score(
    db: Session,
    cluster: EventCluster,
    evidence_items: list[Evidence],
    now: datetime | None = None,
) -> tuple[int, list[dict[str, object]]]:
    now = now or datetime.now(timezone.utc)
    raw_items = _raw_items_for_evidence(db, evidence_items)
    sources = _sources_for_raw_items(db, raw_items)
    last_seen = cluster.last_seen_at or _latest_seen(raw_items)
    recency = _recency_score(last_seen, now)
    source_weight = min(sum(max(source.weight, 0) for source in sources.values()) * 4, 20)
    mention_count = min(len(evidence_items) * 6, 20)
    velocity = _velocity_score(raw_items, now)
    ai_importance = min(max(cluster.confidence, 0) // 7, 15)
    score = min(recency + source_weight + mention_count + velocity + ai_importance, 100)
    reasons = [
        {
            "key": "recency",
            "label": "新鲜度",
            "score": recency,
            "detail": _recency_detail(last_seen, now),
        },
        {
            "key": "sourceWeight",
            "label": "来源权重",
            "score": source_weight,
            "detail": f"{len(sources)} 个来源，权重合计 {sum(source.weight for source in sources.values())}",
        },
        {
            "key": "mentionCount",
            "label": "多源提及",
            "score": mention_count,
            "detail": f"{len(evidence_items)} 条 Evidence",
        },
        {
            "key": "velocity",
            "label": "近期速度",
            "score": velocity,
            "detail": f"{_recent_item_count(raw_items, now)} 条内容出现在最近 24 小时",
        },
        {
            "key": "aiImportance",
            "label": "AI 重要性",
            "score": ai_importance,
            "detail": f"聚类置信度 {cluster.confidence}",
        },
    ]
    return score, reasons


def _raw_items_for_evidence(db: Session, evidence_items: list[Evidence]) -> list[RawItem]:
    raw_items: list[RawItem] = []
    for evidence in evidence_items:
        raw_item = db.get(RawItem, evidence.raw_item_id)
        if raw_item is not None:
            raw_items.append(raw_item)
    return raw_items


def _sources_for_raw_items(db: Session, raw_items: list[RawItem]) -> dict[str, Source]:
    sources: dict[str, Source] = {}
    for raw_item in raw_items:
        source = db.get(Source, raw_item.source_id)
        if source is not None:
            sources[source.id] = source
    return sources


def _latest_seen(raw_items: list[RawItem]) -> datetime | None:
    seen_values = [raw_item.published_at or raw_item.fetched_at for raw_item in raw_items]
    return max(seen_values) if seen_values else None


def _recency_score(last_seen: datetime | None, now: datetime) -> int:
    if last_seen is None:
        return 0
    age = now - _ensure_aware(last_seen)
    if age <= timedelta(hours=6):
        return 30
    if age <= timedelta(hours=24):
        return 24
    if age <= timedelta(days=3):
        return 16
    if age <= timedelta(days=7):
        return 8
    return 2


def _recency_detail(last_seen: datetime | None, now: datetime) -> str:
    if last_seen is None:
        return "缺少 lastSeenAt"
    hours = max(0, int((now - _ensure_aware(last_seen)).total_seconds() // 3600))
    if hours < 1:
        return "最近 1 小时内更新"
    return f"{hours} 小时前更新"


def _velocity_score(raw_items: list[RawItem], now: datetime) -> int:
    return min(_recent_item_count(raw_items, now) * 5, 15)


def _recent_item_count(raw_items: list[RawItem], now: datetime) -> int:
    cutoff = now - timedelta(hours=24)
    return sum(1 for raw_item in raw_items if _ensure_aware(raw_item.published_at or raw_item.fetched_at) >= cutoff)


def _ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value
