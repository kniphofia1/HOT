from __future__ import annotations

from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.report_center import ReportRequest, generate_report_export


router = APIRouter(prefix="/api/reports", tags=["reports"])


class ReportGenerateCreate(BaseModel):
    industry: str
    time_range: str = Field(alias="timeRange")
    start_date: date | None = Field(default=None, alias="startDate")
    end_date: date | None = Field(default=None, alias="endDate")
    report_type: str = Field(alias="reportType")
    modules: list[str] = Field(default_factory=list)
    output_format: str = Field(default="markdown", alias="outputFormat")
    style: str = "consulting"

    model_config = ConfigDict(populate_by_name=True)


class ReportGenerateRead(BaseModel):
    export_id: str = Field(alias="exportId")
    title: str
    markdown: str
    event_cluster_ids: list[str] = Field(alias="eventClusterIds")
    generated_at: datetime = Field(alias="generatedAt")
    ai_status: str = Field(alias="aiStatus")
    ai_error: str | None = Field(alias="aiError")

    model_config = ConfigDict(populate_by_name=True)


@router.post("/generate", response_model=ReportGenerateRead, status_code=status.HTTP_201_CREATED)
def generate_report(payload: ReportGenerateCreate, db: Session = Depends(get_db)) -> dict[str, Any]:
    try:
        result = generate_report_export(
            db,
            ReportRequest(
                industry=payload.industry,
                time_range=payload.time_range,
                start_date=payload.start_date,
                end_date=payload.end_date,
                report_type=payload.report_type,
                modules=payload.modules,
                output_format=payload.output_format,
                style=payload.style,
            ),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {
        "exportId": result.export.id,
        "title": result.export.title,
        "markdown": result.markdown,
        "eventClusterIds": result.event_cluster_ids,
        "generatedAt": result.generated_at,
        "aiStatus": result.ai_status,
        "aiError": result.ai_error,
    }
