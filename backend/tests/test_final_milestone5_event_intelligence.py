from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.db.models import EventCluster, Evidence, RawItem, Source
from app.services.scoring import recompute_hot_scores


def test_event_intelligence_scores_lifecycle_entities_domains_and_history(db_session):
    now = datetime(2026, 4, 30, 12, 0, tzinfo=timezone.utc)
    old_source = _source(db_session, "rss", "Archive RSS", weight=2)
    old_raw = _raw_item(db_session, old_source, "OpenAI model release history", now - timedelta(days=10))
    old_cluster = _cluster(db_session, "OpenAI model release history", now - timedelta(days=10), confidence=80)
    old_cluster.created_at = now - timedelta(days=10)
    old_cluster.impact_domains_json = ["ai_tech"]
    old_cluster.entities_json = ["OpenAI"]
    _evidence(db_session, old_cluster, old_raw)

    rss = _source(db_session, "rss", "RSS", weight=2)
    github = _source(db_session, "github_repo", "GitHub", weight=3)
    x_source = _source(db_session, "x_recent_search", "X", weight=2)
    cluster = _cluster(db_session, "OpenAI releases GPT-5 model", now - timedelta(hours=3), confidence=91)
    cluster.created_at = now - timedelta(hours=3)
    _evidence(db_session, cluster, _raw_item(db_session, rss, "OpenAI releases GPT-5", now - timedelta(hours=3)))
    _evidence(db_session, cluster, _raw_item(db_session, github, "GPT-5 SDK appears on GitHub", now - timedelta(hours=2)))
    _evidence(db_session, cluster, _raw_item(db_session, x_source, "OpenAI GPT-5 discussion spreads", now - timedelta(hours=1)))
    db_session.commit()

    recompute_hot_scores(db_session, now=now)
    db_session.refresh(cluster)

    assert cluster.event_phase == "peaking"
    assert cluster.credibility_score > 50
    assert cluster.propagation_score > 60
    assert "ai_tech" in cluster.impact_domains_json
    assert "OpenAI" in cluster.entities_json
    assert cluster.historical_matches_json[0]["clusterId"] == old_cluster.id
    assert {reason["key"] for reason in cluster.intelligence_reason_json} == {
        "lifecycle",
        "coverage",
        "credibility",
        "propagation",
        "impact",
    }


def test_cluster_api_returns_event_intelligence_fields(client, db_session):
    now = datetime(2026, 4, 30, 12, 0, tzinfo=timezone.utc)
    source = _source(db_session, "telegram_updates", "Telegram", weight=2)
    cluster = _cluster(db_session, "Telegram AI agent launch", now - timedelta(hours=2), confidence=70)
    _evidence(db_session, cluster, _raw_item(db_session, source, "Telegram AI agent launch", now - timedelta(hours=2)))
    db_session.commit()
    recompute_hot_scores(db_session, now=now)

    response = client.get(f"/api/clusters/{cluster.id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["eventPhase"] == "emerging"
    assert payload["credibilityScore"] > 0
    assert payload["propagationScore"] > 0
    assert "ai_tech" in payload["impactDomainsJson"]
    assert "Telegram" in payload["entitiesJson"]
    assert payload["intelligenceReasonJson"]


def _source(db_session, source_type: str, name: str, weight: int) -> Source:
    source = Source(
        type=source_type,
        name=name,
        url=f"https://example.com/{name}",
        weight=weight,
        config_json={},
    )
    db_session.add(source)
    db_session.commit()
    db_session.refresh(source)
    return source


def _raw_item(db_session, source: Source, title: str, seen_at: datetime) -> RawItem:
    raw_item = RawItem(
        source_id=source.id,
        external_id=title,
        source_url=f"https://example.com/{title.replace(' ', '-').lower()}",
        title=title,
        content_text=f"{title} body mentions OpenAI AI model and Telegram discussion",
        published_at=seen_at,
        raw_payload_json={},
        content_hash=f"hash-{source.id}-{title}",
    )
    db_session.add(raw_item)
    db_session.commit()
    db_session.refresh(raw_item)
    return raw_item


def _cluster(db_session, title: str, seen_at: datetime, confidence: int) -> EventCluster:
    cluster = EventCluster(
        title=title,
        summary=f"{title} summary",
        confidence=confidence,
        first_seen_at=seen_at,
        last_seen_at=seen_at,
        hot_score=0,
        score_reason_json=[],
    )
    db_session.add(cluster)
    db_session.commit()
    db_session.refresh(cluster)
    return cluster


def _evidence(db_session, cluster: EventCluster, raw_item: RawItem) -> Evidence:
    evidence = Evidence(
        event_cluster_id=cluster.id,
        raw_item_id=raw_item.id,
        source_name="source",
        source_url=raw_item.source_url or "",
        quote=raw_item.content_text,
        confidence=80,
    )
    db_session.add(evidence)
    db_session.commit()
    db_session.refresh(evidence)
    return evidence
