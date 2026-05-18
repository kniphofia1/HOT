from dataclasses import dataclass

from sqlalchemy import select

from app.connectors.types import RawItemPayload
from app.db.models import EventCandidate
from app.db.models import RawItem, Source
from app.services.connector_runner import run_source_fetch
from app.services.ingestion import ingest_raw_item


@dataclass
class FakeResponse:
    content: bytes = b""

    def raise_for_status(self):
        return None


RSS_FEED = b"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0">
  <channel>
    <title>Retry RSS</title>
    <item>
      <guid>retry-1</guid>
      <title>Retry item</title>
      <link>https://example.com/retry</link>
      <description>Retry summary</description>
    </item>
  </channel>
</rss>
"""


def test_source_fetch_retries_before_success(monkeypatch, db_session):
    attempts = {"count": 0}

    def fake_get(url, **kwargs):
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise RuntimeError("temporary network failure")
        return FakeResponse(content=RSS_FEED)

    monkeypatch.setattr("app.connectors.rss.httpx.get", fake_get)
    source = Source(
        type="rss",
        name="Retry RSS",
        url="https://example.com/feed.xml",
        config_json={"retryAttempts": 3},
    )
    db_session.add(source)
    db_session.commit()

    run = run_source_fetch(db_session, source)

    assert attempts["count"] == 3
    assert run.status == "success"
    assert run.items_created == 1
    assert db_session.scalar(select(RawItem)) is not None


def test_ingestion_deduplicates_same_external_id_when_content_changes(db_session):
    source = Source(type="rss", name="Editable RSS", url="https://example.com/feed.xml", config_json={})
    db_session.add(source)
    db_session.commit()

    first, first_created = ingest_raw_item(
        db_session,
        source,
        RawItemPayload(
            external_id="same-item",
            source_url="https://example.com/item",
            title="Original title",
            content_text="Original summary",
        ),
    )
    second, second_created = ingest_raw_item(
        db_session,
        source,
        RawItemPayload(
            external_id="same-item",
            source_url="https://example.com/item?utm_source=feed",
            title="Updated title",
            content_text="Updated summary",
        ),
    )

    assert first_created is True
    assert second_created is False
    assert first.id == second.id
    assert len(db_session.scalars(select(RawItem)).all()) == 1
    candidate = db_session.scalar(select(EventCandidate))
    assert candidate is not None
    assert candidate.normalized_title == "updated title"


def test_maintenance_health_reports_failing_source(monkeypatch, client):
    def fake_get(url, **kwargs):
        raise RuntimeError("network down")

    monkeypatch.setattr("app.connectors.rss.httpx.get", fake_get)
    created = client.post(
        "/api/sources",
        json={
            "type": "rss",
            "name": "Broken RSS",
            "url": "https://example.com/broken.xml",
            "configJson": {"retryAttempts": 1},
        },
    ).json()

    client.post(f"/api/sources/{created['id']}/refresh")
    response = client.get("/api/maintenance/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "degraded"
    assert payload["failingSourceCount"] == 1
    assert payload["sources"][0]["status"] == "failing"
    assert payload["sources"][0]["consecutiveFailures"] == 1


def test_backup_export_and_restore_merges_rows(client):
    created = client.post(
        "/api/sources",
        json={
            "type": "rss",
            "name": "Backup RSS",
            "url": "https://example.com/feed.xml",
            "configJson": {},
        },
    ).json()
    backup = client.get("/api/maintenance/backup").json()

    assert client.delete(f"/api/sources/{created['id']}").status_code == 204
    assert client.get("/api/sources").json() == []

    response = client.post("/api/maintenance/restore", json=backup)

    assert response.status_code == 200
    assert response.json()["restored"]["sources"] == 1
    sources = client.get("/api/sources").json()
    assert sources[0]["id"] == created["id"]
    assert sources[0]["name"] == "Backup RSS"


def test_credentials_store_environment_reference_not_secret(monkeypatch, client):
    monkeypatch.setenv("AI_API_KEY", "secret-value-1234")

    response = client.post(
        "/api/maintenance/credentials",
        json={
            "key": "openai_api_key",
            "label": "OpenAI API Key",
            "provider": "openai",
            "environmentKey": "AI_API_KEY",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["configured"] is True
    assert payload["secretHint"].endswith("***1234")
    assert "secret-value-1234" not in response.text


def test_brief_template_update_api(client):
    template = client.get("/api/briefs/templates").json()[0]

    response = client.patch(
        f"/api/briefs/templates/{template['id']}",
        json={
            "name": "Updated Template",
            "sectionsJson": ["核心摘要", "证据"],
            "styleRules": "Keep it short.",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["name"] == "Updated Template"
    assert payload["sectionsJson"] == ["核心摘要", "证据"]
    assert payload["styleRules"] == "Keep it short."
