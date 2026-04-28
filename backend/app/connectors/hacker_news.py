from __future__ import annotations

import httpx
from sqlalchemy.orm import Session

from app.connectors.core import BaseConnector, ConnectorMetadata
from app.connectors.types import ConnectorFetchResult, ConnectorError, MetricPayload, RawItemPayload
from app.connectors.utils import stable_hash
from app.db.models import Source


HN_BASE_URL = "https://hacker-news.firebaseio.com/v0"


class HackerNewsConnector(BaseConnector):
    metadata = ConnectorMetadata(
        type="hacker_news",
        name="Hacker News",
        capabilities=["content_fetch", "metric_refresh"],
        real_fetch_enabled=True,
    )

    def fetch(self, db: Session, source: Source) -> ConnectorFetchResult:
        list_type = str(source.config_json.get("listType", "top"))
        limit = int(source.config_json.get("limit", 30))
        if list_type not in {"top", "new", "best"}:
            raise ConnectorError("HN listType must be top, new, or best")

        story_ids = httpx.get(f"{HN_BASE_URL}/{list_type}stories.json", timeout=20.0).json()
        items: list[RawItemPayload] = []
        for story_id in story_ids[:limit]:
            story = httpx.get(f"{HN_BASE_URL}/item/{story_id}.json", timeout=20.0).json()
            if not story or story.get("type") not in {"story", "job"}:
                continue
            title = story.get("title") or f"Hacker News item {story_id}"
            url = story.get("url") or f"https://news.ycombinator.com/item?id={story_id}"
            score = int(story.get("score") or 0)
            comments = int(story.get("descendants") or 0)
            items.append(
                RawItemPayload(
                    external_id=str(story_id),
                    source_url=url,
                    title=title,
                    content_text=story.get("text"),
                    author=story.get("by"),
                    raw_payload_json=story,
                    content_hash=stable_hash("hn", story_id, title, url),
                    metrics=[
                        MetricPayload(metric_type="hn_score", value=score),
                        MetricPayload(metric_type="hn_comments", value=comments),
                    ],
                )
            )

        return ConnectorFetchResult(items=items)
