from datetime import datetime, timezone

from sqlalchemy import select

from app.db.models import BriefExport, EventCluster, Evidence, RawItem, Source


def test_default_brief_templates_are_available(client):
    response = client.get("/api/briefs/templates")

    assert response.status_code == 200
    modes = {template["mode"] for template in response.json()}
    assert modes == {"ai_tech", "investment"}


def test_create_brief_export_contains_summary_reasons_evidence_and_notes(client, db_session):
    cluster = _event_cluster(db_session)
    template_id = client.get("/api/briefs/templates").json()[0]["id"]

    response = client.post(
        "/api/briefs/exports",
        json={
            "templateId": template_id,
            "title": "客户 AI 简报",
            "eventClusterIds": [cluster.id],
            "manualNotes": {cluster.id: "建议持续跟踪企业采用速度。"},
        },
    )

    assert response.status_code == 201
    payload = response.json()
    markdown = payload["markdown"]
    assert "# 客户 AI 简报" in markdown
    assert "生成时间" in markdown
    assert "OpenAI 发布新模型" in markdown
    assert "模型能力显著提升。" in markdown
    assert "新鲜度" in markdown
    assert "建议持续跟踪企业采用速度。" in markdown
    assert "[Official Blog](https://example.com/openai-model)" in markdown
    assert db_session.scalar(select(BriefExport)) is not None


def test_preview_can_be_regenerated_with_edited_notes(client, db_session):
    cluster = _event_cluster(db_session)
    template_id = client.get("/api/briefs/templates").json()[0]["id"]

    first = client.post(
        "/api/briefs/preview",
        json={
            "templateId": template_id,
            "title": "预览简报",
            "eventClusterIds": [cluster.id],
            "manualNotes": {cluster.id: "第一版点评"},
        },
    )
    second = client.post(
        "/api/briefs/preview",
        json={
            "templateId": template_id,
            "title": "预览简报",
            "eventClusterIds": [cluster.id],
            "manualNotes": {cluster.id: "第二版点评"},
        },
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert "第一版点评" in first.json()["markdown"]
    assert "第二版点评" in second.json()["markdown"]


def test_brief_export_degrades_for_empty_evidence_and_bad_links(client, db_session):
    cluster = _event_cluster(db_session, source_url="not-a-url", quote=None)
    template_id = client.get("/api/briefs/templates").json()[0]["id"]

    response = client.post(
        "/api/briefs/exports",
        json={
            "templateId": template_id,
            "title": "中文长标题简报：" + "非常重要" * 20,
            "eventClusterIds": [cluster.id],
            "manualNotes": {},
        },
    )

    assert response.status_code == 201
    markdown = response.json()["markdown"]
    assert "Official Blog：暂无引用片段。" in markdown
    assert "暂无人工点评。" in markdown


def test_download_brief_export_returns_markdown(client, db_session):
    cluster = _event_cluster(db_session)
    template_id = client.get("/api/briefs/templates").json()[0]["id"]
    export = client.post(
        "/api/briefs/exports",
        json={
            "templateId": template_id,
            "title": "下载测试",
            "eventClusterIds": [cluster.id],
            "manualNotes": {},
        },
    ).json()

    response = client.get(f"/api/briefs/exports/{export['id']}/download")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/markdown")
    assert "attachment" in response.headers["content-disposition"]
    assert "# 下载测试" in response.text


def _event_cluster(db_session, source_url: str = "https://example.com/openai-model", quote: str | None = "官方发布内容") -> EventCluster:
    source = Source(type="rss", name="Official Blog", url="https://example.com/feed", weight=3, config_json={})
    db_session.add(source)
    db_session.commit()
    raw_item = RawItem(
        source_id=source.id,
        external_id="openai-model",
        source_url=source_url,
        title="OpenAI 发布新模型",
        content_text="模型能力显著提升。",
        published_at=datetime.now(timezone.utc),
        raw_payload_json={},
        content_hash=f"hash-{source_url}-{quote}",
    )
    db_session.add(raw_item)
    db_session.commit()
    cluster = EventCluster(
        title="OpenAI 发布新模型",
        summary="模型能力显著提升。",
        hot_score=88,
        score_reason_json=[{"key": "recency", "label": "新鲜度", "score": 30, "detail": "最近更新"}],
        confidence=90,
        first_seen_at=datetime.now(timezone.utc),
        last_seen_at=datetime.now(timezone.utc),
    )
    db_session.add(cluster)
    db_session.commit()
    evidence = Evidence(
        event_cluster_id=cluster.id,
        raw_item_id=raw_item.id,
        source_name="Official Blog",
        source_url=source_url,
        quote=quote,
        confidence=90,
    )
    db_session.add(evidence)
    db_session.commit()
    db_session.refresh(cluster)
    return cluster
