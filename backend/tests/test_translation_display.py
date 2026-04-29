from datetime import datetime, timezone

from sqlalchemy import select

from app.db.models import AiRunLog, EventCluster
from app.services.ai import AiTranslation
from app.services.brief_exporter import ensure_default_templates, preview_markdown
from app.services.translation import translate_event_clusters


class FakeTranslationProvider:
    model = "fake-translation-model"

    def translate_event(self, *, title: str, summary: str | None) -> AiTranslation:
        return AiTranslation(title=f"中文：{title}", summary=f"中文摘要：{summary or title}")


class FailingTranslationProvider:
    model = "failing-translation-model"

    def translate_event(self, *, title: str, summary: str | None) -> AiTranslation:
        raise RuntimeError("translation unavailable")


def test_translation_run_writes_cache_and_ai_run_log(db_session):
    cluster = _cluster(db_session, "OpenAI releases a new model", "The model improves coding.")

    result = translate_event_clusters(db_session, ai_provider=FakeTranslationProvider())

    db_session.refresh(cluster)
    assert result.status == "success"
    assert result.clusters_translated == 1
    assert cluster.translated_title == "中文：OpenAI releases a new model"
    assert cluster.translated_summary == "中文摘要：The model improves coding."
    assert cluster.translated_at is not None
    run_log = db_session.scalar(select(AiRunLog))
    assert run_log is not None
    assert run_log.task_type == "event_translation"
    assert run_log.status == "success"


def test_cluster_api_uses_chinese_display_fields(client, db_session):
    cluster = _cluster(db_session, "GitHub repo ships v1.0", "The release is stable.")
    translate_event_clusters(db_session, ai_provider=FakeTranslationProvider())

    response = client.get(f"/api/clusters/{cluster.id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["title"] == "GitHub repo ships v1.0"
    assert payload["translatedTitle"] == "中文：GitHub repo ships v1.0"
    assert payload["displayTitle"] == "中文：GitHub repo ships v1.0"
    assert payload["displaySummary"] == "中文摘要：The release is stable."


def test_translation_failure_keeps_original_display_and_logs_failure(client, db_session):
    cluster = _cluster(db_session, "HN discusses a launch", "Discussion is active.")

    result = translate_event_clusters(db_session, ai_provider=FailingTranslationProvider())

    assert result.status == "failed"
    response = client.get(f"/api/clusters/{cluster.id}")
    assert response.status_code == 200
    payload = response.json()
    assert payload["displayTitle"] == "HN discusses a launch"
    assert payload["displaySummary"] == "Discussion is active."
    run_log = db_session.scalar(select(AiRunLog))
    assert run_log is not None
    assert run_log.status == "failed"
    assert run_log.error_message == "translation unavailable"


def test_brief_markdown_prefers_translated_cluster_text(db_session):
    cluster = _cluster(db_session, "Anthropic publishes a report", "Reliability details are available.")
    translate_event_clusters(db_session, ai_provider=FakeTranslationProvider())
    template = ensure_default_templates(db_session)[0]

    markdown = preview_markdown(
        db_session,
        template_id=template.id,
        title="客户简报",
        event_cluster_ids=[cluster.id],
        manual_notes={},
    )

    assert "中文：Anthropic publishes a report" in markdown
    assert "中文摘要：Reliability details are available." in markdown
    assert "1. Anthropic publishes a report（热度" not in markdown


def _cluster(db_session, title: str, summary: str) -> EventCluster:
    cluster = EventCluster(
        title=title,
        summary=summary,
        hot_score=50,
        score_reason_json=[],
        confidence=80,
        first_seen_at=datetime.now(timezone.utc),
        last_seen_at=datetime.now(timezone.utc),
    )
    db_session.add(cluster)
    db_session.commit()
    db_session.refresh(cluster)
    return cluster
