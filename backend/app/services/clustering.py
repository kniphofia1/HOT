from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.connectors.utils import stable_hash
from app.db.models import AiRunLog, EventCandidate, EventCluster, Evidence, RawItem, Source
from app.services.ai import (
    AiCandidate,
    AiClusterSummary,
    AiProvider,
    MissingAiConfigurationError,
    build_ai_provider,
)
from app.services.candidates import ensure_missing_event_candidates
from app.services.scoring import calculate_hot_score


@dataclass
class ClusterRunResult:
    candidates_created: int = 0
    clusters_created: int = 0
    clusters_updated: int = 0
    evidence_created: int = 0
    ai_runs_created: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def status(self) -> str:
        return "failed" if self.errors else "success"


def run_event_clustering(
    db: Session,
    ai_provider: AiProvider | None = None,
    limit: int = 100,
) -> ClusterRunResult:
    result = ClusterRunResult()
    result.candidates_created = ensure_missing_event_candidates(db)
    candidates = _load_unclustered_candidates(db, limit)
    buckets = _bucket_candidates(candidates)

    provider_error: Exception | None = None
    if ai_provider is None:
        try:
            ai_provider = build_ai_provider()
        except MissingAiConfigurationError as exc:
            provider_error = exc

    for candidate_hash, bucket_candidates in buckets.items():
        current_bundles = _candidate_bundles(db, bucket_candidates)
        input_hash = stable_hash("cluster", candidate_hash, *(candidate.id for candidate in bucket_candidates))
        token_estimate = _estimate_tokens(current_bundles)
        if provider_error is not None:
            _record_ai_run(
                db,
                input_hash=input_hash,
                model=None,
                status="failed",
                token_estimate=token_estimate,
                error_message=str(provider_error),
            )
            result.ai_runs_created += 1
            result.errors.append(str(provider_error))
            continue

        try:
            existing_cluster = _find_existing_cluster_for_bucket(db, candidate_hash)
            all_bundles = current_bundles
            if existing_cluster is not None:
                all_bundles = _existing_cluster_bundles(db, existing_cluster.id) + current_bundles

            assert ai_provider is not None
            summary = ai_provider.summarize_cluster(all_bundles)
            selected_candidates = _select_candidates(bucket_candidates, summary)
            if not selected_candidates:
                selected_candidates = bucket_candidates

            if existing_cluster is None:
                cluster = _create_cluster(db, summary, selected_candidates)
                result.clusters_created += 1
            else:
                cluster = _update_cluster(db, existing_cluster, summary, selected_candidates)
                result.clusters_updated += 1

            for candidate in selected_candidates:
                if _evidence_exists(db, cluster.id, candidate.raw_item_id):
                    continue
                db.add(_build_evidence(db, cluster.id, candidate, summary.confidence))
                result.evidence_created += 1

            cluster_evidence = list(
                db.scalars(select(Evidence).where(Evidence.event_cluster_id == cluster.id)).all()
            )
            cluster.hot_score, cluster.score_reason_json = calculate_hot_score(db, cluster, cluster_evidence)
            db.add(cluster)

            _record_ai_run(
                db,
                input_hash=input_hash,
                model=ai_provider.model,
                status="success",
                token_estimate=token_estimate,
                error_message=None,
            )
            result.ai_runs_created += 1
        except Exception as exc:  # noqa: BLE001 - per-bucket AI failures must not destroy candidates.
            _record_ai_run(
                db,
                input_hash=input_hash,
                model=getattr(ai_provider, "model", None),
                status="failed",
                token_estimate=token_estimate,
                error_message=str(exc),
            )
            result.ai_runs_created += 1
            result.errors.append(str(exc))

    db.commit()
    return result


def _load_unclustered_candidates(db: Session, limit: int) -> list[EventCandidate]:
    return list(
        db.scalars(
            select(EventCandidate)
            .outerjoin(Evidence, Evidence.raw_item_id == EventCandidate.raw_item_id)
            .where(Evidence.id.is_(None))
            .order_by(EventCandidate.created_at.asc())
            .limit(limit)
        ).all()
    )


def _bucket_candidates(candidates: list[EventCandidate]) -> dict[str, list[EventCandidate]]:
    buckets: dict[str, list[EventCandidate]] = {}
    for candidate in candidates:
        buckets.setdefault(candidate.candidate_hash, []).append(candidate)
    return buckets


def _candidate_bundles(db: Session, candidates: list[EventCandidate]) -> list[AiCandidate]:
    return [_candidate_bundle(db, candidate) for candidate in candidates]


def _candidate_bundle(db: Session, candidate: EventCandidate) -> AiCandidate:
    raw_item = db.get(RawItem, candidate.raw_item_id)
    if raw_item is None:
        raise ValueError(f"RawItem not found for EventCandidate {candidate.id}")
    source = db.get(Source, raw_item.source_id)
    source_name = source.name if source is not None else "Unknown source"
    return AiCandidate(
        id=candidate.id,
        title=raw_item.title,
        content_text=raw_item.content_text,
        source_name=source_name,
        source_url=raw_item.source_url,
    )


def _existing_cluster_bundles(db: Session, cluster_id: str) -> list[AiCandidate]:
    evidence_items = db.scalars(select(Evidence).where(Evidence.event_cluster_id == cluster_id)).all()
    bundles: list[AiCandidate] = []
    for evidence in evidence_items:
        candidate = db.scalar(select(EventCandidate).where(EventCandidate.raw_item_id == evidence.raw_item_id))
        if candidate is not None:
            bundles.append(_candidate_bundle(db, candidate))
    return bundles


def _find_existing_cluster_for_bucket(db: Session, candidate_hash: str) -> EventCluster | None:
    return db.scalar(
        select(EventCluster)
        .join(Evidence, Evidence.event_cluster_id == EventCluster.id)
        .join(EventCandidate, EventCandidate.raw_item_id == Evidence.raw_item_id)
        .where(EventCandidate.candidate_hash == candidate_hash)
        .order_by(EventCluster.created_at.asc())
        .limit(1)
    )


def _select_candidates(
    candidates: list[EventCandidate],
    summary: AiClusterSummary,
) -> list[EventCandidate]:
    selected_ids = set(summary.candidate_ids)
    if not selected_ids:
        return candidates
    return [candidate for candidate in candidates if candidate.id in selected_ids]


def _create_cluster(
    db: Session,
    summary: AiClusterSummary,
    candidates: list[EventCandidate],
) -> EventCluster:
    first_seen, last_seen = _candidate_seen_window(db, candidates)
    cluster = EventCluster(
        title=summary.title,
        summary=summary.summary,
        hot_score=0,
        score_reason_json=[],
        confidence=summary.confidence,
        first_seen_at=first_seen,
        last_seen_at=last_seen,
    )
    db.add(cluster)
    db.flush()
    return cluster


def _update_cluster(
    db: Session,
    cluster: EventCluster,
    summary: AiClusterSummary,
    candidates: list[EventCandidate],
) -> EventCluster:
    first_seen, last_seen = _candidate_seen_window(db, candidates)
    cluster.title = summary.title
    cluster.summary = summary.summary
    cluster.confidence = summary.confidence
    if first_seen is not None and (cluster.first_seen_at is None or first_seen < cluster.first_seen_at):
        cluster.first_seen_at = first_seen
    if last_seen is not None and (cluster.last_seen_at is None or last_seen > cluster.last_seen_at):
        cluster.last_seen_at = last_seen
    db.add(cluster)
    db.flush()
    return cluster


def _candidate_seen_window(
    db: Session,
    candidates: list[EventCandidate],
) -> tuple[datetime | None, datetime | None]:
    seen_values: list[datetime] = []
    for candidate in candidates:
        raw_item = db.get(RawItem, candidate.raw_item_id)
        if raw_item is None:
            continue
        seen_values.append(raw_item.published_at or raw_item.fetched_at)
    if not seen_values:
        return None, None
    return min(seen_values), max(seen_values)


def _build_evidence(
    db: Session,
    cluster_id: str,
    candidate: EventCandidate,
    confidence: int,
) -> Evidence:
    raw_item = db.get(RawItem, candidate.raw_item_id)
    if raw_item is None:
        raise ValueError(f"RawItem not found for EventCandidate {candidate.id}")
    source = db.get(Source, raw_item.source_id)
    quote = _quote_for_raw_item(raw_item)
    return Evidence(
        event_cluster_id=cluster_id,
        raw_item_id=raw_item.id,
        source_name=source.name if source is not None else "Unknown source",
        source_url=raw_item.source_url or (source.url if source is not None else ""),
        quote=quote,
        confidence=confidence,
    )


def _evidence_exists(db: Session, cluster_id: str, raw_item_id: str) -> bool:
    return (
        db.scalar(
            select(Evidence.id)
            .where(Evidence.event_cluster_id == cluster_id)
            .where(Evidence.raw_item_id == raw_item_id)
            .limit(1)
        )
        is not None
    )


def _quote_for_raw_item(raw_item: RawItem) -> str:
    text = (raw_item.content_text or raw_item.title).strip()
    return text[:240]


def _record_ai_run(
    db: Session,
    *,
    input_hash: str,
    model: str | None,
    status: str,
    token_estimate: int,
    error_message: str | None,
) -> None:
    db.add(
        AiRunLog(
            task_type="event_clustering",
            input_hash=input_hash,
            model=model,
            status=status,
            token_estimate=token_estimate,
            error_message=error_message,
        )
    )


def _estimate_tokens(candidates: list[AiCandidate]) -> int:
    total_chars = 0
    for candidate in candidates:
        total_chars += len(candidate.title)
        total_chars += len(candidate.content_text or "")
    return max(1, total_chars // 4)
