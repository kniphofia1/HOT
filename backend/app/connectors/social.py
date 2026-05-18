from __future__ import annotations

import os
from html import unescape
from urllib.parse import quote, urlparse

import httpx
from sqlalchemy.orm import Session

from app.connectors.core import BaseConnector, ConnectorMetadata
from app.connectors.types import ConnectorError, ConnectorFetchResult, MetricPayload, RawItemPayload
from app.connectors.utils import parse_datetime, stable_hash
from app.db.models import Source


REDDIT_BASE_URL = "https://www.reddit.com"
REDDIT_OAUTH_BASE_URL = "https://oauth.reddit.com"
REDDIT_TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
BLUESKY_PUBLIC_API_BASE = "https://api.bsky.app"


class RedditSubredditConnector(BaseConnector):
    metadata = ConnectorMetadata(
        type="reddit_subreddit",
        name="Reddit subreddit",
        capabilities=["content_fetch", "metric_refresh"],
        real_fetch_enabled=True,
    )

    def fetch(self, db: Session, source: Source) -> ConnectorFetchResult:
        subreddit = str(source.config_json.get("subreddit") or "").strip().strip("r/")
        if not subreddit:
            raise ConnectorError("Reddit source requires subreddit")

        sort = str(source.config_json.get("sort", "hot")).strip().lower()
        if sort not in {"hot", "new", "top", "rising", "search"}:
            raise ConnectorError("Reddit sort must be hot, new, top, rising, or search")

        limit = _bounded_limit(source.config_json.get("limit"), default=25, maximum=100)
        time_range = str(source.config_json.get("timeRange", "day")).strip().lower()
        query = str(source.config_json.get("query") or "").strip()

        path = f"/r/{quote(subreddit)}/{sort}.json"
        params: dict[str, object] = {"limit": limit, "raw_json": 1}
        if sort == "top":
            params["t"] = time_range
        if sort == "search":
            if not query:
                raise ConnectorError("Reddit search source requires query")
            params.update({"q": query, "restrict_sr": 1, "sort": "relevance", "t": time_range})

        payload = _reddit_get(path, params=params)
        children = payload.get("data", {}).get("children", [])
        items: list[RawItemPayload] = []
        for child in children[:limit]:
            post = child.get("data", {})
            post_id = str(post.get("name") or post.get("id") or "")
            title = str(post.get("title") or post_id or "Reddit post")
            permalink = post.get("permalink")
            source_url = f"{REDDIT_BASE_URL}{permalink}" if permalink else post.get("url")
            content_text = _join_nonempty(
                post.get("selftext"),
                f"Subreddit: r/{post.get('subreddit') or subreddit}",
                f"Score: {int(post.get('score') or 0)}",
                f"Comments: {int(post.get('num_comments') or 0)}",
                f"Outbound URL: {post.get('url') or ''}",
            )
            items.append(
                RawItemPayload(
                    external_id=post_id or None,
                    source_url=source_url,
                    title=f"Reddit: {title}",
                    content_text=content_text,
                    author=post.get("author"),
                    published_at=_unix_timestamp(post.get("created_utc")),
                    raw_payload_json={
                        "provider": "reddit",
                        "subreddit": subreddit,
                        "sort": sort,
                        "timeRange": time_range,
                        "query": query,
                        "post": post,
                    },
                    content_hash=stable_hash("reddit", post_id, title, source_url),
                    metrics=[
                        MetricPayload("reddit_score", int(post.get("score") or 0)),
                        MetricPayload("reddit_comments", int(post.get("num_comments") or 0)),
                    ],
                )
            )
        return ConnectorFetchResult(items=items)


class BlueskySearchConnector(BaseConnector):
    metadata = ConnectorMetadata(
        type="bluesky_search",
        name="Bluesky public search",
        capabilities=["content_fetch", "metric_refresh"],
        real_fetch_enabled=True,
    )

    def fetch(self, db: Session, source: Source) -> ConnectorFetchResult:
        query = str(source.config_json.get("query") or "").strip()
        if not query:
            raise ConnectorError("Bluesky search source requires query")

        limit = _bounded_limit(source.config_json.get("limit"), default=25, maximum=100)
        params = {"q": query, "limit": limit}
        author = str(source.config_json.get("actor") or "").strip().lstrip("@")
        if author:
            params["author"] = author

        response = httpx.get(
            f"{BLUESKY_PUBLIC_API_BASE}/xrpc/app.bsky.feed.searchPosts",
            params=params,
            timeout=20.0,
        )
        response.raise_for_status()
        payload = response.json()

        items: list[RawItemPayload] = []
        for post in payload.get("posts", [])[:limit]:
            record = post.get("record", {})
            text = str(record.get("text") or "").strip()
            author_payload = post.get("author", {})
            handle = str(author_payload.get("handle") or "")
            uri = str(post.get("uri") or "")
            source_url = _bluesky_post_url(uri, handle)
            items.append(
                RawItemPayload(
                    external_id=uri or post.get("cid"),
                    source_url=source_url,
                    title=f"Bluesky: {_title_from_text(text, fallback=uri or 'post')}",
                    content_text=_join_nonempty(
                        text,
                        f"Author: @{handle}" if handle else "",
                        f"Replies: {int(post.get('replyCount') or 0)}",
                        f"Reposts: {int(post.get('repostCount') or 0)}",
                        f"Likes: {int(post.get('likeCount') or 0)}",
                    ),
                    author=handle or None,
                    published_at=parse_datetime(record.get("createdAt")),
                    raw_payload_json={"provider": "bluesky", "query": query, "actor": author, "post": post},
                    content_hash=stable_hash("bluesky", uri, post.get("cid"), text),
                    metrics=[
                        MetricPayload("bluesky_replies", int(post.get("replyCount") or 0)),
                        MetricPayload("bluesky_reposts", int(post.get("repostCount") or 0)),
                        MetricPayload("bluesky_likes", int(post.get("likeCount") or 0)),
                    ],
                )
            )
        return ConnectorFetchResult(items=items)


class BlueskyActorFeedConnector(BaseConnector):
    metadata = ConnectorMetadata(
        type="bluesky_actor_feed",
        name="Bluesky actor feed",
        capabilities=["content_fetch", "metric_refresh"],
        real_fetch_enabled=True,
    )

    def fetch(self, db: Session, source: Source) -> ConnectorFetchResult:
        actor = str(source.config_json.get("actor") or "").strip().lstrip("@")
        if not actor:
            raise ConnectorError("Bluesky actor feed source requires actor")

        limit = _bounded_limit(source.config_json.get("limit"), default=25, maximum=100)
        response = httpx.get(
            f"{BLUESKY_PUBLIC_API_BASE}/xrpc/app.bsky.feed.getAuthorFeed",
            params={"actor": actor, "limit": limit},
            timeout=20.0,
        )
        response.raise_for_status()
        payload = response.json()

        items: list[RawItemPayload] = []
        for entry in payload.get("feed", [])[:limit]:
            post = entry.get("post", {})
            record = post.get("record", {})
            text = str(record.get("text") or "").strip()
            author_payload = post.get("author", {})
            handle = str(author_payload.get("handle") or actor)
            uri = str(post.get("uri") or "")
            source_url = _bluesky_post_url(uri, handle)
            items.append(
                RawItemPayload(
                    external_id=uri or post.get("cid"),
                    source_url=source_url,
                    title=f"Bluesky: {_title_from_text(text, fallback=uri or 'post')}",
                    content_text=_join_nonempty(
                        text,
                        f"Author: @{handle}" if handle else "",
                        f"Replies: {int(post.get('replyCount') or 0)}",
                        f"Reposts: {int(post.get('repostCount') or 0)}",
                        f"Likes: {int(post.get('likeCount') or 0)}",
                    ),
                    author=handle or None,
                    published_at=parse_datetime(record.get("createdAt")),
                    raw_payload_json={"provider": "bluesky", "actor": actor, "entry": entry},
                    content_hash=stable_hash("bluesky_actor_feed", actor, uri, post.get("cid"), text),
                    metrics=[
                        MetricPayload("bluesky_replies", int(post.get("replyCount") or 0)),
                        MetricPayload("bluesky_reposts", int(post.get("repostCount") or 0)),
                        MetricPayload("bluesky_likes", int(post.get("likeCount") or 0)),
                    ],
                )
            )
        return ConnectorFetchResult(items=items)


class MastodonTimelineConnector(BaseConnector):
    metadata = ConnectorMetadata(
        type="mastodon_timeline",
        name="Mastodon public timeline",
        capabilities=["content_fetch", "metric_refresh"],
        real_fetch_enabled=True,
    )

    def fetch(self, db: Session, source: Source) -> ConnectorFetchResult:
        instance_url = str(source.config_json.get("instanceUrl") or source.url or "").strip().rstrip("/")
        if not instance_url:
            raise ConnectorError("Mastodon source requires instanceUrl")

        mode = str(source.config_json.get("mode", "public")).strip().lower()
        if mode not in {"public", "tag"}:
            raise ConnectorError("Mastodon mode must be public or tag")

        limit = _bounded_limit(source.config_json.get("limit"), default=25, maximum=40)
        if mode == "tag":
            tag = str(source.config_json.get("tag") or "").strip().lstrip("#")
            if not tag:
                raise ConnectorError("Mastodon tag timeline requires tag")
            url = f"{instance_url}/api/v1/timelines/tag/{quote(tag)}"
        else:
            tag = ""
            url = f"{instance_url}/api/v1/timelines/public"

        response = httpx.get(url, params={"limit": limit}, timeout=20.0)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list):
            raise ConnectorError("Mastodon timeline response must be a list")

        items: list[RawItemPayload] = []
        for status in payload[:limit]:
            account = status.get("account", {})
            content = _clean_html(status.get("content"))
            source_url = status.get("url") or status.get("uri")
            account_name = account.get("acct") or account.get("username")
            status_id = str(status.get("id") or source_url or "")
            items.append(
                RawItemPayload(
                    external_id=status_id or None,
                    source_url=source_url,
                    title=f"Mastodon: {_title_from_text(content, fallback=status_id or 'status')}",
                    content_text=_join_nonempty(
                        content,
                        f"Instance: {_netloc(instance_url)}",
                        f"Account: @{account_name}" if account_name else "",
                        f"Replies: {int(status.get('replies_count') or 0)}",
                        f"Reblogs: {int(status.get('reblogs_count') or 0)}",
                        f"Favourites: {int(status.get('favourites_count') or 0)}",
                    ),
                    author=account_name,
                    published_at=parse_datetime(status.get("created_at")),
                    raw_payload_json={
                        "provider": "mastodon",
                        "instanceUrl": instance_url,
                        "mode": mode,
                        "tag": tag,
                        "status": status,
                    },
                    content_hash=stable_hash("mastodon", instance_url, status_id, content),
                    metrics=[
                        MetricPayload("mastodon_replies", int(status.get("replies_count") or 0)),
                        MetricPayload("mastodon_reblogs", int(status.get("reblogs_count") or 0)),
                        MetricPayload("mastodon_favourites", int(status.get("favourites_count") or 0)),
                    ],
                )
            )
        return ConnectorFetchResult(items=items)


def _reddit_get(path: str, *, params: dict[str, object]):
    token = _reddit_access_token()
    headers = {"User-Agent": os.getenv("REDDIT_USER_AGENT", "hot-radar/0.1")}
    if token:
        headers["Authorization"] = f"Bearer {token}"
        url = f"{REDDIT_OAUTH_BASE_URL}{path.removesuffix('.json')}"
    else:
        url = f"{REDDIT_BASE_URL}{path}"
    response = httpx.get(url, params=params, headers=headers, timeout=20.0)
    response.raise_for_status()
    return response.json()


def _reddit_access_token() -> str | None:
    client_id = os.getenv("REDDIT_CLIENT_ID", "").strip()
    client_secret = os.getenv("REDDIT_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        return None
    headers = {"User-Agent": os.getenv("REDDIT_USER_AGENT", "hot-radar/0.1")}
    response = httpx.post(
        REDDIT_TOKEN_URL,
        auth=(client_id, client_secret),
        data={"grant_type": "client_credentials"},
        headers=headers,
        timeout=20.0,
    )
    response.raise_for_status()
    return response.json().get("access_token")


def _bounded_limit(value: object, *, default: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(1, min(maximum, parsed))


def _unix_timestamp(value: object):
    try:
        timestamp = float(value)
    except (TypeError, ValueError):
        return None
    from datetime import datetime, timezone

    return datetime.fromtimestamp(timestamp, tz=timezone.utc)


def _join_nonempty(*values: object) -> str:
    return "\n".join(str(value).strip() for value in values if value is not None and str(value).strip())


def _title_from_text(value: str, *, fallback: str) -> str:
    text = " ".join(value.split())
    return (text[:96] + "...") if len(text) > 96 else (text or fallback)


def _bluesky_post_url(uri: str, handle: str) -> str | None:
    if not uri or not handle:
        return None
    rkey = uri.rsplit("/", 1)[-1]
    return f"https://bsky.app/profile/{handle}/post/{rkey}"


def _clean_html(value: object) -> str:
    if value is None:
        return ""
    text = str(value)
    for token in ("<p>", "</p>", "<br>", "<br/>", "<br />"):
        text = text.replace(token, " ")
    while "<" in text and ">" in text:
        start = text.find("<")
        end = text.find(">", start)
        if end == -1:
            break
        text = text[:start] + " " + text[end + 1 :]
    return " ".join(unescape(text).split())


def _netloc(value: str) -> str:
    parsed = urlparse(value)
    return parsed.netloc or value
