from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from sqlalchemy import select

from app.db.models import AutomationRunLog, BriefDelivery, BriefExport, EventCluster, FetchRun, Source
from app.services.automation import run_automation_task


def test_automation_settings_defaults_and_update(client):
    response = client.get("/api/automation/settings")

    assert response.status_code == 200
    schedules = {item["taskType"]: item for item in response.json()["schedules"]}
    assert schedules["source_refresh"]["enabled"] is True
    assert schedules["daily_reports"]["runTime"] == "08:30"

    update = client.patch(
        "/api/automation/settings",
        json={
            "sourceRefreshEnabled": False,
            "dailyReportsEnabled": True,
            "dailyRunTime": "09:15",
            "timezone": "Asia/Shanghai",
            "globalMaxEvents": 20,
            "industryMaxEvents": 8,
        },
    )

    assert update.status_code == 200
    schedules = {item["taskType"]: item for item in update.json()["schedules"]}
    assert schedules["source_refresh"]["enabled"] is False
    assert schedules["daily_reports"]["runTime"] == "09:15"
    assert schedules["daily_reports"]["configJson"]["globalMaxEvents"] == 20
    assert schedules["daily_reports"]["configJson"]["industryMaxEvents"] == 8


def test_source_refresh_only_runs_due_sources(monkeypatch, db_session):
    now = datetime(2026, 5, 10, 0, 30, tzinfo=timezone.utc)
    due = Source(type="rss", name="Due RSS", url="https://example.com/due.xml", enabled=True, config_json={})
    not_due = Source(
        type="rss",
        name="Fresh RSS",
        url="https://example.com/fresh.xml",
        enabled=True,
        poll_interval_minutes=60,
        last_fetched_at=now - timedelta(minutes=10),
        config_json={},
    )
    db_session.add_all([due, not_due])
    db_session.commit()
    fetched: list[str] = []

    def fake_fetch(db, source):
        fetched.append(source.name)
        run = FetchRun(source_id=source.id, status="success", items_found=1, items_created=1)
        db.add(run)
        db.flush()
        return run

    monkeypatch.setattr("app.services.automation.run_source_fetch", fake_fetch)
    monkeypatch.setattr(
        "app.services.automation.run_event_clustering",
        lambda db, limit: SimpleNamespace(
            status="success",
            candidates_created=0,
            clusters_created=0,
            clusters_updated=0,
            evidence_created=0,
            ai_runs_created=0,
            errors=[],
        ),
    )
    monkeypatch.setattr(
        "app.services.automation.classify_event_clusters",
        lambda db, limit: SimpleNamespace(
            status="success",
            clusters_classified=0,
            clusters_skipped=0,
            ai_runs_created=0,
            errors=[],
        ),
    )
    monkeypatch.setattr(
        "app.services.automation.edit_event_clusters",
        lambda db, limit: SimpleNamespace(status="success", clusters_edited=0, clusters_skipped=0, ai_runs_created=0, errors=[]),
    )
    monkeypatch.setattr(
        "app.services.automation.translate_event_clusters",
        lambda db, limit: SimpleNamespace(status="success", clusters_translated=0, clusters_skipped=0, ai_runs_created=0, errors=[]),
    )
    monkeypatch.setattr("app.services.automation.recompute_hot_scores", lambda db: SimpleNamespace(clusters_scored=0))

    result = run_automation_task(db_session, "source_refresh", now=now)

    assert result.status == "success"
    assert fetched == ["Due RSS"]
    assert result.payload["sourceCount"] == 1
    assert result.payload["skippedSources"] == []


def test_source_refresh_skips_credential_sources_without_env(monkeypatch, db_session):
    now = datetime(2026, 5, 10, 0, 30, tzinfo=timezone.utc)
    public = Source(type="rss", name="Public RSS", url="https://example.com/public.xml", enabled=True, config_json={})
    paid = Source(
        type="x_recent_search",
        name="Paid X",
        enabled=True,
        config_json={"requiresCredential": True, "bearerTokenEnv": "MISSING_TEST_X_TOKEN"},
    )
    db_session.add_all([public, paid])
    db_session.commit()
    monkeypatch.delenv("MISSING_TEST_X_TOKEN", raising=False)

    fetched: list[str] = []

    def fake_fetch(db, source):
        fetched.append(source.name)
        run = FetchRun(source_id=source.id, status="success", items_found=1, items_created=1)
        db.add(run)
        db.flush()
        return run

    monkeypatch.setattr("app.services.automation.run_source_fetch", fake_fetch)
    monkeypatch.setattr(
        "app.services.automation.run_event_clustering",
        lambda db, limit: SimpleNamespace(
            status="success",
            candidates_created=0,
            clusters_created=0,
            clusters_updated=0,
            evidence_created=0,
            ai_runs_created=0,
            errors=[],
        ),
    )
    monkeypatch.setattr(
        "app.services.automation.classify_event_clusters",
        lambda db, limit: SimpleNamespace(
            status="success",
            clusters_classified=0,
            clusters_skipped=0,
            ai_runs_created=0,
            errors=[],
        ),
    )
    monkeypatch.setattr(
        "app.services.automation.edit_event_clusters",
        lambda db, limit: SimpleNamespace(status="success", clusters_edited=0, clusters_skipped=0, ai_runs_created=0, errors=[]),
    )
    monkeypatch.setattr(
        "app.services.automation.translate_event_clusters",
        lambda db, limit: SimpleNamespace(status="success", clusters_translated=0, clusters_skipped=0, ai_runs_created=0, errors=[]),
    )
    monkeypatch.setattr("app.services.automation.recompute_hot_scores", lambda db: SimpleNamespace(clusters_scored=0))

    result = run_automation_task(db_session, "source_refresh", now=now)

    assert result.status == "success"
    assert fetched == ["Public RSS"]
    assert result.payload["sourceCount"] == 1
    assert result.payload["skippedSources"] == [
        {"sourceId": paid.id, "name": "Paid X", "type": "x_recent_search", "reason": "missing credential"}
    ]


def test_automation_skips_when_same_task_is_running(db_session):
    now = datetime(2026, 5, 10, 0, 30, tzinfo=timezone.utc)
    active = AutomationRunLog(task_type="source_refresh", status="running", started_at=now - timedelta(minutes=3), payload_json={})
    db_session.add(active)
    db_session.commit()

    result = run_automation_task(db_session, "source_refresh", now=now)

    assert result.status == "running"
    assert result.payload["skipped"] is True
    assert result.payload["activeRunId"] == active.id


def test_daily_reports_create_public_industry_exports(db_session):
    now = datetime(2026, 5, 10, 0, 40, tzinfo=timezone.utc)
    cluster = _cluster(
        db_session,
        "AI datacenter power demand accelerates",
        now,
        ["semiconductor", "energy"],
    )
    db_session.commit()

    result = run_automation_task(db_session, "daily_reports", now=now)

    assert result.status == "success"
    exports = db_session.scalars(select(BriefExport).order_by(BriefExport.scope_type, BriefExport.scope_key)).all()
    public_exports = [export for export in exports if export.is_public]
    assert {(export.scope_type, export.scope_key) for export in public_exports} == {
        ("industry", "semiconductor"),
        ("industry", "energy"),
    }
    assert all(export.report_date.isoformat() == "2026-05-10" for export in public_exports if export.report_date)
    assert all(cluster.id in export.event_cluster_ids_json for export in public_exports)
    assert {export.brief_type for export in public_exports} == {"industry_daily"}
    deliveries = db_session.scalars(select(BriefDelivery)).all()
    assert {delivery.target_type for delivery in deliveries} == {"site_public"}
    assert all(delivery.status == "ready" for delivery in deliveries)
    assert db_session.scalar(select(AutomationRunLog).where(AutomationRunLog.task_type == "daily_reports")) is not None


def test_public_industry_digest_uses_public_report(client, db_session):
    now = datetime(2026, 5, 10, 0, 40, tzinfo=timezone.utc)
    cluster = _cluster(db_session, "Robot platform launch", now, ["embodied_ai"])
    db_session.commit()
    run_automation_task(db_session, "daily_reports", now=now)

    index_response = client.get("/api/public/industries")
    digest_response = client.get("/api/public/industries/embodied_ai?date=2026-05-10")

    assert index_response.status_code == 200
    robotics = next(item for item in index_response.json() if item["domain"] == "embodied_ai")
    assert robotics["storyCount"] == 1
    assert robotics["latestDate"] == "2026-05-10"
    assert digest_response.status_code == 200
    payload = digest_response.json()
    assert payload["domain"] == "embodied_ai"
    assert payload["storyCount"] == 1
    assert payload["markdown"]


def _cluster(db_session, title: str, now: datetime, domains: list[str]) -> EventCluster:
    cluster = EventCluster(
        title=title,
        summary=f"{title} summary",
        hot_score=82,
        score_reason_json=[{"key": "hot", "label": "热度", "score": 82, "detail": "自动报告测试"}],
        confidence=80,
        first_seen_at=now - timedelta(hours=1),
        last_seen_at=now - timedelta(minutes=5),
        editorial_tags_json=[],
        editorial_priority=1,
        intelligence_reason_json=[],
        impact_domains_json=domains,
        entities_json=["OpenAI"],
        historical_matches_json=[],
    )
    db_session.add(cluster)
    db_session.flush()
    return cluster
