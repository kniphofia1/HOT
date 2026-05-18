from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.connectors.types import RawItemPayload
from app.connectors.utils import stable_hash
from app.db.models import MetricSnapshot, RawItem
from app.db.models import Source
from app.db.session import get_db
from app.services.ingestion import ingest_raw_item


router = APIRouter(prefix="/api/items", tags=["items"])


class RawItemRead(BaseModel):
    id: str
    source_id: str = Field(alias="sourceId")
    title: str
    source_url: str | None = Field(alias="sourceUrl")
    content_text: str | None = Field(alias="contentText")
    author: str | None
    published_at: datetime | None = Field(alias="publishedAt")
    fetched_at: datetime = Field(alias="fetchedAt")
    content_hash: str = Field(alias="contentHash")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ManualRawItemCreate(BaseModel):
    title: str
    source_url: str | None = Field(default=None, alias="sourceUrl")
    content_text: str | None = Field(default=None, alias="contentText")
    author: str | None = None
    platform: str | None = None
    source_name: str = Field(default="Manual Link", alias="sourceName")
    published_at: datetime | None = Field(default=None, alias="publishedAt")

    model_config = ConfigDict(populate_by_name=True)


class MetricSnapshotRead(BaseModel):
    id: str
    raw_item_id: str = Field(alias="rawItemId")
    metric_type: str = Field(alias="metricType")
    value: int

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


@router.get("", response_model=list[RawItemRead])
def list_raw_items(db: Session = Depends(get_db)) -> list[RawItem]:
    return list(db.scalars(select(RawItem).order_by(func.coalesce(RawItem.published_at, RawItem.fetched_at).desc())).all())


@router.post("/manual", response_model=RawItemRead, status_code=201)
def create_manual_raw_item(payload: ManualRawItemCreate, db: Session = Depends(get_db)) -> RawItem:
    source = _manual_source(db, payload.source_name)
    external_id = payload.source_url or stable_hash("manual", payload.title, payload.content_text)
    raw_item, _ = ingest_raw_item(
        db,
        source,
        RawItemPayload(
            external_id=external_id,
            source_url=payload.source_url,
            title=payload.title.strip(),
            content_text=payload.content_text.strip() if payload.content_text else None,
            author=payload.author.strip() if payload.author else None,
            published_at=payload.published_at,
            raw_payload_json={
                "ingestionMode": "manual_link",
                "sourceName": payload.source_name,
                "platform": payload.platform.strip() if payload.platform else None,
            },
            content_hash=stable_hash("manual", source.id, external_id, payload.title, payload.content_text),
        ),
    )
    db.commit()
    db.refresh(raw_item)
    return raw_item


@router.get("/{raw_item_id}/metrics", response_model=list[MetricSnapshotRead])
def list_item_metrics(raw_item_id: str, db: Session = Depends(get_db)) -> list[MetricSnapshot]:
    return list(
        db.scalars(
            select(MetricSnapshot)
            .where(MetricSnapshot.raw_item_id == raw_item_id)
            .order_by(MetricSnapshot.captured_at.desc())
        ).all()
    )


def _manual_source(db: Session, source_name: str) -> Source:
    name = source_name.strip() or "Manual Link"
    source = db.scalar(select(Source).where(Source.type == "manual_link", Source.name == name))
    if source is not None:
        return source
    source = Source(
        type="manual_link",
        name=name,
        url=None,
        enabled=False,
        weight=1,
        poll_interval_minutes=0,
        config_json={"ingestionMode": "manual_link"},
    )
    db.add(source)
    db.flush()
    return source
