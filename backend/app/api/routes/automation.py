from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.db.models import AutomationRunLog, AutomationSchedule
from app.db.session import get_db
from app.services.automation import (
    ensure_default_schedules,
    list_automation_runs,
    run_automation_task,
    update_automation_settings,
)


router = APIRouter(prefix="/api/automation", tags=["automation"])


class AutomationScheduleRead(BaseModel):
    id: str
    task_type: str = Field(alias="taskType")
    enabled: bool
    timezone: str
    run_time: str | None = Field(alias="runTime")
    cadence_minutes: int = Field(alias="cadenceMinutes")
    config_json: dict[str, Any] = Field(alias="configJson")
    last_run_at: datetime | None = Field(alias="lastRunAt")
    next_run_at: datetime | None = Field(alias="nextRunAt")
    last_error: str | None = Field(alias="lastError")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class AutomationSettingsRead(BaseModel):
    schedules: list[AutomationScheduleRead]


class AutomationSettingsUpdate(BaseModel):
    source_refresh_enabled: bool | None = Field(default=None, alias="sourceRefreshEnabled")
    daily_reports_enabled: bool | None = Field(default=None, alias="dailyReportsEnabled")
    daily_run_time: str | None = Field(default=None, alias="dailyRunTime", pattern=r"^\d{2}:\d{2}$")
    timezone: str | None = None
    global_max_events: int | None = Field(default=None, alias="globalMaxEvents", ge=1, le=100)
    industry_max_events: int | None = Field(default=None, alias="industryMaxEvents", ge=1, le=50)

    model_config = ConfigDict(populate_by_name=True)


class AutomationRunRequest(BaseModel):
    task: Literal["source_refresh", "daily_reports", "all"] = "all"


class AutomationRunResultRead(BaseModel):
    task_type: str = Field(alias="taskType")
    status: str
    payload: dict[str, Any]
    error: str | None = None

    model_config = ConfigDict(populate_by_name=True)


class AutomationRunLogRead(BaseModel):
    id: str
    task_type: str = Field(alias="taskType")
    status: str
    started_at: datetime = Field(alias="startedAt")
    finished_at: datetime | None = Field(alias="finishedAt")
    payload_json: dict[str, Any] = Field(alias="payloadJson")
    error_message: str | None = Field(alias="errorMessage")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


@router.get("/settings", response_model=AutomationSettingsRead)
def get_automation_settings(db: Session = Depends(get_db)) -> dict[str, list[AutomationSchedule]]:
    return {"schedules": ensure_default_schedules(db)}


@router.patch("/settings", response_model=AutomationSettingsRead)
def patch_automation_settings(
    payload: AutomationSettingsUpdate,
    db: Session = Depends(get_db),
) -> dict[str, list[AutomationSchedule]]:
    try:
        schedules = update_automation_settings(
            db,
            source_refresh_enabled=payload.source_refresh_enabled,
            daily_reports_enabled=payload.daily_reports_enabled,
            daily_run_time=payload.daily_run_time,
            timezone_name=payload.timezone,
            global_max_events=payload.global_max_events,
            industry_max_events=payload.industry_max_events,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return {"schedules": schedules}


@router.post("/run", response_model=AutomationRunResultRead)
def run_automation(
    payload: AutomationRunRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    try:
        result = run_automation_task(db, payload.task)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return {
        "taskType": result.task_type,
        "status": result.status,
        "payload": result.payload,
        "error": result.error,
    }


@router.get("/runs", response_model=list[AutomationRunLogRead])
def list_runs(
    take: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[AutomationRunLog]:
    return list_automation_runs(db, take=take)
