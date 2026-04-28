from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.db.models import EventCluster, Evidence, RawItem, Source
from app.services.scoring import recompute_hot_scores


def test_recompute_hot_scores_writes_explainable_reasons(db_session):
    source = _source(db_session, "rss", "RSS", weight=3)
    raw_item = _raw_item(db_session, source, "Fresh AI release", hours_ago=2)
    cluster = _cluster(db_session, "Fresh AI release", confidence=91, hours_ago=2)
    _evidence(db_session, cluster, raw_item)

    result = recompute_hot_scores(db_session)

    db_session.refresh(cluster)
    assert result.clusters_scored == 1
    assert cluster.hot_score > 0
    assert {reason["key"] for reason in cluster.score_reason_json} == {
        "recency",
        "sourceWeight",
        "mentionCount",
        "velocity",
        "aiImportance",
    }


def test_cluster_list_supports_time_source_score_type_filters_and_score_sort(client, db_session):
    rss_source = _source(db_session, "rss", "RSS", weight=3)
    hn_source = _source(db_session, "hacker_news", "HN", weight=1)

    fresh_rss_item = _raw_item(db_session, rss_source, "Fresh RSS event", hours_ago=2)
    fresh_cluster = _cluster(db_session, "Fresh RSS event", confidence=90, hours_ago=2)
    fresh_cluster.hot_score = 82
    fresh_cluster.score_reason_json = [{"key": "recency", "score": 30}]
    _evidence(db_session, fresh_cluster, fresh_rss_item)

    stale_hn_item = _raw_item(db_session, hn_source, "Old HN event", hours_ago=90)
    stale_cluster = _cluster(db_session, "Old HN event", confidence=50, hours_ago=90)
    stale_cluster.hot_score = 20
    stale_cluster.score_reason_json = [{"key": "recency", "score": 2}]
    _evidence(db_session, stale_cluster, stale_hn_item)
    db_session.commit()

    response = client.get("/api/clusters?hours=24&sourceType=rss&minScore=50&sort=score")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["id"] == fresh_cluster.id
    assert payload[0]["hotScore"] == 82
    assert payload[0]["sourceTypes"] == ["rss"]
    assert payload[0]["sourceNames"] == ["RSS"]


def test_score_endpoint_recomputes_all_clusters(client, db_session):
    source = _source(db_session, "github_repo", "GitHub", weight=2)
    raw_item = _raw_item(db_session, source, "Repo metrics changed", hours_ago=1)
    cluster = _cluster(db_session, "Repo metrics changed", confidence=70, hours_ago=1)
    _evidence(db_session, cluster, raw_item)

    response = client.post("/api/clusters/score")

    db_session.refresh(cluster)
    assert response.status_code == 200
    assert response.json() == {"clustersScored": 1}
    assert cluster.hot_score > 0
    assert cluster.score_reason_json


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


def _raw_item(db_session, source: Source, title: str, hours_ago: int) -> RawItem:
    seen_at = datetime.now(timezone.utc) - timedelta(hours=hours_ago)
    raw_item = RawItem(
        source_id=source.id,
        external_id=title,
        source_url=f"https://example.com/{title.replace(' ', '-').lower()}",
        title=title,
        content_text=f"{title} body",
        published_at=seen_at,
        raw_payload_json={},
        content_hash=f"hash-{source.id}-{title}",
    )
    db_session.add(raw_item)
    db_session.commit()
    db_session.refresh(raw_item)
    return raw_item


def _cluster(db_session, title: str, confidence: int, hours_ago: int) -> EventCluster:
    seen_at = datetime.now(timezone.utc) - timedelta(hours=hours_ago)
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
