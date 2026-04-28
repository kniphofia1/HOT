from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import MetricSnapshot, RawItem
from app.db.session import get_db


router = APIRouter(prefix="/api/items", tags=["items"])


class RawItemRead(BaseModel):
    id: str
    source_id: str = Field(alias="sourceId")
    title: str
    source_url: str | None = Field(alias="sourceUrl")
    content_text: str | None = Field(alias="contentText")
    content_hash: str = Field(alias="contentHash")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class MetricSnapshotRead(BaseModel):
    id: str
    raw_item_id: str = Field(alias="rawItemId")
    metric_type: str = Field(alias="metricType")
    value: int

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


@router.get("", response_model=list[RawItemRead])
def list_raw_items(db: Session = Depends(get_db)) -> list[RawItem]:
    return list(db.scalars(select(RawItem).order_by(RawItem.fetched_at.desc())).all())


@router.get("/{raw_item_id}/metrics", response_model=list[MetricSnapshotRead])
def list_item_metrics(raw_item_id: str, db: Session = Depends(get_db)) -> list[MetricSnapshot]:
    return list(
        db.scalars(
            select(MetricSnapshot)
            .where(MetricSnapshot.raw_item_id == raw_item_id)
            .order_by(MetricSnapshot.captured_at.desc())
        ).all()
    )
