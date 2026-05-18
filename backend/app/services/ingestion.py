from sqlalchemy import select
from sqlalchemy.orm import Session

from app.connectors.types import RawItemPayload
from app.connectors.utils import stable_hash
from app.db.models import MetricSnapshot, RawItem, Source
from app.services.candidates import ensure_event_candidate


def ingest_raw_item(db: Session, source: Source, payload: RawItemPayload) -> tuple[RawItem, bool]:
    content_hash = payload.content_hash or stable_hash(
        source.id,
        payload.external_id,
        payload.source_url,
        payload.title,
        payload.content_text,
    )
    existing = _find_existing_raw_item(db, source, payload, content_hash)
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
    else:
        existing.external_id = existing.external_id or payload.external_id
        existing.source_url = payload.source_url or existing.source_url
        existing.title = payload.title
        existing.content_text = payload.content_text
        existing.author = payload.author
        existing.published_at = payload.published_at
        existing.raw_payload_json = payload.raw_payload_json
        existing.content_hash = content_hash
        db.add(existing)
        db.flush()

    ensure_event_candidate(db, existing, source)

    for metric in payload.metrics:
        db.add(
            MetricSnapshot(
                raw_item_id=existing.id,
                metric_type=metric.metric_type,
                value=metric.value,
            )
        )

    return existing, created


def _find_existing_raw_item(
    db: Session,
    source: Source,
    payload: RawItemPayload,
    content_hash: str,
) -> RawItem | None:
    existing = db.scalar(
        select(RawItem).where(
            RawItem.source_id == source.id,
            RawItem.content_hash == content_hash,
        )
    )
    if existing is not None:
        return existing
    if payload.external_id:
        existing = db.scalar(
            select(RawItem).where(
                RawItem.source_id == source.id,
                RawItem.external_id == payload.external_id,
            )
        )
        if existing is not None:
            return existing
    if payload.source_url and source.type != "webpage":
        return db.scalar(
            select(RawItem).where(
                RawItem.source_id == source.id,
                RawItem.source_url == payload.source_url,
            )
        )
    return None
