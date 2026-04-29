from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.connectors.utils import stable_hash
from app.db.models import AiRunLog, EventCluster, Evidence, RawItem, Source, utc_now
from app.services.ai import AiProvider, MissingAiConfigurationError, build_ai_provider


EDITORIAL_CATEGORIES = {
    "ai_big_news",
    "commercial_value",
    "watchlist_update",
    "tech_project",
    "other",
}


@dataclass
class EditorialRunResult:
    clusters_edited: int = 0
    clusters_skipped: int = 0
    ai_runs_created: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def status(self) -> str:
        if self.errors and self.clusters_edited:
            return "partial"
        if self.errors:
            return "failed"
        return "success"


def edit_event_clusters(
    db: Session,
    *,
    ai_provider: AiProvider | None = None,
    force: bool = False,
    limit: int = 100,
) -> EditorialRunResult:
    result = EditorialRunResult()
    clusters = _load_editorial_targets(db, force=force, limit=limit)
    if not clusters:
        return result

    provider_error: Exception | None = None
    if ai_provider is None:
        try:
            ai_provider = build_ai_provider()
        except MissingAiConfigurationError as exc:
            provider_error = exc

    for cluster in clusters:
        if _has_editorial(cluster) and not force:
            result.clusters_skipped += 1
            continue

        context = _editorial_context(db, cluster)
        input_hash = _editorial_input_hash(cluster, context)
        token_estimate = _estimate_tokens(cluster, context)
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
            assert ai_provider is not None
            edited = ai_provider.edit_event(
                title=cluster.title,
                summary=cluster.summary,
                source_names=context.source_names,
                source_types=context.source_types,
                source_weight=context.source_weight,
                evidence_count=context.evidence_count,
            )
            cluster.editorial_title = edited.title
            cluster.editorial_summary = edited.summary
            cluster.editorial_category = _safe_category(edited.category)
            cluster.editorial_tags_json = _safe_tags(edited.tags, context)
            cluster.editorial_priority = _safe_priority(edited.priority, context)
            cluster.editorial_at = utc_now()
            db.add(cluster)
            _record_ai_run(
                db,
                input_hash=input_hash,
                model=ai_provider.model,
                status="success",
                token_estimate=token_estimate,
                error_message=None,
            )
            result.clusters_edited += 1
            result.ai_runs_created += 1
        except Exception as exc:  # noqa: BLE001 - editorial output is best-effort per event.
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


def edit_event_cluster(
    db: Session,
    cluster: EventCluster,
    *,
    ai_provider: AiProvider | None = None,
    force: bool = False,
) -> EditorialRunResult:
    if _has_editorial(cluster) and not force:
        return EditorialRunResult(clusters_skipped=1)

    result = EditorialRunResult()
    context = _editorial_context(db, cluster)
    input_hash = _editorial_input_hash(cluster, context)
    token_estimate = _estimate_tokens(cluster, context)
    provider = ai_provider
    provider_error: Exception | None = None
    if provider is None:
        try:
            provider = build_ai_provider()
        except MissingAiConfigurationError as exc:
            provider_error = exc

    if provider_error is not None:
        _record_ai_run(
            db,
            input_hash=input_hash,
            model=None,
            status="failed",
            token_estimate=token_estimate,
            error_message=str(provider_error),
        )
        result.ai_runs_created = 1
        result.errors.append(str(provider_error))
        db.commit()
        return result

    try:
        assert provider is not None
        edited = provider.edit_event(
            title=cluster.title,
            summary=cluster.summary,
            source_names=context.source_names,
            source_types=context.source_types,
            source_weight=context.source_weight,
            evidence_count=context.evidence_count,
        )
        cluster.editorial_title = edited.title
        cluster.editorial_summary = edited.summary
        cluster.editorial_category = _safe_category(edited.category)
        cluster.editorial_tags_json = _safe_tags(edited.tags, context)
        cluster.editorial_priority = _safe_priority(edited.priority, context)
        cluster.editorial_at = utc_now()
        db.add(cluster)
        _record_ai_run(
            db,
            input_hash=input_hash,
            model=provider.model,
            status="success",
            token_estimate=token_estimate,
            error_message=None,
        )
        result.clusters_edited = 1
        result.ai_runs_created = 1
    except Exception as exc:  # noqa: BLE001 - preserve existing display and log the failure.
        _record_ai_run(
            db,
            input_hash=input_hash,
            model=getattr(provider, "model", None),
            status="failed",
            token_estimate=token_estimate,
            error_message=str(exc),
        )
        result.ai_runs_created = 1
        result.errors.append(str(exc))

    db.commit()
    return result


@dataclass(frozen=True)
class EditorialContext:
    source_names: list[str]
    source_types: list[str]
    source_weight: int
    evidence_count: int


def _load_editorial_targets(db: Session, *, force: bool, limit: int) -> list[EventCluster]:
    clusters = list(db.scalars(select(EventCluster)).all())
    if not force:
        clusters = [cluster for cluster in clusters if not _has_editorial(cluster)]
    clusters.sort(
        key=lambda cluster: (
            cluster.last_seen_at or cluster.created_at,
            cluster.hot_score,
        ),
        reverse=True,
    )
    return clusters[:limit]


def _has_editorial(cluster: EventCluster) -> bool:
    return bool(cluster.editorial_title and cluster.editorial_summary and cluster.editorial_category)


def _editorial_context(db: Session, cluster: EventCluster) -> EditorialContext:
    rows = db.execute(
        select(Source.id, Source.name, Source.type, Source.weight)
        .join(RawItem, RawItem.source_id == Source.id)
        .join(Evidence, Evidence.raw_item_id == RawItem.id)
        .where(Evidence.event_cluster_id == cluster.id)
    ).all()
    source_names = sorted({name for _, name, _, _ in rows})
    source_types = sorted({source_type for _, _, source_type, _ in rows})
    source_weights = {source_id: max(weight or 0, 0) for source_id, _, _, weight in rows}
    source_weight = sum(source_weights.values())
    total_evidence = db.scalar(
        select(func.count(Evidence.id)).where(Evidence.event_cluster_id == cluster.id)
    )
    return EditorialContext(
        source_names=source_names,
        source_types=source_types,
        source_weight=source_weight,
        evidence_count=total_evidence or 0,
    )


def _editorial_input_hash(cluster: EventCluster, context: EditorialContext) -> str:
    return stable_hash(
        "event_editorial",
        cluster.id,
        cluster.title,
        cluster.summary,
        *context.source_names,
        *context.source_types,
        context.source_weight,
        context.evidence_count,
    )


def _estimate_tokens(cluster: EventCluster, context: EditorialContext) -> int:
    total_chars = len(cluster.title) + len(cluster.summary or "")
    total_chars += sum(len(value) for value in context.source_names)
    total_chars += sum(len(value) for value in context.source_types)
    return max(1, total_chars // 4)


def _safe_category(value: str) -> str:
    return value if value in EDITORIAL_CATEGORIES else "other"


def _safe_tags(tags: list[str], context: EditorialContext) -> list[str]:
    normalized: list[str] = []
    if context.source_weight >= 3:
        normalized.append("重点源")
    for tag in tags:
        tag = str(tag).strip()
        if tag and tag not in normalized:
            normalized.append(tag)
        if len(normalized) >= 5:
            break
    return normalized or ["其他"]


def _safe_priority(priority: int, context: EditorialContext) -> int:
    try:
        value = int(priority)
    except (TypeError, ValueError):
        value = 0
    if context.source_weight >= 3:
        value += 8
    return max(0, min(100, value))


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
            task_type="event_editorial",
            input_hash=input_hash,
            model=model,
            status=status,
            token_estimate=token_estimate,
            error_message=error_message,
        )
    )
