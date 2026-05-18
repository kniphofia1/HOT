from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import BriefDelivery, BriefExport, BriefTemplate
from app.db.session import get_db
from app.services.brief_delivery import create_delivery
from app.services.brief_exporter import (
    create_brief_export,
    ensure_default_templates,
    preview_markdown,
)
from app.services.brief_renderers import render_markdown_docx, render_markdown_html


router = APIRouter(prefix="/api/briefs", tags=["briefs"])


class BriefTemplateRead(BaseModel):
    id: str
    name: str
    mode: str
    sections_json: list = Field(alias="sectionsJson")
    style_rules: str | None = Field(alias="styleRules")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class BriefTemplateUpdate(BaseModel):
    name: str | None = None
    sections_json: list[str] | None = Field(default=None, alias="sectionsJson")
    style_rules: str | None = Field(default=None, alias="styleRules")

    model_config = ConfigDict(populate_by_name=True)


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
    brief_type: str | None = Field(alias="briefType")
    scope_type: str = Field(alias="scopeType")
    scope_key: str = Field(alias="scopeKey")
    report_date: date | None = Field(alias="reportDate")
    is_public: bool = Field(alias="isPublic")
    event_cluster_ids_json: list[str] = Field(alias="eventClusterIdsJson")
    manual_notes_json: dict[str, Any] = Field(alias="manualNotesJson")
    export_formats_json: list[str] = Field(alias="exportFormatsJson")
    delivery_targets_json: list = Field(alias="deliveryTargetsJson")
    markdown: str
    generated_at: datetime = Field(alias="generatedAt")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class BriefDeliveryCreate(BaseModel):
    target_type: str = Field(alias="targetType")
    target_label: str = Field(default="", alias="targetLabel")

    model_config = ConfigDict(populate_by_name=True)


class BriefDeliveryRead(BaseModel):
    id: str
    export_id: str = Field(alias="exportId")
    target_type: str = Field(alias="targetType")
    target_label: str = Field(alias="targetLabel")
    status: str
    payload_json: dict[str, Any] = Field(alias="payloadJson")
    error_message: str | None = Field(alias="errorMessage")
    created_at: datetime = Field(alias="createdAt")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


@router.get("/templates", response_model=list[BriefTemplateRead])
def list_templates(db: Session = Depends(get_db)) -> list[BriefTemplate]:
    return ensure_default_templates(db)


@router.patch("/templates/{template_id}", response_model=BriefTemplateRead)
def update_template(
    template_id: str,
    payload: BriefTemplateUpdate,
    db: Session = Depends(get_db),
) -> BriefTemplate:
    ensure_default_templates(db)
    template = db.get(BriefTemplate, template_id)
    if template is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="BriefTemplate not found")
    updates = payload.model_dump(exclude_unset=True)
    if "name" in updates and updates["name"] is not None:
        template.name = updates["name"].strip() or template.name
    if "sections_json" in updates and updates["sections_json"] is not None:
        template.sections_json = [section.strip() for section in updates["sections_json"] if section.strip()]
    if "style_rules" in updates:
        template.style_rules = updates["style_rules"]
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


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


@router.get("/exports/{export_id}/download/html")
def download_export_html(export_id: str, db: Session = Depends(get_db)) -> Response:
    export = db.get(BriefExport, export_id)
    if export is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="BriefExport not found")
    filename = f"{_safe_filename(export.title)}.html"
    return Response(
        content=render_markdown_html(export.title, export.markdown),
        media_type="text/html; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/exports/{export_id}/download/docx")
def download_export_docx(export_id: str, db: Session = Depends(get_db)) -> Response:
    export = db.get(BriefExport, export_id)
    if export is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="BriefExport not found")
    filename = f"{_safe_filename(export.title)}.docx"
    return Response(
        content=render_markdown_docx(export.markdown),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/exports/{export_id}/deliveries", response_model=list[BriefDeliveryRead])
def list_deliveries(export_id: str, db: Session = Depends(get_db)) -> list[BriefDelivery]:
    export = db.get(BriefExport, export_id)
    if export is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="BriefExport not found")
    return list(
        db.scalars(
            select(BriefDelivery)
            .where(BriefDelivery.export_id == export_id)
            .order_by(BriefDelivery.created_at.desc())
        ).all()
    )


@router.post("/exports/{export_id}/deliveries", response_model=BriefDeliveryRead, status_code=status.HTTP_201_CREATED)
def create_export_delivery(
    export_id: str,
    payload: BriefDeliveryCreate,
    db: Session = Depends(get_db),
) -> BriefDelivery:
    export = db.get(BriefExport, export_id)
    if export is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="BriefExport not found")
    delivery = create_delivery(export, target_type=payload.target_type, target_label=payload.target_label)
    export.delivery_targets_json = [
        *(export.delivery_targets_json or []),
        {"targetType": delivery.target_type, "targetLabel": delivery.target_label, "status": delivery.status},
    ]
    db.add(export)
    db.add(delivery)
    db.commit()
    db.refresh(delivery)
    return delivery


def _safe_filename(value: str) -> str:
    safe = "".join(
        char if char.isascii() and (char.isalnum() or char in {"-", "_"}) else "-"
        for char in value.strip()
    )
    return safe.strip("-") or "brief"
