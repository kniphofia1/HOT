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
        "ai_relevance",
        "strategic_importance",
        "novelty",
        "source_authority",
        "actionability",
        "technical_density",
        "discussion_signal",
        "audience_fit",
    }


def test_value_dense_event_beats_vague_fresh_chatter(db_session):
    rss_source = _source(db_session, "rss", "RSS", weight=2)
    social_source = _source(db_session, "x_recent_search", "X", weight=3)

    valuable_item = _raw_item(
        db_session,
        rss_source,
        "OpenAI launches Responses API batch pricing update",
        hours_ago=20,
        content_text=(
            "OpenAI launched a Responses API batch processing update with pricing details, "
            "SDK examples, developer workflow migration notes, and enterprise rollout guidance."
        ),
    )
    valuable_cluster = _cluster(
        db_session,
        "OpenAI launches Responses API batch pricing update",
        confidence=75,
        hours_ago=20,
    )
    _evidence(db_session, valuable_cluster, valuable_item)

    vague_item = _raw_item(
        db_session,
        social_source,
        "AI is getting interesting again",
        hours_ago=1,
        content_text="Interesting thoughts on AI. What do you think?",
    )
    vague_cluster = _cluster(db_session, "AI is getting interesting again", confidence=95, hours_ago=1)
    _evidence(db_session, vague_cluster, vague_item)

    recompute_hot_scores(db_session)

    db_session.refresh(valuable_cluster)
    db_session.refresh(vague_cluster)
    assert valuable_cluster.hot_score > vague_cluster.hot_score
    assert valuable_cluster.hot_score >= 60
    assert vague_cluster.hot_score < 60
    assert any(reason["key"].endswith("_penalty") for reason in vague_cluster.score_reason_json)


def test_personal_social_badge_is_not_selected_as_high_value_signal(db_session):
    social_source = _source(db_session, "bluesky_search", "Bluesky", weight=3)
    raw_item = _raw_item(
        db_session,
        social_source,
        "MicrosoftLearn achievement badge for AI identity risk course",
        hours_ago=1,
        content_text=(
            "Day 130 MicrosoftLearn achievement badge: Analyze AI identity risks using "
            "Microsoft Defender XDR. #AlwaysLearning #MSLearnBadge"
        ),
    )
    cluster = _cluster(
        db_session,
        "MicrosoftLearn achievement badge for AI identity risk course",
        confidence=92,
        hours_ago=1,
    )
    _evidence(db_session, cluster, raw_item)

    recompute_hot_scores(db_session)

    db_session.refresh(cluster)
    assert cluster.hot_score < 60
    assert any(reason["key"].endswith("_penalty") for reason in cluster.score_reason_json)


def test_generic_homepage_scrape_gets_noise_penalty(db_session):
    source = _source(db_session, "webpage", "ASML News", weight=4)
    raw_item = _raw_item(
        db_session,
        source,
        "ASML News",
        hours_ago=1,
        content_text=(
            "News | ASML - Supplying the semiconductor industry. Skip to main content. "
            "Saved jobs. Board of Directors. Policies and Guidelines. Search jobs."
        ),
    )
    cluster = _cluster(db_session, "ASML News", confidence=80, hours_ago=1)
    _evidence(db_session, cluster, raw_item)

    recompute_hot_scores(db_session)

    db_session.refresh(cluster)
    assert cluster.hot_score < 55
    assert any(reason["key"] == "noise_penalty" for reason in cluster.score_reason_json)


def test_broad_ai_source_does_not_lift_consumer_electronics_noise(db_session):
    source = _source(db_session, "rss", "IT之家 RSS", weight=3)
    source.config_json = {"industry": "ai", "industries": ["ai"], "sourceTier": "P0"}
    raw_item = _raw_item(
        db_session,
        source,
        "New mechanical keyboard and smartphone accessory launch",
        hours_ago=1,
        content_text="Consumer electronics update: a phone accessory, keyboard, earbuds, and camera lens are now on sale.",
    )
    cluster = _cluster(db_session, "New mechanical keyboard and smartphone accessory launch", confidence=80, hours_ago=1)
    _evidence(db_session, cluster, raw_item)

    recompute_hot_scores(db_session)

    db_session.refresh(cluster)
    assert cluster.hot_score < 55
    assert any(reason["key"] == "off_topic_penalty" for reason in cluster.score_reason_json)


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


def test_cluster_list_returns_primary_source_and_other_source_type_count(client, db_session):
    rss_source = _source(db_session, "rss", "RSS", weight=1)
    hn_source = _source(db_session, "hacker_news", "HN", weight=3)
    github_source = _source(db_session, "github_repo", "GitHub", weight=3)
    cluster = _cluster(db_session, "Multi source event", confidence=88, hours_ago=1)
    cluster.hot_score = 80
    cluster.score_reason_json = [{"key": "sourceWeight", "score": 20, "detail": "多平台报道"}]

    _evidence(db_session, cluster, _raw_item(db_session, rss_source, "RSS report", hours_ago=1))
    _evidence(db_session, cluster, _raw_item(db_session, hn_source, "HN report", hours_ago=3))
    _evidence(db_session, cluster, _raw_item(db_session, github_source, "GitHub report", hours_ago=2))
    db_session.commit()

    response = client.get("/api/clusters?sort=score")

    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["id"] == cluster.id
    assert payload[0]["primarySourceName"] == "GitHub"
    assert payload[0]["primarySourceType"] == "github_repo"
    assert payload[0]["otherSourceTypeCount"] == 2


def test_score_endpoint_recomputes_all_clusters(client, db_session):
    source = _source(db_session, "github_repo", "GitHub", weight=2)
    raw_item = _raw_item(db_session, source, "OpenAI agent SDK repo metrics changed", hours_ago=1)
    cluster = _cluster(db_session, "OpenAI agent SDK repo metrics changed", confidence=70, hours_ago=1)
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


def _raw_item(
    db_session,
    source: Source,
    title: str,
    hours_ago: int,
    content_text: str | None = None,
) -> RawItem:
    seen_at = datetime.now(timezone.utc) - timedelta(hours=hours_ago)
    raw_item = RawItem(
        source_id=source.id,
        external_id=title,
        source_url=f"https://example.com/{title.replace(' ', '-').lower()}",
        title=title,
        content_text=content_text or f"{title} body",
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
