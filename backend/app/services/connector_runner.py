from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.connectors import connectors_by_type
from app.connectors.types import ConnectorFetchResult
from app.db.models import FetchRun, Source, WebpageSnapshot
from app.services.ingestion import ingest_raw_item


def run_source_fetch(db: Session, source: Source) -> FetchRun:
    run = FetchRun(source_id=source.id, status="failed")
    db.add(run)
    db.flush()

    attempts = _retry_attempts(source)
    errors: list[str] = []
    try:
        connector = connectors_by_type[source.type]
        for attempt in range(1, attempts + 1):
            try:
                result = connector.fetch(db, source)
                created_count = _persist_result(db, source, result)
                run.status = "success"
                run.items_found = len(result.items)
                run.items_created = created_count
                run.error_message = None
                source.last_fetched_at = datetime.now(timezone.utc)
                source.last_error = None
                break
            except Exception as exc:  # noqa: BLE001 - connector errors must be isolated and retried.
                errors.append(f"attempt {attempt}: {exc}")
                if attempt == attempts:
                    raise
    except Exception as exc:  # noqa: BLE001 - connector errors must be isolated and recorded.
        run.status = "failed"
        detail = errors[-1] if errors else str(exc)
        run.error_message = detail
        source.last_error = detail
    finally:
        run.finished_at = datetime.now(timezone.utc)
        db.add(source)
        db.add(run)
        db.commit()
        db.refresh(run)
    return run


def run_enabled_sources(db: Session) -> list[FetchRun]:
    runs: list[FetchRun] = []
    sources = db.scalars(select(Source).where(Source.enabled.is_(True))).all()
    for source in sources:
        runs.append(run_source_fetch(db, source))
    return runs


def _persist_result(db: Session, source: Source, result: ConnectorFetchResult) -> int:
    created_count = 0
    for snapshot in result.snapshots:
        db.add(
            WebpageSnapshot(
                target_id=snapshot.target_id,
                text_content=snapshot.text_content,
                content_hash=snapshot.content_hash,
                diff_summary=snapshot.diff_summary,
            )
        )

    for item in result.items:
        _, created = ingest_raw_item(db, source, item)
        if created:
            created_count += 1

    return created_count


def _retry_attempts(source: Source) -> int:
    value = source.config_json.get("retryAttempts", 2)
    try:
        attempts = int(value)
    except (TypeError, ValueError):
        attempts = 2
    return max(1, min(attempts, 5))
