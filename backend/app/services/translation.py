from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.connectors.utils import stable_hash
from app.db.models import AiRunLog, EventCluster, utc_now
from app.services.ai import AiProvider, MissingAiConfigurationError, build_ai_provider


@dataclass
class TranslationRunResult:
    clusters_translated: int = 0
    clusters_skipped: int = 0
    ai_runs_created: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def status(self) -> str:
        if self.errors and self.clusters_translated:
            return "partial"
        if self.errors:
            return "failed"
        return "success"


def translate_event_clusters(
    db: Session,
    *,
    ai_provider: AiProvider | None = None,
    force: bool = False,
    limit: int = 100,
) -> TranslationRunResult:
    result = TranslationRunResult()
    clusters = _load_translation_targets(db, force=force, limit=limit)
    if not clusters:
        return result

    provider_error: Exception | None = None
    if ai_provider is None:
        try:
            ai_provider = build_ai_provider()
        except MissingAiConfigurationError as exc:
            provider_error = exc

    for cluster in clusters:
        if _has_translation(cluster) and not force:
            result.clusters_skipped += 1
            continue

        input_hash = _translation_input_hash(cluster)
        token_estimate = _estimate_tokens(cluster)
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
            translated = ai_provider.translate_event(title=cluster.title, summary=cluster.summary)
            cluster.translated_title = translated.title
            cluster.translated_summary = translated.summary
            cluster.translated_at = utc_now()
            db.add(cluster)
            _record_ai_run(
                db,
                input_hash=input_hash,
                model=ai_provider.model,
                status="success",
                token_estimate=token_estimate,
                error_message=None,
            )
            result.clusters_translated += 1
            result.ai_runs_created += 1
        except Exception as exc:  # noqa: BLE001 - translation is best-effort per event.
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


def translate_event_cluster(
    db: Session,
    cluster: EventCluster,
    *,
    ai_provider: AiProvider | None = None,
    force: bool = False,
) -> TranslationRunResult:
    if _has_translation(cluster) and not force:
        return TranslationRunResult(clusters_skipped=1)

    provider = ai_provider
    result = TranslationRunResult()
    provider_error: Exception | None = None
    if provider is None:
        try:
            provider = build_ai_provider()
        except MissingAiConfigurationError as exc:
            provider_error = exc

    input_hash = _translation_input_hash(cluster)
    token_estimate = _estimate_tokens(cluster)
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
        translated = provider.translate_event(title=cluster.title, summary=cluster.summary)
        cluster.translated_title = translated.title
        cluster.translated_summary = translated.summary
        cluster.translated_at = utc_now()
        db.add(cluster)
        _record_ai_run(
            db,
            input_hash=input_hash,
            model=provider.model,
            status="success",
            token_estimate=token_estimate,
            error_message=None,
        )
        result.clusters_translated = 1
        result.ai_runs_created = 1
    except Exception as exc:  # noqa: BLE001 - preserve original event and log the failure.
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


def _load_translation_targets(db: Session, *, force: bool, limit: int) -> list[EventCluster]:
    clusters = list(db.scalars(select(EventCluster)).all())
    if not force:
        clusters = [cluster for cluster in clusters if not _has_translation(cluster)]
    clusters.sort(key=lambda cluster: cluster.last_seen_at or cluster.created_at, reverse=True)
    return clusters[:limit]


def _has_translation(cluster: EventCluster) -> bool:
    return bool(cluster.translated_title and cluster.translated_summary)


def _translation_input_hash(cluster: EventCluster) -> str:
    return stable_hash("event_translation", cluster.id, cluster.title, cluster.summary)


def _estimate_tokens(cluster: EventCluster) -> int:
    return max(1, (len(cluster.title) + len(cluster.summary or "")) // 4)


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
            task_type="event_translation",
            input_hash=input_hash,
            model=model,
            status=status,
            token_estimate=token_estimate,
            error_message=error_message,
        )
    )
