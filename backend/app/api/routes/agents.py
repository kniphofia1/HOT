from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import AgentAlert, AgentRunLog, IntelligenceAgent, Organization
from app.db.session import get_db
from app.services.agent_intelligence import AgentRunResult, run_agent, run_enabled_agents


router = APIRouter(prefix="/api/agents", tags=["agents"])


class IntelligenceAgentCreate(BaseModel):
    organization_id: str | None = Field(default=None, alias="organizationId")
    name: str
    agent_type: str = Field(alias="agentType")
    scope_json: dict[str, Any] = Field(default_factory=dict, alias="scopeJson")
    enabled: bool = True
    cadence_minutes: int = Field(default=60, alias="cadenceMinutes")

    model_config = ConfigDict(populate_by_name=True)


class IntelligenceAgentRead(BaseModel):
    id: str
    organization_id: str | None = Field(alias="organizationId")
    name: str
    agent_type: str = Field(alias="agentType")
    scope_json: dict[str, Any] = Field(alias="scopeJson")
    enabled: bool
    cadence_minutes: int = Field(alias="cadenceMinutes")
    last_run_at: datetime | None = Field(alias="lastRunAt")
    created_at: datetime = Field(alias="createdAt")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class AgentRunRead(BaseModel):
    status: str
    clusters_scanned: int = Field(alias="clustersScanned")
    alerts_created: int = Field(alias="alertsCreated")
    error_message: str | None = Field(alias="errorMessage")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class AgentAlertUpdate(BaseModel):
    status: str


class AgentAlertRead(BaseModel):
    id: str
    agent_id: str = Field(alias="agentId")
    event_cluster_id: str = Field(alias="eventClusterId")
    severity: str
    title: str
    reason: str
    follow_up_questions_json: list[str] = Field(alias="followUpQuestionsJson")
    status: str
    created_at: datetime = Field(alias="createdAt")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class AgentRunLogRead(BaseModel):
    id: str
    agent_id: str = Field(alias="agentId")
    status: str
    clusters_scanned: int = Field(alias="clustersScanned")
    alerts_created: int = Field(alias="alertsCreated")
    error_message: str | None = Field(alias="errorMessage")
    created_at: datetime = Field(alias="createdAt")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


@router.get("", response_model=list[IntelligenceAgentRead])
def list_agents(db: Session = Depends(get_db)) -> list[IntelligenceAgent]:
    return list(db.scalars(select(IntelligenceAgent).order_by(IntelligenceAgent.created_at.desc())).all())


@router.post("", response_model=IntelligenceAgentRead, status_code=status.HTTP_201_CREATED)
def create_agent(payload: IntelligenceAgentCreate, db: Session = Depends(get_db)) -> IntelligenceAgent:
    if payload.organization_id and db.get(Organization, payload.organization_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    agent = IntelligenceAgent(
        organization_id=payload.organization_id,
        name=payload.name.strip(),
        agent_type=payload.agent_type.strip(),
        scope_json=payload.scope_json,
        enabled=payload.enabled,
        cadence_minutes=payload.cadence_minutes,
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent


@router.post("/run", response_model=list[AgentRunRead])
def run_all_agents(
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[AgentRunResult]:
    return run_enabled_agents(db, limit=limit)


@router.post("/{agent_id}/run", response_model=AgentRunRead)
def run_single_agent(
    agent_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> AgentRunResult:
    agent = db.get(IntelligenceAgent, agent_id)
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="IntelligenceAgent not found")
    return run_agent(db, agent, limit=limit)


@router.get("/alerts", response_model=list[AgentAlertRead])
def list_alerts(db: Session = Depends(get_db)) -> list[AgentAlert]:
    return list(db.scalars(select(AgentAlert).order_by(AgentAlert.created_at.desc())).all())


@router.patch("/alerts/{alert_id}", response_model=AgentAlertRead)
def update_alert(alert_id: str, payload: AgentAlertUpdate, db: Session = Depends(get_db)) -> AgentAlert:
    alert = db.get(AgentAlert, alert_id)
    if alert is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AgentAlert not found")
    alert.status = payload.status
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert


@router.get("/runs", response_model=list[AgentRunLogRead])
def list_agent_runs(db: Session = Depends(get_db)) -> list[AgentRunLog]:
    return list(db.scalars(select(AgentRunLog).order_by(AgentRunLog.created_at.desc()).limit(100)).all())
