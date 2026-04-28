from __future__ import annotations

import feedparser
import httpx
from sqlalchemy.orm import Session

from app.connectors.core import BaseConnector, ConnectorMetadata
from app.connectors.types import ConnectorFetchResult, ConnectorError, RawItemPayload
from app.connectors.utils import parse_datetime, stable_hash
from app.db.models import Source


class RssConnector(BaseConnector):
    metadata = ConnectorMetadata(
        type="rss",
        name="RSS",
        capabilities=["content_fetch"],
        real_fetch_enabled=True,
    )

    def fetch(self, db: Session, source: Source) -> ConnectorFetchResult:
        if not source.url:
            raise ConnectorError("RSS source requires url")

        response = httpx.get(source.url, timeout=20.0, follow_redirects=True)
        response.raise_for_status()
        parsed = feedparser.parse(response.content)
        if parsed.bozo and not parsed.entries:
            raise ConnectorError(f"RSS parse failed: {parsed.bozo_exception}")

        items: list[RawItemPayload] = []
        for entry in parsed.entries:
            link = entry.get("link") or source.url
            title = entry.get("title") or link
            content_text = _entry_text(entry)
            external_id = entry.get("id") or entry.get("guid") or link
            published_at = parse_datetime(entry.get("published") or entry.get("updated"))
            author = entry.get("author")
            items.append(
                RawItemPayload(
                    external_id=str(external_id),
                    source_url=str(link),
                    title=str(title),
                    content_text=content_text,
                    author=str(author) if author else None,
                    published_at=published_at,
                    raw_payload_json=_safe_entry_dict(entry),
                    content_hash=stable_hash(source.id, external_id, title, link, content_text),
                )
            )

        return ConnectorFetchResult(items=items)


def _entry_text(entry) -> str | None:
    summary = entry.get("summary")
    if summary:
        return str(summary)
    content = entry.get("content")
    if content and isinstance(content, list):
        value = content[0].get("value")
        return str(value) if value else None
    return None


def _safe_entry_dict(entry) -> dict:
    return {
        "id": entry.get("id"),
        "title": entry.get("title"),
        "link": entry.get("link"),
        "published": entry.get("published"),
        "updated": entry.get("updated"),
        "author": entry.get("author"),
        "summary": entry.get("summary"),
    }
