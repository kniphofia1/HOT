from datetime import datetime, timezone

from sqlalchemy import select

from app.db.models import AgentAlert, AgentRunLog, EventCluster


def test_agent_intelligence_generates_alerts_and_follow_up_questions(client, db_session):
    cluster = _cluster(db_session)
    agent = client.post(
        "/api/agents",
        json={
            "name": "OpenAI risk agent",
            "agentType": "risk",
            "scopeJson": {"keywords": ["openai"], "minPropagationScore": 60},
            "cadenceMinutes": 30,
        },
    ).json()

    run = client.post(f"/api/agents/{agent['id']}/run")
    alerts = client.get("/api/agents/alerts")
    runs = client.get("/api/agents/runs")

    assert run.status_code == 200
    assert run.json()["clustersScanned"] == 1
    assert run.json()["alertsCreated"] == 1
    assert alerts.status_code == 200
    alert = alerts.json()[0]
    assert alert["eventClusterId"] == cluster.id
    assert alert["severity"] == "high"
    assert "风险 Agent" in alert["reason"]
    assert len(alert["followUpQuestionsJson"]) >= 3
    assert runs.status_code == 200
    assert runs.json()[0]["status"] == "success"
    assert db_session.scalar(select(AgentAlert)) is not None
    assert db_session.scalar(select(AgentRunLog)) is not None


def test_run_all_agents_deduplicates_existing_alerts(client, db_session):
    _cluster(db_session)
    client.post(
        "/api/agents",
        json={
            "name": "Anomaly agent",
            "agentType": "anomaly",
            "scopeJson": {"minPropagationScore": 60},
        },
    )

    first = client.post("/api/agents/run")
    second = client.post("/api/agents/run")

    assert first.status_code == 200
    assert first.json()[0]["alertsCreated"] == 1
    assert second.status_code == 200
    assert second.json()[0]["alertsCreated"] == 0


def test_agent_alert_status_can_be_updated(client, db_session):
    _cluster(db_session)
    agent = client.post(
        "/api/agents",
        json={"name": "Topic agent", "agentType": "topic", "scopeJson": {"keywords": ["openai"]}},
    ).json()
    client.post(f"/api/agents/{agent['id']}/run")
    alert = client.get("/api/agents/alerts").json()[0]

    updated = client.patch(f"/api/agents/alerts/{alert['id']}", json={"status": "acknowledged"})

    assert updated.status_code == 200
    assert updated.json()["status"] == "acknowledged"


def _cluster(db_session) -> EventCluster:
    cluster = EventCluster(
        title="OpenAI enterprise risk event",
        summary="OpenAI event is spreading across platforms.",
        hot_score=88,
        score_reason_json=[],
        confidence=82,
        event_phase="peaking",
        credibility_score=76,
        propagation_score=84,
        impact_domains_json=["ai_tech", "policy_risk"],
        entities_json=["OpenAI"],
        intelligence_reason_json=[
            {"key": "propagation", "label": "传播速度", "score": 84, "detail": "异常扩散"}
        ],
        first_seen_at=datetime.now(timezone.utc),
        last_seen_at=datetime.now(timezone.utc),
    )
    db_session.add(cluster)
    db_session.commit()
    db_session.refresh(cluster)
    return cluster
