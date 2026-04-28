from sqlalchemy import select
from sqlalchemy.orm import Session

from app.connectors.types import RawItemPayload
from app.connectors.utils import stable_hash
from app.db.models import MetricSnapshot, RawItem, Source


def ingest_raw_item(db: Session, source: Source, payload: RawItemPayload) -> tuple[RawItem, bool]:
    content_hash = payload.content_hash or stable_hash(
        source.id,
        payload.external_id,
        payload.source_url,
        payload.title,
        payload.content_text,
    )
    existing = db.scalar(
        select(RawItem).where(
            RawItem.source_id == source.id,
            RawItem.content_hash == content_hash,
        )
    )
    created = False
    if existing is None:
        existing = RawItem(
            source_id=source.id,
            external_id=payload.external_id,
            source_url=payload.source_url,
            title=payload.title,
            content_text=payload.content_text,
            author=payload.author,
            published_at=payload.published_at,
            raw_payload_json=payload.raw_payload_json,
            content_hash=content_hash,
        )
        db.add(existing)
        db.flush()
        created = True

    for metric in payload.metrics:
        db.add(
            MetricSnapshot(
                raw_item_id=existing.id,
                metric_type=metric.metric_type,
                value=metric.value,
            )
        )

    return existing, created
