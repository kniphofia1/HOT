from datetime import datetime, timezone
from zipfile import ZipFile
from io import BytesIO

from app.db.models import EventCluster, Evidence, RawItem, Source


def test_commercial_brief_export_contains_intelligence_and_formats(client, db_session):
    cluster = _event_cluster(db_session)
    template = next(item for item in client.get("/api/briefs/templates").json() if item["mode"] == "risk_alert")

    response = client.post(
        "/api/briefs/exports",
        json={
            "templateId": template["id"],
            "title": "风险预警简报",
            "eventClusterIds": [cluster.id],
            "manualNotes": {cluster.id: "需要核实企业客户影响范围。"},
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["briefType"] == "risk_alert"
    assert payload["exportFormatsJson"] == ["markdown", "docx", "print_html"]
    assert "智能判断" in payload["markdown"]
    assert "生命周期" in payload["markdown"]
    assert "OpenAI" in payload["markdown"]
    assert "[Official Blog](https://example.com/openai-risk)" in payload["markdown"]


def test_brief_export_downloads_docx_and_print_html(client, db_session):
    cluster = _event_cluster(db_session)
    template_id = client.get("/api/briefs/templates").json()[0]["id"]
    export = client.post(
        "/api/briefs/exports",
        json={
            "templateId": template_id,
            "title": "交付测试",
            "eventClusterIds": [cluster.id],
            "manualNotes": {},
        },
    ).json()

    docx = client.get(f"/api/briefs/exports/{export['id']}/download/docx")
    html = client.get(f"/api/briefs/exports/{export['id']}/download/html")

    assert docx.status_code == 200
    assert docx.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    with ZipFile(BytesIO(docx.content)) as archive:
        assert "word/document.xml" in archive.namelist()
        assert "交付测试" in archive.read("word/document.xml").decode("utf-8")
    assert html.status_code == 200
    assert html.headers["content-type"].startswith("text/html")
    assert "<h1>交付测试</h1>" in html.text


def test_brief_delivery_outbox_records_external_configuration_requirement(client, db_session):
    cluster = _event_cluster(db_session)
    template_id = client.get("/api/briefs/templates").json()[0]["id"]
    export = client.post(
        "/api/briefs/exports",
        json={
            "templateId": template_id,
            "title": "Slack 交付测试",
            "eventClusterIds": [cluster.id],
            "manualNotes": {},
        },
    ).json()

    created = client.post(
        f"/api/briefs/exports/{export['id']}/deliveries",
        json={"targetType": "slack", "targetLabel": "#intel"},
    )
    listed = client.get(f"/api/briefs/exports/{export['id']}/deliveries")

    assert created.status_code == 201
    payload = created.json()
    assert payload["targetType"] == "slack"
    assert payload["targetLabel"] == "#intel"
    assert payload["status"] == "requires_configuration"
    assert payload["payloadJson"]["formats"] == ["markdown", "docx", "print_html"]
    assert listed.status_code == 200
    assert listed.json()[0]["id"] == payload["id"]


def _event_cluster(db_session) -> EventCluster:
    source = Source(type="rss", name="Official Blog", url="https://example.com/feed", weight=3, config_json={})
    db_session.add(source)
    db_session.commit()
    raw_item = RawItem(
        source_id=source.id,
        external_id="openai-risk",
        source_url="https://example.com/openai-risk",
        title="OpenAI 发布新模型风险说明",
        content_text="OpenAI 发布新模型，并说明企业采用风险。",
        published_at=datetime.now(timezone.utc),
        raw_payload_json={},
        content_hash="hash-openai-risk",
    )
    db_session.add(raw_item)
    db_session.commit()
    cluster = EventCluster(
        title="OpenAI 发布新模型风险说明",
        summary="模型能力提升，但企业采用需要关注安全边界。",
        hot_score=90,
        score_reason_json=[{"key": "recency", "label": "新鲜度", "score": 30, "detail": "最近更新"}],
        confidence=88,
        event_phase="spreading",
        credibility_score=72,
        propagation_score=66,
        impact_domains_json=["ai_tech", "policy_risk"],
        entities_json=["OpenAI"],
        historical_matches_json=[{"clusterId": "history", "title": "历史模型发布", "score": 55}],
        intelligence_reason_json=[
            {"key": "coverage", "label": "跨平台覆盖", "score": 60, "detail": "覆盖多个来源"}
        ],
        first_seen_at=datetime.now(timezone.utc),
        last_seen_at=datetime.now(timezone.utc),
    )
    db_session.add(cluster)
    db_session.commit()
    evidence = Evidence(
        event_cluster_id=cluster.id,
        raw_item_id=raw_item.id,
        source_name="Official Blog",
        source_url="https://example.com/openai-risk",
        quote="OpenAI 发布新模型，并说明企业采用风险。",
        confidence=90,
    )
    db_session.add(evidence)
    db_session.commit()
    db_session.refresh(cluster)
    return cluster
