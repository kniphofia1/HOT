from __future__ import annotations

from difflib import SequenceMatcher
from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.connectors.core import BaseConnector, ConnectorMetadata
from app.connectors.types import ConnectorFetchResult, ConnectorError, RawItemPayload, WebpageSnapshotPayload
from app.connectors.utils import stable_hash
from app.db.models import Source, WebMonitorTarget


class WebpageConnector(BaseConnector):
    metadata = ConnectorMetadata(
        type="webpage",
        name="Public webpage watch",
        capabilities=["content_fetch"],
        real_fetch_enabled=True,
    )

    def fetch(self, db: Session, source: Source) -> ConnectorFetchResult:
        if not source.url:
            raise ConnectorError("Webpage source requires url")

        target = _get_or_create_target(db, source)
        response = httpx.get(target.url, timeout=20.0, follow_redirects=True)
        response.raise_for_status()

        text_content = _extract_text(response.text, target.css_selector)
        if not text_content:
            raise ConnectorError("No text content extracted from webpage")

        content_hash = stable_hash(target.url, text_content)
        if target.last_content_hash == content_hash:
            return ConnectorFetchResult()

        diff_summary = _diff_summary(target.last_content_hash, content_hash)
        target.last_content_hash = content_hash
        target.last_changed_at = datetime.now(timezone.utc)

        item = RawItemPayload(
            external_id=content_hash,
            source_url=target.url,
            title=source.name,
            content_text=text_content,
            raw_payload_json={
                "url": target.url,
                "cssSelector": target.css_selector,
                "extractionMode": target.extraction_mode,
            },
            content_hash=content_hash,
        )
        snapshot = WebpageSnapshotPayload(
            target_id=target.id,
            text_content=text_content,
            content_hash=content_hash,
            diff_summary=diff_summary,
        )
        return ConnectorFetchResult(items=[item], snapshots=[snapshot])


def _get_or_create_target(db: Session, source: Source) -> WebMonitorTarget:
    target = db.scalar(select(WebMonitorTarget).where(WebMonitorTarget.source_id == source.id))
    if target is not None:
        return target

    target = WebMonitorTarget(
        source_id=source.id,
        url=source.url or "",
        css_selector=source.config_json.get("cssSelector"),
        extraction_mode=source.config_json.get("extractionMode", "css_selector"),
    )
    db.add(target)
    db.flush()
    return target


def _extract_text(html: str, css_selector: str | None) -> str:
    soup = BeautifulSoup(html, "html.parser")
    if css_selector:
        elements = soup.select(css_selector)
        if not elements:
            raise ConnectorError(f"CSS selector did not match: {css_selector}")
        text = "\n".join(element.get_text(" ", strip=True) for element in elements)
    else:
        text = soup.get_text(" ", strip=True)
    return " ".join(text.split())


def _diff_summary(previous_hash: str | None, current_hash: str) -> str:
    if previous_hash is None:
        return "Initial snapshot"
    ratio = SequenceMatcher(None, previous_hash, current_hash).ratio()
    return f"Content hash changed; hash similarity {ratio:.2f}"
