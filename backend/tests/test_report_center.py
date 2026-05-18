from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.db.models import AiRunLog, BriefExport, EventCluster, FetchRun, Source


class FakeReportProvider:
    model = "fake-report-model"

    def generate_report(self, payload):
        return f"# {payload['title']}\n\n## 一、今日核心结论\n\n1. {payload['events'][0]['title']}"


def test_generate_report_center_calls_ai_for_markdown(client, db_session, monkeypatch):
    monkeypatch.setattr("app.services.report_center.build_ai_provider", lambda: FakeReportProvider())
    now = datetime.now(timezone.utc)
    cluster = EventCluster(
        title="AI datacenter power demand accelerates",
        summary="Cloud providers are expanding AI datacenter power capacity.",
        translated_title="AI 数据中心电力需求加速",
        translated_summary="云厂商正在扩张 AI 数据中心供电能力。",
        hot_score=86,
        score_reason_json=[{"key": "impact", "label": "影响", "score": 30, "detail": "影响数据中心投资"}],
        confidence=82,
        impact_domains_json=["semiconductor"],
        entities_json=["NVIDIA", "Microsoft"],
        first_seen_at=now - timedelta(hours=2),
        last_seen_at=now - timedelta(minutes=15),
    )
    db_session.add(cluster)
    db_session.commit()

    response = client.post(
        "/api/reports/generate",
        json={
            "industry": "semiconductor",
            "timeRange": "today",
            "reportType": "daily",
            "modules": ["core_conclusions", "important_events", "technology_progress", "risk_signals"],
            "outputFormat": "markdown",
            "style": "consulting",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["title"] == "半导体行业日报"
    assert "# 半导体行业日报" in payload["markdown"]
    assert "## 一、今日核心结论" in payload["markdown"]
    assert "AI 数据中心电力需求加速" in payload["markdown"]
    assert payload["aiStatus"] == "success"
    assert payload["eventClusterIds"] == [cluster.id]
    export = db_session.scalar(select(BriefExport).where(BriefExport.id == payload["exportId"]))
    assert export is not None
    assert export.export_formats_json == ["markdown"]
    assert export.scope_key == "semiconductor"
    assert db_session.scalar(select(AiRunLog).where(AiRunLog.task_type == "report_generation")).status == "success"


def test_generate_report_supports_custom_date_range(client, db_session, monkeypatch):
    monkeypatch.setattr("app.services.report_center.build_ai_provider", lambda: FakeReportProvider())
    cluster = EventCluster(
        title="Figure ships humanoid robot update",
        summary="Figure AI updated humanoid robot deployment progress.",
        hot_score=78,
        score_reason_json=[],
        confidence=80,
        impact_domains_json=["embodied_ai"],
        entities_json=["Figure AI"],
        first_seen_at=datetime(2026, 5, 10, 3, 0, tzinfo=timezone.utc),
        last_seen_at=datetime(2026, 5, 10, 4, 0, tzinfo=timezone.utc),
    )
    db_session.add(cluster)
    db_session.commit()

    response = client.post(
        "/api/reports/generate",
        json={
            "industry": "embodied_ai",
            "timeRange": "custom",
            "startDate": "2026-05-10",
            "endDate": "2026-05-10",
            "reportType": "daily",
            "modules": ["core_conclusions"],
            "outputFormat": "markdown",
            "style": "concise",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["title"] == "具身智能行业日报"
    assert payload["eventClusterIds"] == [cluster.id]


def test_generate_report_rejects_non_markdown_output(client):
    response = client.post(
        "/api/reports/generate",
        json={
            "industry": "ai",
            "timeRange": "today",
            "reportType": "daily",
            "modules": ["core_conclusions"],
            "outputFormat": "pdf",
            "style": "consulting",
        },
    )

    assert response.status_code == 400
    assert "Only Markdown" in response.json()["detail"]


def test_generate_report_requires_ai_provider(client, db_session):
    now = datetime.now(timezone.utc)
    cluster = EventCluster(
        title="OpenAI launches agent SDK",
        summary="OpenAI launches an agent SDK for developers.",
        hot_score=80,
        score_reason_json=[],
        confidence=82,
        impact_domains_json=["ai"],
        entities_json=["OpenAI"],
        first_seen_at=now - timedelta(hours=1),
        last_seen_at=now,
    )
    db_session.add(cluster)
    db_session.commit()

    response = client.post(
        "/api/reports/generate",
        json={
            "industry": "ai",
            "timeRange": "today",
            "reportType": "daily",
            "modules": ["core_conclusions"],
            "outputFormat": "markdown",
            "style": "consulting",
        },
    )

    assert response.status_code == 400
    assert "requires AI_API_KEY" in response.json()["detail"]


def test_retry_failed_sources_skips_missing_credential_sources(client, db_session, monkeypatch):
    public = Source(
        type="rss",
        name="Failed RSS",
        url="https://example.com/feed.xml",
        enabled=True,
        last_error="timeout",
        config_json={},
    )
    paid = Source(
        type="x_recent_search",
        name="Failed X",
        enabled=True,
        last_error="missing token",
        config_json={"requiresCredential": True, "bearerTokenEnv": "MISSING_TEST_X_TOKEN"},
    )
    db_session.add_all([public, paid])
    db_session.commit()
    monkeypatch.delenv("MISSING_TEST_X_TOKEN", raising=False)

    def fake_fetch(db, source):
        run = FetchRun(source_id=source.id, status="success", items_found=1, items_created=0)
        source.last_error = None
        db.add(source)
        db.add(run)
        db.flush()
        return run

    monkeypatch.setattr("app.api.routes.sources.run_source_fetch", fake_fetch)

    response = client.post(
        "/api/sources/retry-failed",
        json={"industry": "all", "includeCredentialed": False, "runPipeline": False},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["attemptedCount"] == 1
    assert payload["skippedCount"] == 1
    assert payload["successCount"] == 1
    assert payload["skippedSources"][0]["sourceId"] == paid.id
