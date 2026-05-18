from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.db.models import BriefExport, BriefTemplate, EventCluster, Evidence, FeedbackEntry, RawItem, Source


def test_public_items_returns_selected_timeline_with_media(client, db_session):
    published_at = datetime(2026, 5, 10, 9, 0, tzinfo=timezone.utc)
    cluster = _cluster(db_session, title="OpenAI releases new voice model", score=71, tags=["模型发布"])
    raw_item = _raw_item(
        db_session,
        title="OpenAI voice model",
        published_at=published_at,
        payload={
            "author": {"avatar": "https://cdn.example.com/avatar.jpg"},
            "media": [{"url": "https://cdn.example.com/voice-model.png"}],
        },
    )
    _evidence(db_session, cluster, raw_item)
    db_session.commit()

    response = client.get("/api/public/items?mode=selected&category=ai-models")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    item = payload["items"][0]
    assert item["displayTitle"] == "OpenAI releases new voice model"
    assert item["selected"] is True
    assert item["category"] == "ai-models"
    assert item["avatarUrl"] == "https://cdn.example.com/avatar.jpg"
    assert item["mediaUrls"] == ["https://cdn.example.com/voice-model.png"]
    assert item["publishedAt"].startswith("2026-05-10T09:00:00")
    assert item["displayedAt"] == item["publishedAt"]
    assert item["timeBasis"] == "source_published"


def test_public_items_filters_search_and_mode(client, db_session):
    selected = _cluster(db_session, title="Claude Code workflow", score=66, tags=["教程/实践"])
    hidden = _cluster(db_session, title="Small source note", score=20)
    _evidence(db_session, selected, _raw_item(db_session, title="Claude Code workflow"))
    _evidence(db_session, hidden, _raw_item(db_session, title="Small source note"))
    db_session.commit()

    selected_response = client.get("/api/public/items?mode=selected&q=Claude")
    all_response = client.get("/api/public/items?mode=all")

    assert selected_response.status_code == 200
    assert selected_response.json()["total"] == 1
    assert all_response.status_code == 200
    assert all_response.json()["total"] == 2


def test_public_items_do_not_select_generic_page_noise(client, db_session):
    cluster = _cluster(db_session, title="Generic website page overview", score=59)
    cluster.score_reason_json = [
        {"key": "source_authority", "score": 10, "detail": "official source"},
        {"key": "noise_penalty", "score": -20, "detail": "generic page"},
    ]
    _evidence(db_session, cluster, _raw_item(db_session, title="Generic website page overview"))
    db_session.commit()

    response = client.get("/api/public/items?mode=selected")

    assert response.status_code == 200
    assert response.json()["total"] == 0


def test_public_items_filters_by_industry_from_evidence_source(client, db_session):
    compute = _cluster(db_session, title="NVIDIA expands AI datacenter capacity", score=70)
    robot = _cluster(db_session, title="Figure AI ships humanoid robot update", score=70)
    _evidence(
        db_session,
        compute,
        _raw_item(
            db_session,
            title="NVIDIA datacenter capacity",
            source_config={"industry": "semiconductor"},
        ),
    )
    _evidence(
        db_session,
        robot,
        _raw_item(
            db_session,
            title="Figure humanoid robot",
            source_config={"industry": "embodied_ai"},
        ),
    )
    db_session.commit()

    response = client.get("/api/public/items?mode=all&industry=embodied_ai")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    item = payload["items"][0]
    assert item["displayTitle"] == "Figure AI ships humanoid robot update"
    assert item["industries"] == ["embodied_ai"]
    assert item["industryLabels"] == ["具身智能"]


def test_public_items_filter_uses_single_primary_industry_over_impact_domains(client, db_session):
    cluster = _cluster(db_session, title="Rust 1.90 release improves compiler tooling", score=70)
    cluster.primary_industry = "technology"
    cluster.related_industries_json = ["products"]
    cluster.impact_domains_json = ["ai_tech", "product_business"]
    _evidence(db_session, cluster, _raw_item(db_session, title="Rust compiler release"))
    db_session.commit()

    tech_response = client.get("/api/public/items?mode=all&industry=technology")
    ai_response = client.get("/api/public/items?mode=all&industry=ai")

    assert tech_response.status_code == 200
    assert tech_response.json()["total"] == 1
    item = tech_response.json()["items"][0]
    assert item["industries"] == ["technology"]
    assert item["industryLabels"] == ["技术"]
    assert item["relatedIndustryLabels"] == ["产品"]
    assert ai_response.status_code == 200
    assert ai_response.json()["total"] == 0


def test_public_items_order_by_source_published_time(client, db_session):
    older_cluster = _cluster(db_session, title="Older high score", score=90)
    newer_cluster = _cluster(db_session, title="Newer lower score", score=66)
    _evidence(
        db_session,
        older_cluster,
        _raw_item(db_session, title="Older high score", published_at=datetime(2026, 5, 10, 8, 0, tzinfo=timezone.utc)),
    )
    _evidence(
        db_session,
        newer_cluster,
        _raw_item(db_session, title="Newer lower score", published_at=datetime(2026, 5, 10, 10, 0, tzinfo=timezone.utc)),
    )
    db_session.commit()

    response = client.get("/api/public/items?mode=selected")

    assert response.status_code == 200
    titles = [item["displayTitle"] for item in response.json()["items"]]
    assert titles[:2] == ["Newer lower score", "Older high score"]


def test_public_daily_falls_back_to_cluster_sections(client, db_session):
    now = datetime.now(timezone.utc)
    cluster = _cluster(db_session, title="New AI product launch", score=80, tags=["产品更新"])
    cluster.last_seen_at = now
    _evidence(db_session, cluster, _raw_item(db_session, title="New AI product launch", published_at=now))
    db_session.commit()

    response = client.get(f"/api/public/daily?date={now.date().isoformat()}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["storyCount"] == 1
    assert payload["sections"][0]["key"] == "ai-products"
    assert payload["archive"][0]["date"] == now.date().isoformat()


def test_public_daily_uses_brief_export_when_available(client, db_session):
    now = datetime.now(timezone.utc)
    cluster = _cluster(db_session, title="Daily model item", score=80, tags=["模型"])
    _evidence(db_session, cluster, _raw_item(db_session, title="Daily model item", published_at=now))
    template = BriefTemplate(name="AI 日报", mode="daily", sections_json=["summary"])
    db_session.add(template)
    db_session.flush()
    export = BriefExport(
        template_id=template.id,
        title="AI HOT 日报",
        brief_type="ai_daily",
        event_cluster_ids_json=[cluster.id],
        manual_notes_json={},
        export_formats_json=["markdown"],
        delivery_targets_json=[],
        markdown="# AI HOT 日报",
        generated_at=now,
    )
    db_session.add(export)
    db_session.commit()

    response = client.get(f"/api/public/daily?date={now.date().isoformat()}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["title"] == "AI HOT 日报"
    assert payload["markdown"] == "# AI HOT 日报"
    assert payload["storyCount"] == 1


def test_feedback_is_saved_locally(client, db_session):
    response = client.post("/api/feedback", json={"message": "希望增加日报导出", "contact": "user@example.com"})

    assert response.status_code == 201
    saved = db_session.scalar(select(FeedbackEntry))
    assert saved is not None
    assert saved.message == "希望增加日报导出"
    assert saved.contact == "user@example.com"
    assert saved.status == "new"


def test_feedback_rejects_blank_message(client):
    response = client.post("/api/feedback", json={"message": "   ", "contact": "user@example.com"})

    assert response.status_code == 422


def _cluster(db_session, *, title: str, score: int, tags: list[str] | None = None) -> EventCluster:
    now = datetime.now(timezone.utc) - timedelta(minutes=5)
    cluster = EventCluster(
        title=title,
        summary=f"{title} summary",
        hot_score=score,
        score_reason_json=[{"key": "hot", "label": "热度", "score": score, "detail": "热度达到精选阈值"}],
        confidence=80,
        first_seen_at=now,
        last_seen_at=now,
        editorial_tags_json=tags or [],
        editorial_priority=1 if score >= 60 else 0,
        intelligence_reason_json=[{"key": "reason", "label": "推荐", "score": score, "detail": "值得关注"}],
        impact_domains_json=[],
        entities_json=[],
        historical_matches_json=[],
    )
    db_session.add(cluster)
    db_session.flush()
    return cluster


def _raw_item(
    db_session,
    *,
    title: str,
    payload: dict | None = None,
    published_at: datetime | None = None,
    source_config: dict | None = None,
) -> RawItem:
    source = Source(
        type="rss",
        name="OpenAI Blog",
        url="https://example.com/feed.xml",
        enabled=True,
        weight=3,
        poll_interval_minutes=60,
        config_json=source_config or {},
    )
    db_session.add(source)
    db_session.flush()
    raw_item = RawItem(
        source_id=source.id,
        external_id=title,
        source_url="https://example.com/item",
        title=title,
        content_text=f"{title} content",
        author="OpenAI",
        published_at=published_at or datetime.now(timezone.utc),
        raw_payload_json=payload or {},
        content_hash=f"hash-{source.id}-{title}",
    )
    db_session.add(raw_item)
    db_session.flush()
    return raw_item


def _evidence(db_session, cluster: EventCluster, raw_item: RawItem) -> Evidence:
    evidence = Evidence(
        event_cluster_id=cluster.id,
        raw_item_id=raw_item.id,
        source_name="OpenAI Blog",
        source_url=raw_item.source_url or "https://example.com/item",
        quote="quoted evidence",
        confidence=80,
    )
    db_session.add(evidence)
    db_session.flush()
    return evidence
