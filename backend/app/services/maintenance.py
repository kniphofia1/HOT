from __future__ import annotations

from datetime import datetime, timedelta, timezone
from os import getenv
from typing import Any

from sqlalchemy import Date, DateTime, func, select
from sqlalchemy.orm import Session

from app.db.models import (
    AiRunLog,
    AutomationRunLog,
    AutomationSchedule,
    BriefDelivery,
    BriefExport,
    BriefTemplate,
    EventCandidate,
    EventCluster,
    Evidence,
    FetchRun,
    LocalCredential,
    MetricSnapshot,
    RawItem,
    Source,
    WebMonitorTarget,
    WebpageSnapshot,
)


BACKUP_VERSION = 1
BACKUP_MODELS = [
    Source,
    RawItem,
    FetchRun,
    WebMonitorTarget,
    WebpageSnapshot,
    EventCandidate,
    EventCluster,
    Evidence,
    MetricSnapshot,
    AiRunLog,
    BriefTemplate,
    BriefExport,
    BriefDelivery,
    AutomationSchedule,
    AutomationRunLog,
    LocalCredential,
]


def source_health_summary(db: Session) -> dict[str, Any]:
    sources = list(db.scalars(select(Source).order_by(Source.created_at.desc())).all())
    rows = [_source_health(db, source) for source in sources]
    failing = sum(1 for row in rows if row["status"] == "failing")
    stale = sum(1 for row in rows if row["status"] == "stale")
    disabled = sum(1 for row in rows if row["status"] == "disabled")
    never_fetched = sum(1 for row in rows if row["status"] == "never_fetched")
    status = "ok"
    if failing:
        status = "degraded"
    elif stale or never_fetched:
        status = "attention"
    return {
        "status": status,
        "generatedAt": datetime.now(timezone.utc),
        "sourceCount": len(sources),
        "enabledSourceCount": len([source for source in sources if source.enabled]),
        "failingSourceCount": failing,
        "staleSourceCount": stale,
        "disabledSourceCount": disabled,
        "neverFetchedSourceCount": never_fetched,
        "sources": rows,
    }


def export_backup(db: Session) -> dict[str, Any]:
    return {
        "version": BACKUP_VERSION,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "tables": {
            model.__tablename__: [_serialize_row(row) for row in db.scalars(select(model)).all()]
            for model in BACKUP_MODELS
        },
    }


def restore_backup(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("version") != BACKUP_VERSION:
        raise ValueError("Unsupported backup version")
    tables = payload.get("tables")
    if not isinstance(tables, dict):
        raise ValueError("Backup payload missing tables")

    restored: dict[str, int] = {}
    for model in BACKUP_MODELS:
        rows = tables.get(model.__tablename__, [])
        if not isinstance(rows, list):
            raise ValueError(f"Backup table {model.__tablename__} must be a list")
        restored[model.__tablename__] = _restore_rows(db, model, rows)
    db.commit()
    return {"status": "success", "restored": restored}


def upsert_local_credential(
    db: Session,
    *,
    key: str,
    label: str,
    provider: str | None,
    environment_key: str | None,
    notes: str | None,
) -> LocalCredential:
    credential = db.scalar(select(LocalCredential).where(LocalCredential.key == key))
    if credential is None:
        credential = LocalCredential(key=key, label=label)
    credential.label = label
    credential.provider = provider
    credential.environment_key = environment_key
    credential.notes = notes
    credential.configured = bool(environment_key and getenv(environment_key))
    credential.secret_hint = _secret_hint(environment_key)
    db.add(credential)
    db.commit()
    db.refresh(credential)
    return credential


def refresh_local_credentials(db: Session) -> list[LocalCredential]:
    credentials = list(db.scalars(select(LocalCredential).order_by(LocalCredential.key.asc())).all())
    for credential in credentials:
        credential.configured = bool(credential.environment_key and getenv(credential.environment_key))
        credential.secret_hint = _secret_hint(credential.environment_key)
        db.add(credential)
    db.commit()
    return credentials


def _source_health(db: Session, source: Source) -> dict[str, Any]:
    last_run = db.scalar(
        select(FetchRun)
        .where(FetchRun.source_id == source.id)
        .order_by(FetchRun.started_at.desc())
        .limit(1)
    )
    total_runs = db.scalar(select(func.count(FetchRun.id)).where(FetchRun.source_id == source.id)) or 0
    failed_runs = db.scalar(
        select(func.count(FetchRun.id)).where(
            FetchRun.source_id == source.id,
            FetchRun.status == "failed",
        )
    ) or 0
    consecutive_failures = _consecutive_failures(db, source.id)
    next_fetch_at = _next_fetch_at(source)
    now = datetime.now(timezone.utc)
    is_due = bool(source.enabled and (next_fetch_at is None or _ensure_aware(next_fetch_at) <= now))
    status = "healthy"
    if not source.enabled:
        status = "disabled"
    elif last_run is None:
        status = "never_fetched"
    elif last_run.status == "failed":
        status = "failing"
    elif is_due and source.last_fetched_at is not None:
        status = "stale"
    return {
        "sourceId": source.id,
        "name": source.name,
        "type": source.type,
        "status": status,
        "enabled": source.enabled,
        "isDue": is_due,
        "lastFetchedAt": source.last_fetched_at,
        "nextFetchAt": next_fetch_at,
        "lastRunStatus": last_run.status if last_run else None,
        "lastRunAt": last_run.started_at if last_run else None,
        "lastError": source.last_error or (last_run.error_message if last_run else None),
        "totalRuns": total_runs,
        "failedRuns": failed_runs,
        "consecutiveFailures": consecutive_failures,
    }


def _consecutive_failures(db: Session, source_id: str) -> int:
    runs = db.scalars(
        select(FetchRun).where(FetchRun.source_id == source_id).order_by(FetchRun.started_at.desc())
    ).all()
    count = 0
    for run in runs:
        if run.status != "failed":
            break
        count += 1
    return count


def _next_fetch_at(source: Source) -> datetime | None:
    if source.last_fetched_at is None:
        return None
    return _ensure_aware(source.last_fetched_at) + timedelta(minutes=source.poll_interval_minutes)


def _serialize_row(row: Any) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for column in row.__table__.columns:
        value = getattr(row, column.name)
        if isinstance(value, datetime):
            result[column.name] = _ensure_aware(value).isoformat()
        else:
            result[column.name] = value
    return result


def _restore_rows(db: Session, model: type, rows: list[dict[str, Any]]) -> int:
    restored = 0
    for row in rows:
        if not isinstance(row, dict) or "id" not in row:
            raise ValueError(f"Backup row for {model.__tablename__} is invalid")
        data = {
            column.name: _coerce_value(column, row[column.name])
            for column in model.__table__.columns
            if column.name in row
        }
        existing = db.get(model, data["id"])
        if existing is None:
            db.add(model(**data))
        else:
            for key, value in data.items():
                setattr(existing, key, value)
            db.add(existing)
        restored += 1
    return restored


def _coerce_value(column: Any, value: Any) -> Any:
    if value is None:
        return None
    if isinstance(column.type, DateTime) and isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    if isinstance(column.type, Date) and isinstance(value, str):
        return datetime.fromisoformat(value).date()
    return value


def _secret_hint(environment_key: str | None) -> str | None:
    if not environment_key:
        return None
    value = getenv(environment_key, "")
    if not value:
        return None
    return f"set:{environment_key}:***{value[-4:]}"


def _ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value
