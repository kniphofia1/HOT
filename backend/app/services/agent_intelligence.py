from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import AgentAlert, AgentRunLog, EventCluster, IntelligenceAgent


@dataclass(frozen=True)
class AgentRunResult:
    status: str
    clusters_scanned: int
    alerts_created: int
    error_message: str | None = None


def run_enabled_agents(db: Session, limit: int = 100) -> list[AgentRunResult]:
    agents = db.scalars(select(IntelligenceAgent).where(IntelligenceAgent.enabled.is_(True))).all()
    return [run_agent(db, agent, limit=limit) for agent in agents]


def run_agent(db: Session, agent: IntelligenceAgent, limit: int = 100) -> AgentRunResult:
    clusters = list(
        db.scalars(
            select(EventCluster)
            .order_by(EventCluster.last_seen_at.desc().nullslast(), EventCluster.hot_score.desc())
            .limit(limit)
        ).all()
    )
    alerts_created = 0
    try:
        for cluster in clusters:
            match = _match_agent(agent, cluster)
            if match is None:
                continue
            if _alert_exists(db, agent.id, cluster.id):
                continue
            alert = AgentAlert(
                agent_id=agent.id,
                event_cluster_id=cluster.id,
                severity=match["severity"],
                title=cluster.editorial_title or cluster.translated_title or cluster.title,
                reason=match["reason"],
                follow_up_questions_json=_follow_up_questions(agent, cluster),
                status="open",
            )
            db.add(alert)
            alerts_created += 1
        agent.last_run_at = datetime.now(timezone.utc)
        db.add(agent)
        db.add(
            AgentRunLog(
                agent_id=agent.id,
                status="success",
                clusters_scanned=len(clusters),
                alerts_created=alerts_created,
            )
        )
        db.commit()
        return AgentRunResult("success", len(clusters), alerts_created)
    except Exception as exc:  # noqa: BLE001 - an agent failure should be recorded and isolated.
        db.add(
            AgentRunLog(
                agent_id=agent.id,
                status="failed",
                clusters_scanned=len(clusters),
                alerts_created=alerts_created,
                error_message=str(exc),
            )
        )
        db.commit()
        return AgentRunResult("failed", len(clusters), alerts_created, str(exc))


def _match_agent(agent: IntelligenceAgent, cluster: EventCluster) -> dict[str, str] | None:
    scope = agent.scope_json or {}
    text = _cluster_text(cluster).lower()
    keywords = [str(item).lower() for item in scope.get("keywords", [])]
    entities = [str(item) for item in scope.get("entities", [])]
    domains = [str(item) for item in scope.get("domains", [])]
    min_score = int(scope.get("minHotScore", 0) or 0)
    min_propagation = int(scope.get("minPropagationScore", 0) or 0)
    if cluster.hot_score < min_score or cluster.propagation_score < min_propagation:
        return None

    matched_keyword = next((keyword for keyword in keywords if keyword in text), None)
    matched_entity = next((entity for entity in entities if entity in (cluster.entities_json or [])), None)
    matched_domain = next((domain for domain in domains if domain in (cluster.impact_domains_json or [])), None)

    if agent.agent_type in {"topic", "company", "competitor", "investment"}:
        if matched_keyword or matched_entity or matched_domain:
            return {
                "severity": _severity(cluster),
                "reason": _reason(agent, cluster, matched_keyword, matched_entity, matched_domain),
            }
        return None

    if agent.agent_type == "risk":
        risk_domain = "policy_risk" in (cluster.impact_domains_json or [])
        risky_phase = cluster.event_phase in {"spreading", "peaking"}
        if risk_domain or risky_phase or matched_keyword:
            return {
                "severity": _severity(cluster),
                "reason": f"风险 Agent 发现 {cluster.event_phase or 'unknown'} 阶段事件，可信度 {cluster.credibility_score}，传播 {cluster.propagation_score}。",
            }
        return None

    if agent.agent_type == "anomaly":
        if cluster.event_phase in {"spreading", "peaking"} and cluster.propagation_score >= max(min_propagation, 60):
            return {
                "severity": _severity(cluster),
                "reason": f"异常扩散：事件处于 {cluster.event_phase}，传播速度 {cluster.propagation_score}，热度 {cluster.hot_score}。",
            }
    return None


def _follow_up_questions(agent: IntelligenceAgent, cluster: EventCluster) -> list[str]:
    entities = cluster.entities_json or ["该主体"]
    entity = entities[0]
    return [
        f"{entity} 是否会受到这个事件的一阶影响？",
        "当前 Evidence 是否足够支撑简报判断？",
        "是否需要追加官方来源或人工标注？",
        f"这个事件在 {cluster.event_phase or '当前阶段'} 后是否可能继续扩散？",
        f"{agent.name} 是否需要触发风险预警或商业简报？",
    ]


def _reason(
    agent: IntelligenceAgent,
    cluster: EventCluster,
    keyword: str | None,
    entity: str | None,
    domain: str | None,
) -> str:
    matched = keyword or entity or domain or "scope"
    return (
        f"{agent.name} 命中 {matched}；事件阶段 {cluster.event_phase or 'unknown'}，"
        f"热度 {cluster.hot_score}，可信度 {cluster.credibility_score}，传播 {cluster.propagation_score}。"
    )


def _severity(cluster: EventCluster) -> str:
    if cluster.hot_score >= 85 or cluster.propagation_score >= 80:
        return "high"
    if cluster.hot_score >= 65 or cluster.propagation_score >= 55:
        return "medium"
    return "low"


def _cluster_text(cluster: EventCluster) -> str:
    return " ".join(
        [
            cluster.title,
            cluster.summary or "",
            " ".join(cluster.entities_json or []),
            " ".join(cluster.impact_domains_json or []),
        ]
    )


def _alert_exists(db: Session, agent_id: str, cluster_id: str) -> bool:
    return (
        db.scalar(
            select(AgentAlert.id)
            .where(AgentAlert.agent_id == agent_id)
            .where(AgentAlert.event_cluster_id == cluster_id)
            .limit(1)
        )
        is not None
    )
