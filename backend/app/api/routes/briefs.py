from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import BriefExport, BriefTemplate
from app.db.session import get_db
from app.services.brief_exporter import (
    create_brief_export,
    ensure_default_templates,
    preview_markdown,
)


router = APIRouter(prefix="/api/briefs", tags=["briefs"])


class BriefTemplateRead(BaseModel):
    id: str
    name: str
    mode: str
    sections_json: list = Field(alias="sectionsJson")
    style_rules: str | None = Field(alias="styleRules")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class BriefExportCreate(BaseModel):
    template_id: str = Field(alias="templateId")
    title: str
    event_cluster_ids: list[str] = Field(alias="eventClusterIds")
    manual_notes: dict[str, str] = Field(default_factory=dict, alias="manualNotes")

    model_config = ConfigDict(populate_by_name=True)


class BriefPreviewRead(BaseModel):
    markdown: str


class BriefExportRead(BaseModel):
    id: str
    template_id: str = Field(alias="templateId")
    title: str
    event_cluster_ids_json: list[str] = Field(alias="eventClusterIdsJson")
    manual_notes_json: dict[str, Any] = Field(alias="manualNotesJson")
    markdown: str
    generated_at: datetime = Field(alias="generatedAt")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


@router.get("/templates", response_model=list[BriefTemplateRead])
def list_templates(db: Session = Depends(get_db)) -> list[BriefTemplate]:
    return ensure_default_templates(db)


@router.post("/preview", response_model=BriefPreviewRead)
def preview_brief(payload: BriefExportCreate, db: Session = Depends(get_db)) -> dict[str, str]:
    try:
        markdown = preview_markdown(
            db,
            template_id=payload.template_id,
            title=payload.title,
            event_cluster_ids=payload.event_cluster_ids,
            manual_notes=payload.manual_notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return {"markdown": markdown}


@router.post("/exports", response_model=BriefExportRead, status_code=status.HTTP_201_CREATED)
def create_export(payload: BriefExportCreate, db: Session = Depends(get_db)) -> BriefExport:
    try:
        return create_brief_export(
            db,
            template_id=payload.template_id,
            title=payload.title,
            event_cluster_ids=payload.event_cluster_ids,
            manual_notes=payload.manual_notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/exports", response_model=list[BriefExportRead])
def list_exports(db: Session = Depends(get_db)) -> list[BriefExport]:
    return list(db.scalars(select(BriefExport).order_by(BriefExport.generated_at.desc())).all())


@router.get("/exports/{export_id}", response_model=BriefExportRead)
def get_export(export_id: str, db: Session = Depends(get_db)) -> BriefExport:
    export = db.get(BriefExport, export_id)
    if export is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="BriefExport not found")
    return export


@router.get("/exports/{export_id}/download")
def download_export(export_id: str, db: Session = Depends(get_db)) -> Response:
    export = db.get(BriefExport, export_id)
    if export is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="BriefExport not found")
    filename = f"{_safe_filename(export.title)}.md"
    return Response(
        content=export.markdown,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _safe_filename(value: str) -> str:
    safe = "".join(
        char if char.isascii() and (char.isalnum() or char in {"-", "_"}) else "-"
        for char in value.strip()
    )
    return safe.strip("-") or "brief"
