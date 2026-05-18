from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    AutomationRunLog,
    AutomationSchedule,
    BriefDelivery,
    BriefExport,
    BriefTemplate,
    EventCluster,
    Evidence,
    RawItem,
    Source,
)
from app.services.brief_delivery import create_delivery
from app.services.brief_exporter import ensure_default_templates, preview_markdown
from app.services.clustering import run_event_clustering
from app.services.connector_runner import run_source_fetch
from app.services.editorial import edit_event_clusters
from app.services.industry_classifier import classify_event_clusters
from app.services.industry_taxonomy import (
    INDUSTRY_LABELS,
    industry_classification_blocks_source_fallback,
    industry_values_from_config,
    industry_values_from_domains,
)
from app.services.scoring import recompute_hot_scores
from app.services.translation import translate_event_clusters


SOURCE_REFRESH_TASK = "source_refresh"
DAILY_REPORTS_TASK = "daily_reports"
DEFAULT_TIMEZONE = "Asia/Shanghai"
DEFAULT_DAILY_RUN_TIME = "08:30"
DEFAULT_SOURCE_CADENCE_MINUTES = 5
TASK_LOCK_MINUTES = 30

IMPACT_DOMAIN_LABELS = INDUSTRY_LABELS


@dataclass(frozen=True)
class AutomationResult:
    task_type: str
    status: str
    payload: dict[str, Any]
    error: str | None = None


def ensure_default_schedules(db: Session, *, now: datetime | None = None) -> list[AutomationSchedule]:
    current = _ensure_aware(now or datetime.now(timezone.utc))
    specs = [
        {
            "task_type": SOURCE_REFRESH_TASK,
            "enabled": True,
            "timezone": DEFAULT_TIMEZONE,
            "run_time": None,
            "cadence_minutes": DEFAULT_SOURCE_CADENCE_MINUTES,
            "config_json": {"clusterLimit": 10, "translationLimit": 10, "editorialLimit": 10},
        },
        {
            "task_type": DAILY_REPORTS_TASK,
            "enabled": True,
            "timezone": DEFAULT_TIMEZONE,
            "run_time": DEFAULT_DAILY_RUN_TIME,
            "cadence_minutes": 1440,
            "config_json": {"globalMaxEvents": 30, "industryMaxEvents": 12, "windowHours": 24},
        },
    ]
    schedules: list[AutomationSchedule] = []
    for spec in specs:
        schedule = db.scalar(select(AutomationSchedule).where(AutomationSchedule.task_type == spec["task_type"]))
        if schedule is None:
            schedule = AutomationSchedule(**spec)
            schedule.next_run_at = _initial_next_run_at(schedule, current)
            db.add(schedule)
        else:
            for key in ("enabled", "timezone", "run_time", "cadence_minutes"):
                if getattr(schedule, key) in {None, ""}:
                    setattr(schedule, key, spec[key])
            schedule.config_json = {**spec["config_json"], **(schedule.config_json or {})}
            if schedule.next_run_at is None:
                schedule.next_run_at = _next_run_at(schedule, current)
            db.add(schedule)
        schedules.append(schedule)
    db.commit()
    for schedule in schedules:
        db.refresh(schedule)
    return sorted(schedules, key=lambda item: item.task_type)


def update_automation_settings(
    db: Session,
    *,
    source_refresh_enabled: bool | None = None,
    daily_reports_enabled: bool | None = None,
    daily_run_time: str | None = None,
    timezone_name: str | None = None,
    global_max_events: int | None = None,
    industry_max_events: int | None = None,
    now: datetime | None = None,
) -> list[AutomationSchedule]:
    schedules = {schedule.task_type: schedule for schedule in ensure_default_schedules(db, now=now)}
    current = _ensure_aware(now or datetime.now(timezone.utc))

    source_schedule = schedules[SOURCE_REFRESH_TASK]
    daily_schedule = schedules[DAILY_REPORTS_TASK]
    if source_refresh_enabled is not None:
        source_schedule.enabled = source_refresh_enabled
    if daily_reports_enabled is not None:
        daily_schedule.enabled = daily_reports_enabled
    if timezone_name:
        _timezone(timezone_name)
        source_schedule.timezone = timezone_name
        daily_schedule.timezone = timezone_name
    if daily_run_time is not None:
        _parse_run_time(daily_run_time)
        daily_schedule.run_time = daily_run_time
    if global_max_events is not None:
        daily_schedule.config_json = {**(daily_schedule.config_json or {}), "globalMaxEvents": _bounded(global_max_events, 1, 100)}
    if industry_max_events is not None:
        daily_schedule.config_json = {**(daily_schedule.config_json or {}), "industryMaxEvents": _bounded(industry_max_events, 1, 50)}

    for schedule in schedules.values():
        schedule.next_run_at = _next_run_at(schedule, current)
        db.add(schedule)
    db.commit()
    return ensure_default_schedules(db, now=current)


def run_due_automation(db: Session, *, now: datetime | None = None) -> list[AutomationResult]:
    current = _ensure_aware(now or datetime.now(timezone.utc))
    results: list[AutomationResult] = []
    for schedule in ensure_default_schedules(db, now=current):
        next_run_at = _ensure_aware(schedule.next_run_at) if schedule.next_run_at else current
        if schedule.enabled and next_run_at <= current:
            results.append(run_automation_task(db, schedule.task_type, now=current))
    return results


def run_automation_task(db: Session, task_type: str, *, now: datetime | None = None) -> AutomationResult:
    current = _ensure_aware(now or datetime.now(timezone.utc))
    ensure_default_schedules(db, now=current)
    if task_type == "all":
        source = run_automation_task(db, SOURCE_REFRESH_TASK, now=current)
        reports = run_automation_task(db, DAILY_REPORTS_TASK, now=current)
        status = "success" if source.status == "success" and reports.status == "success" else "partial"
        return AutomationResult("all", status, {"results": [source.payload, reports.payload]})
    if task_type == SOURCE_REFRESH_TASK:
        return _run_with_log(db, task_type, lambda: _run_source_refresh(db, current), now=current)
    if task_type == DAILY_REPORTS_TASK:
        return _run_with_log(db, task_type, lambda: _run_daily_reports(db, current), now=current)
    raise ValueError(f"Unsupported automation task: {task_type}")


def list_automation_runs(db: Session, *, take: int = 100) -> list[AutomationRunLog]:
    return list(db.scalars(select(AutomationRunLog).order_by(AutomationRunLog.started_at.desc()).limit(take)).all())


def _run_with_log(db: Session, task_type: str, action, *, now: datetime) -> AutomationResult:
    active_log = _active_running_log(db, task_type, now)
    if active_log is not None:
        return AutomationResult(
            task_type,
            "running",
            {
                "skipped": True,
                "reason": "task already running",
                "activeRunId": active_log.id,
                "activeStartedAt": active_log.started_at.isoformat(),
            },
        )

    log = AutomationRunLog(task_type=task_type, status="running", started_at=now, payload_json={})
    db.add(log)
    db.commit()
    try:
        payload = action()
        status = "partial" if payload.get("errors") else "success"
        log.status = status
        log.payload_json = payload
        log.error_message = "; ".join(payload.get("errors", [])) or None
        result = AutomationResult(task_type, status, payload, log.error_message)
    except Exception as exc:  # noqa: BLE001 - automation should log failures and keep the app alive.
        log.status = "failed"
        log.error_message = str(exc)
        log.payload_json = {"errors": [str(exc)]}
        result = AutomationResult(task_type, "failed", log.payload_json, str(exc))
    finally:
        log.finished_at = datetime.now(timezone.utc)
        schedule = db.scalar(select(AutomationSchedule).where(AutomationSchedule.task_type == task_type))
        if schedule is not None:
            schedule.last_run_at = log.finished_at
            schedule.last_error = log.error_message
            schedule.next_run_at = _next_run_at(schedule, log.finished_at)
            db.add(schedule)
        db.add(log)
        db.commit()
    return result


def _active_running_log(db: Session, task_type: str, now: datetime) -> AutomationRunLog | None:
    active: AutomationRunLog | None = None
    running_logs = db.scalars(
        select(AutomationRunLog)
        .where(AutomationRunLog.task_type == task_type)
        .where(AutomationRunLog.status == "running")
        .order_by(AutomationRunLog.started_at.desc())
    ).all()
    stale_before = now - timedelta(minutes=TASK_LOCK_MINUTES)
    for log in running_logs:
        started_at = _ensure_aware(log.started_at)
        if started_at < stale_before:
            log.status = "failed"
            log.finished_at = now
            log.error_message = "stale running task recovered"
            log.payload_json = {"errors": [log.error_message]}
            db.add(log)
        elif active is None:
            active = log
    if running_logs:
        db.commit()
    return active


def _run_source_refresh(db: Session, now: datetime) -> dict[str, Any]:
    source_schedule = db.scalar(select(AutomationSchedule).where(AutomationSchedule.task_type == SOURCE_REFRESH_TASK))
    config = source_schedule.config_json if source_schedule is not None else {}
    enabled_sources = db.scalars(select(Source).where(Source.enabled.is_(True))).all()
    skipped_sources = _skipped_sources(enabled_sources)
    skipped_ids = {item["sourceId"] for item in skipped_sources}
    due_sources = [source for source in enabled_sources if source.id not in skipped_ids and _source_is_due(source, now)]
    fetch_runs = [run_source_fetch(db, source) for source in due_sources]
    clustering = run_event_clustering(db, limit=int(config.get("clusterLimit", 100)))
    classification = classify_event_clusters(db, limit=int(config.get("clusterLimit", 100)))
    translation = translate_event_clusters(db, limit=int(config.get("translationLimit", config.get("editorialLimit", 100))))
    editorial = edit_event_clusters(db, limit=int(config.get("editorialLimit", 100)))
    scoring = recompute_hot_scores(db)
    errors = [run.error_message for run in fetch_runs if run.error_message]
    errors.extend(clustering.errors)
    errors.extend(classification.errors)
    errors.extend(translation.errors)
    errors.extend(editorial.errors)
    return {
        "sourceCount": len(due_sources),
        "skippedSources": skipped_sources,
        "fetchRuns": [
            {
                "id": run.id,
                "sourceId": run.source_id,
                "status": run.status,
                "itemsFound": run.items_found,
                "itemsCreated": run.items_created,
                "errorMessage": run.error_message,
            }
            for run in fetch_runs
        ],
        "clustering": {
            "status": clustering.status,
            "candidatesCreated": clustering.candidates_created,
            "clustersCreated": clustering.clusters_created,
            "clustersUpdated": clustering.clusters_updated,
            "evidenceCreated": clustering.evidence_created,
            "aiRunsCreated": clustering.ai_runs_created,
            "errors": clustering.errors,
        },
        "classification": {
            "status": classification.status,
            "clustersClassified": classification.clusters_classified,
            "clustersSkipped": classification.clusters_skipped,
            "aiRunsCreated": classification.ai_runs_created,
            "errors": classification.errors,
        },
        "translation": {
            "status": translation.status,
            "clustersTranslated": translation.clusters_translated,
            "clustersSkipped": translation.clusters_skipped,
            "aiRunsCreated": translation.ai_runs_created,
            "errors": translation.errors,
        },
        "editorial": {
            "status": editorial.status,
            "clustersEdited": editorial.clusters_edited,
            "clustersSkipped": editorial.clusters_skipped,
            "aiRunsCreated": editorial.ai_runs_created,
            "errors": editorial.errors,
        },
        "scoring": {"clustersScored": scoring.clusters_scored},
        "errors": errors,
    }


def _run_daily_reports(db: Session, now: datetime) -> dict[str, Any]:
    schedule = db.scalar(select(AutomationSchedule).where(AutomationSchedule.task_type == DAILY_REPORTS_TASK))
    config = schedule.config_json if schedule is not None else {}
    timezone_name = schedule.timezone if schedule is not None else DEFAULT_TIMEZONE
    local_now = now.astimezone(_timezone(timezone_name))
    report_date = local_now.date()
    window_hours = _bounded(int(config.get("windowHours", 24)), 1, 168)
    start = now - timedelta(hours=window_hours)
    clusters = [
        cluster
        for cluster in db.scalars(select(EventCluster)).all()
        if _cluster_seen_between(cluster, start, now)
    ]
    clusters = sorted(clusters, key=lambda item: (item.hot_score, item.last_seen_at or item.created_at), reverse=True)
    industry_limit = _bounded(int(config.get("industryMaxEvents", 12)), 1, 50)

    exports: list[BriefExport] = []
    for domain, label in INDUSTRY_LABELS.items():
        domain_clusters = [cluster for cluster in clusters if domain in _cluster_industry_keys(db, cluster)]
        if not domain_clusters:
            continue
        exports.append(
            _upsert_public_report(
                db,
                title=f"{report_date.isoformat()} {label}日报",
                scope_type="industry",
                scope_key=domain,
                report_date=report_date,
                clusters=domain_clusters[:industry_limit],
                template_mode="industry_weekly",
                now=now,
            )
        )
    return {
        "reportDate": report_date.isoformat(),
        "windowHours": window_hours,
        "clustersScanned": len(clusters),
        "industries": list(INDUSTRY_LABELS),
        "exportsCreated": len(exports),
        "exportIds": [export.id for export in exports],
        "errors": [],
    }


def _upsert_public_report(
    db: Session,
    *,
    title: str,
    scope_type: str,
    scope_key: str,
    report_date: date,
    clusters: list[EventCluster],
    template_mode: str,
    now: datetime,
) -> BriefExport:
    template = _template_for_mode(db, template_mode)
    cluster_ids = [cluster.id for cluster in clusters]
    markdown = preview_markdown(
        db,
        template_id=template.id,
        title=title,
        event_cluster_ids=cluster_ids,
        manual_notes={},
    )
    export = db.scalar(
        select(BriefExport)
        .where(BriefExport.scope_type == scope_type)
        .where(BriefExport.scope_key == scope_key)
        .where(BriefExport.report_date == report_date)
        .where(BriefExport.is_public.is_(True))
    )
    if export is None:
        export = BriefExport(template_id=template.id, title=title, markdown=markdown)
    export.template_id = template.id
    export.title = title
    export.brief_type = "industry_daily" if scope_type == "industry" else "daily"
    export.scope_type = scope_type
    export.scope_key = scope_key
    export.report_date = report_date
    export.is_public = True
    export.event_cluster_ids_json = cluster_ids
    export.manual_notes_json = {}
    export.export_formats_json = ["markdown", "docx", "print_html"]
    export.markdown = markdown
    export.generated_at = now
    db.add(export)
    db.commit()
    db.refresh(export)
    _ensure_site_public_delivery(db, export)
    db.refresh(export)
    return export


def _ensure_site_public_delivery(db: Session, export: BriefExport) -> BriefDelivery:
    delivery = db.scalar(
        select(BriefDelivery)
        .where(BriefDelivery.export_id == export.id)
        .where(BriefDelivery.target_type == "site_public")
    )
    if delivery is None:
        delivery = create_delivery(export, target_type="site_public", target_label="AIHOT site")
    delivery.status = "ready"
    delivery.error_message = None
    delivery.payload_json = {
        "title": export.title,
        "briefType": export.brief_type,
        "scopeType": export.scope_type,
        "scopeKey": export.scope_key,
        "reportDate": export.report_date.isoformat() if export.report_date else None,
        "eventClusterIds": export.event_cluster_ids_json,
        "markdownChars": len(export.markdown),
    }
    db.add(delivery)
    export.delivery_targets_json = [
        target
        for target in (export.delivery_targets_json or [])
        if not (isinstance(target, dict) and target.get("targetType") == "site_public")
    ]
    export.delivery_targets_json = [
        *export.delivery_targets_json,
        {"targetType": "site_public", "targetLabel": "AIHOT site", "status": "ready"},
    ]
    db.add(export)
    db.commit()
    db.refresh(delivery)
    return delivery


def _template_for_mode(db: Session, mode: str) -> BriefTemplate:
    templates = ensure_default_templates(db)
    return next((template for template in templates if template.mode == mode), templates[0])


def _due_sources(db: Session, now: datetime) -> list[Source]:
    sources = db.scalars(select(Source).where(Source.enabled.is_(True))).all()
    skipped_ids = {item["sourceId"] for item in _skipped_sources(sources)}
    return [source for source in sources if source.id not in skipped_ids and _source_is_due(source, now)]


def _source_is_due(source: Source, now: datetime) -> bool:
    if source.last_fetched_at is None:
        return True
    next_fetch = _ensure_aware(source.last_fetched_at) + timedelta(minutes=max(source.poll_interval_minutes, 1))
    return next_fetch <= now


def _skipped_sources(sources: list[Source]) -> list[dict[str, str]]:
    skipped: list[dict[str, str]] = []
    for source in sources:
        reason = _automation_skip_reason(source)
        if reason:
            skipped.append({"sourceId": source.id, "name": source.name, "type": source.type, "reason": reason})
    return skipped


def _automation_skip_reason(source: Source) -> str | None:
    config = source.config_json or {}
    if not config.get("requiresCredential"):
        return None

    for key in ("bearerTokenEnv", "apiKeyEnv", "accessTokenEnv", "botTokenEnv"):
        env_name = config.get(key)
        if isinstance(env_name, str) and env_name and os.getenv(env_name):
            return None
    return "missing credential"


def _cluster_industry_keys(db: Session, cluster: EventCluster) -> list[str]:
    classified_keys = industry_values_from_domains(cluster.impact_domains_json)
    if classified_keys:
        return classified_keys
    if industry_classification_blocks_source_fallback(cluster.intelligence_reason_json):
        return []

    keys: list[str] = []
    rows = db.execute(
        select(Source)
        .join(RawItem, RawItem.source_id == Source.id)
        .join(Evidence, Evidence.raw_item_id == RawItem.id)
        .where(Evidence.event_cluster_id == cluster.id)
    ).scalars()
    for source in rows:
        for key in industry_values_from_config(source.config_json):
            if key not in keys:
                keys.append(key)
    return keys


def _cluster_seen_between(cluster: EventCluster, start: datetime, end: datetime) -> bool:
    value = _ensure_aware(cluster.last_seen_at or cluster.first_seen_at or cluster.created_at)
    return start <= value <= end


def _next_run_at(schedule: AutomationSchedule, now: datetime) -> datetime:
    if schedule.task_type == DAILY_REPORTS_TASK:
        zone = _timezone(schedule.timezone)
        run_at = _parse_run_time(schedule.run_time or DEFAULT_DAILY_RUN_TIME)
        local_now = now.astimezone(zone)
        candidate = datetime.combine(local_now.date(), run_at, tzinfo=zone)
        if candidate <= local_now:
            candidate = candidate + timedelta(days=1)
        return candidate.astimezone(timezone.utc)
    minutes = max(int(schedule.cadence_minutes or DEFAULT_SOURCE_CADENCE_MINUTES), 1)
    return now + timedelta(minutes=minutes)


def _initial_next_run_at(schedule: AutomationSchedule, now: datetime) -> datetime:
    if schedule.task_type == SOURCE_REFRESH_TASK:
        return now
    return _next_run_at(schedule, now)


def _parse_run_time(value: str) -> time:
    hour, minute = value.split(":", 1)
    return time(hour=int(hour), minute=int(minute))


def _timezone(value: str) -> ZoneInfo:
    try:
        return ZoneInfo(value)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"Unsupported timezone: {value}") from exc


def _bounded(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, int(value)))


def _ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value
