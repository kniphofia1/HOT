from __future__ import annotations

from datetime import datetime, timedelta, timezone
from os import getenv
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.connectors.core import BaseConnector, ConnectorMetadata
from app.connectors.types import ConnectorError, ConnectorFetchResult, MetricPayload, RawItemPayload
from app.connectors.utils import parse_datetime, stable_hash
from app.db.models import Source


class XRecentSearchConnector(BaseConnector):
    metadata = ConnectorMetadata(
        type="x_recent_search",
        name="X Recent Search",
        capabilities=["content_fetch", "metrics"],
        real_fetch_enabled=True,
    )

    def fetch(self, db: Session, source: Source) -> ConnectorFetchResult:
        token = _env_secret(source, "bearerTokenEnv", "X_BEARER_TOKEN")
        query = _x_query(source)
        limit = _limit(source, default=25, max_value=100)
        page_limit = _int_config(source, "pageLimit", default=1, min_value=1, max_value=5)
        params: dict[str, Any] = {
            "query": query,
            "max_results": max(10, min(100, limit)),
            "tweet.fields": "created_at,author_id,public_metrics,entities,lang,referenced_tweets,attachments,conversation_id",
            "expansions": "author_id,attachments.media_keys",
            "user.fields": "id,name,username,verified,verified_type,profile_image_url,public_metrics,url",
            "media.fields": "media_key,type,url,preview_image_url,width,height,public_metrics",
        }
        latest_tweet_id = str(source.config_json.get("latestTweetId") or "").strip()
        if latest_tweet_id:
            params["since_id"] = latest_tweet_id
        elif source.config_json.get("lookbackHours"):
            hours = _int_config(source, "lookbackHours", default=24, min_value=1, max_value=168)
            params["start_time"] = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat().replace("+00:00", "Z")

        items = []
        newest_id: str | None = None
        next_token: str | None = None
        for _ in range(page_limit):
            request_params = dict(params)
            if next_token:
                request_params["next_token"] = next_token
            response = httpx.get(
                "https://api.x.com/2/tweets/search/recent",
                headers={"Authorization": f"Bearer {token}"},
                params=request_params,
                timeout=20.0,
            )
            _raise_for_status(response, "X")
            payload = response.json()
            items.extend(_x_items_from_payload(source, payload, remaining=limit - len(items)))
            newest_id = _max_id(newest_id, *((post.get("id") for post in payload.get("data", []))))
            next_token = (payload.get("meta") or {}).get("next_token")
            if len(items) >= limit or not next_token:
                break
        if newest_id:
            source.config_json = {**source.config_json, "latestTweetId": newest_id}
            db.add(source)
        return ConnectorFetchResult(items=items[:limit])


def _x_items_from_payload(source: Source, payload: dict[str, Any], *, remaining: int) -> list[RawItemPayload]:
    users_by_id = {
        str(user.get("id")): user
        for user in (payload.get("includes") or {}).get("users", [])
        if user.get("id") is not None
    }
    media_by_key = {
        str(media.get("media_key")): media
        for media in (payload.get("includes") or {}).get("media", [])
        if media.get("media_key") is not None
    }
    items: list[RawItemPayload] = []
    for post in payload.get("data", [])[:remaining]:
        author = users_by_id.get(str(post.get("author_id")))
        media = [
            media_by_key[key]
            for key in ((post.get("attachments") or {}).get("media_keys") or [])
            if key in media_by_key
        ]
        username = author.get("username") if isinstance(author, dict) else None
        display_author = username or (author.get("name") if isinstance(author, dict) else None) or post.get("author_id")
        post_url = f"https://x.com/{username}/status/{post.get('id')}" if username else f"https://x.com/i/web/status/{post.get('id')}"
        raw_payload = {**post, "author": author, "media": media}
        metrics = post.get("public_metrics") or {}
        metric_payloads = [
            MetricPayload("x_retweets", int(metrics.get("retweet_count", 0))),
            MetricPayload("x_replies", int(metrics.get("reply_count", 0))),
            MetricPayload("x_likes", int(metrics.get("like_count", 0))),
            MetricPayload("x_quotes", int(metrics.get("quote_count", 0))),
        ]
        if "impression_count" in metrics:
            metric_payloads.append(MetricPayload("x_impressions", int(metrics.get("impression_count", 0))))
        items.append(
            RawItemPayload(
                external_id=str(post.get("id")),
                source_url=post_url,
                title=_first_line(post.get("text") or "X Post"),
                content_text=post.get("text"),
                author=str(display_author) if display_author else None,
                published_at=parse_datetime(post.get("created_at")),
                raw_payload_json=raw_payload,
                content_hash=stable_hash(source.id, post.get("id"), post.get("text")),
                metrics=metric_payloads,
            )
        )
    return items


def _x_query(source: Source) -> str:
    query = str(source.config_json.get("query") or "").strip()
    if not query:
        handles = source.config_json.get("handles")
        if isinstance(handles, list) and handles:
            query = "(" + " OR ".join(f"from:{str(handle).lstrip('@')}" for handle in handles) + ")"
    if not query:
        raise ConnectorError("x_recent_search source requires query or handles")
    if source.config_json.get("excludeRetweets", True) and "-is:retweet" not in query:
        query = f"{query} -is:retweet"
    if source.config_json.get("excludeReplies", True) and "-is:reply" not in query:
        query = f"{query} -is:reply"
    return query


def _max_id(current: str | None, *values: object) -> str | None:
    ids = [value for value in [current, *values] if value is not None and str(value).isdigit()]
    if not ids:
        return current
    return str(max(int(value) for value in ids))


class YouTubeChannelConnector(BaseConnector):
    metadata = ConnectorMetadata(
        type="youtube_channel",
        name="YouTube Data API Channel Search",
        capabilities=["content_fetch"],
        real_fetch_enabled=True,
    )

    def fetch(self, db: Session, source: Source) -> ConnectorFetchResult:
        api_key = _env_secret(source, "apiKeyEnv", "YOUTUBE_API_KEY")
        limit = _limit(source, default=10, max_value=50)
        params: dict[str, Any] = {
            "part": "snippet",
            "type": "video",
            "order": "date",
            "maxResults": limit,
            "key": api_key,
        }
        if source.config_json.get("channelId"):
            params["channelId"] = source.config_json["channelId"]
        if source.config_json.get("query"):
            params["q"] = source.config_json["query"]
        if "channelId" not in params and "q" not in params:
            raise ConnectorError("YouTube source requires channelId or query")
        response = httpx.get("https://www.googleapis.com/youtube/v3/search", params=params, timeout=20.0)
        _raise_for_status(response, "YouTube")
        items = []
        for rank, video in enumerate(response.json().get("items", []), start=1):
            video_id = (video.get("id") or {}).get("videoId")
            snippet = video.get("snippet") or {}
            if not video_id:
                continue
            items.append(
                RawItemPayload(
                    external_id=video_id,
                    source_url=f"https://www.youtube.com/watch?v={video_id}",
                    title=snippet.get("title") or "YouTube video",
                    content_text=snippet.get("description"),
                    author=snippet.get("channelTitle"),
                    published_at=parse_datetime(snippet.get("publishedAt")),
                    raw_payload_json=video,
                    content_hash=stable_hash(source.id, video_id, snippet.get("title")),
                    metrics=[MetricPayload("youtube_search_rank", rank)],
                )
            )
        return ConnectorFetchResult(items=items)


class TelegramUpdatesConnector(BaseConnector):
    metadata = ConnectorMetadata(
        type="telegram_updates",
        name="Telegram Bot Updates",
        capabilities=["content_fetch"],
        real_fetch_enabled=True,
    )

    def fetch(self, db: Session, source: Source) -> ConnectorFetchResult:
        token = _env_secret(source, "botTokenEnv", "TELEGRAM_BOT_TOKEN")
        params = {
            "limit": _limit(source, default=50, max_value=100),
            "allowed_updates": '["message","channel_post","edited_channel_post"]',
        }
        if source.config_json.get("offset"):
            params["offset"] = int(source.config_json["offset"])
        response = httpx.get(f"https://api.telegram.org/bot{token}/getUpdates", params=params, timeout=20.0)
        _raise_for_status(response, "Telegram")
        payload = response.json()
        if not payload.get("ok", False):
            raise ConnectorError(payload.get("description") or "Telegram getUpdates failed")
        expected_chat_id = str(source.config_json.get("chatId") or "")
        items = []
        next_offset = None
        for update in payload.get("result", []):
            update_id = update.get("update_id")
            if update_id is not None:
                next_offset = max(next_offset or 0, int(update_id) + 1)
            message = update.get("channel_post") or update.get("edited_channel_post") or update.get("message")
            if not message:
                continue
            chat = message.get("chat") or {}
            if expected_chat_id and str(chat.get("id")) != expected_chat_id:
                continue
            text = message.get("text") or message.get("caption") or ""
            title = _first_line(text) or chat.get("title") or "Telegram message"
            items.append(
                RawItemPayload(
                    external_id=str(message.get("message_id") or update_id),
                    source_url=_telegram_message_url(chat, message),
                    title=title,
                    content_text=text,
                    author=chat.get("title") or chat.get("username"),
                    published_at=_unix_datetime(message.get("date")),
                    raw_payload_json=update,
                    content_hash=stable_hash(source.id, chat.get("id"), message.get("message_id"), text),
                    metrics=[MetricPayload("telegram_views", int(message.get("views", 0) or 0))],
                )
            )
        if next_offset is not None:
            source.config_json = {**source.config_json, "offset": next_offset}
            db.add(source)
        return ConnectorFetchResult(items=items)


class DiscordChannelConnector(BaseConnector):
    metadata = ConnectorMetadata(
        type="discord_channel",
        name="Discord Channel Messages",
        capabilities=["content_fetch"],
        real_fetch_enabled=True,
    )

    def fetch(self, db: Session, source: Source) -> ConnectorFetchResult:
        token = _env_secret(source, "botTokenEnv", "DISCORD_BOT_TOKEN")
        channel_id = _required_config(source, "channelId")
        response = httpx.get(
            f"https://discord.com/api/v10/channels/{channel_id}/messages",
            headers={"Authorization": f"Bot {token}"},
            params={"limit": _limit(source, default=50, max_value=100)},
            timeout=20.0,
        )
        _raise_for_status(response, "Discord")
        items = []
        for message in response.json():
            author = message.get("author") or {}
            content = message.get("content") or ""
            guild_id = source.config_json.get("guildId") or "@me"
            items.append(
                RawItemPayload(
                    external_id=str(message.get("id")),
                    source_url=f"https://discord.com/channels/{guild_id}/{channel_id}/{message.get('id')}",
                    title=_first_line(content) or "Discord message",
                    content_text=content,
                    author=author.get("username"),
                    published_at=parse_datetime(message.get("timestamp")),
                    raw_payload_json=message,
                    content_hash=stable_hash(source.id, message.get("id"), content),
                    metrics=[
                        MetricPayload("discord_reactions", _reaction_count(message.get("reactions"))),
                        MetricPayload("discord_attachments", len(message.get("attachments") or [])),
                    ],
                )
            )
        return ConnectorFetchResult(items=items)


class SlackChannelConnector(BaseConnector):
    metadata = ConnectorMetadata(
        type="slack_channel",
        name="Slack Conversation History",
        capabilities=["content_fetch"],
        real_fetch_enabled=True,
    )

    def fetch(self, db: Session, source: Source) -> ConnectorFetchResult:
        token = _env_secret(source, "botTokenEnv", "SLACK_BOT_TOKEN")
        channel_id = _required_config(source, "channelId")
        response = httpx.post(
            "https://slack.com/api/conversations.history",
            headers={"Authorization": f"Bearer {token}"},
            data={"channel": channel_id, "limit": _limit(source, default=50, max_value=100)},
            timeout=20.0,
        )
        _raise_for_status(response, "Slack")
        payload = response.json()
        if not payload.get("ok", False):
            raise ConnectorError(payload.get("error") or "Slack conversations.history failed")
        items = []
        for message in payload.get("messages", []):
            text = message.get("text") or ""
            ts = str(message.get("ts"))
            items.append(
                RawItemPayload(
                    external_id=ts,
                    source_url=f"https://slack.com/app_redirect?channel={channel_id}&message_ts={ts}",
                    title=_first_line(text) or "Slack message",
                    content_text=text,
                    author=message.get("user") or message.get("username"),
                    published_at=_slack_ts_datetime(ts),
                    raw_payload_json=message,
                    content_hash=stable_hash(source.id, ts, text),
                    metrics=[MetricPayload("slack_reactions", _reaction_count(message.get("reactions")))],
                )
            )
        return ConnectorFetchResult(items=items)


class LinkedInPostsConnector(BaseConnector):
    metadata = ConnectorMetadata(
        type="linkedin_posts",
        name="LinkedIn Posts API",
        capabilities=["content_fetch"],
        real_fetch_enabled=True,
    )

    def fetch(self, db: Session, source: Source) -> ConnectorFetchResult:
        token = _env_secret(source, "accessTokenEnv", "LINKEDIN_ACCESS_TOKEN")
        author = _required_config(source, "authorUrn")
        version = str(source.config_json.get("version") or "202602")
        response = httpx.get(
            "https://api.linkedin.com/rest/posts",
            headers={
                "Authorization": f"Bearer {token}",
                "Linkedin-Version": version,
                "X-Restli-Protocol-Version": "2.0.0",
            },
            params={"q": "author", "author": author, "count": _limit(source, default=20, max_value=100)},
            timeout=20.0,
        )
        _raise_for_status(response, "LinkedIn")
        items = []
        for post in response.json().get("elements", []):
            urn = str(post.get("id") or post.get("entity") or stable_hash(post))
            commentary = post.get("commentary") or post.get("text") or {}
            text = commentary.get("text") if isinstance(commentary, dict) else str(commentary)
            items.append(
                RawItemPayload(
                    external_id=urn,
                    source_url=post.get("permalink") or f"https://www.linkedin.com/feed/update/{urn}",
                    title=_first_line(text) or "LinkedIn post",
                    content_text=text,
                    author=str(post.get("author") or author),
                    published_at=_millis_datetime(post.get("createdAt") or post.get("publishedAt")),
                    raw_payload_json=post,
                    content_hash=stable_hash(source.id, urn, text),
                    metrics=[
                        MetricPayload("linkedin_likes", _summary_count(post, "likesSummary", "totalLikes")),
                        MetricPayload("linkedin_comments", _summary_count(post, "commentsSummary", "totalFirstLevelComments")),
                    ],
                )
            )
        return ConnectorFetchResult(items=items)


class TikTokResearchConnector(BaseConnector):
    metadata = ConnectorMetadata(
        type="tiktok_research",
        name="TikTok Research API",
        capabilities=["content_fetch", "metrics"],
        real_fetch_enabled=True,
    )

    def fetch(self, db: Session, source: Source) -> ConnectorFetchResult:
        token = _env_secret(source, "accessTokenEnv", "TIKTOK_RESEARCH_ACCESS_TOKEN")
        query_json = source.config_json.get("queryJson")
        if not isinstance(query_json, dict):
            raise ConnectorError("TikTok Research source requires queryJson")
        response = httpx.post(
            "https://open.tiktokapis.com/v2/research/video/query/",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            params={
                "fields": "id,video_description,create_time,username,share_count,view_count,like_count,comment_count,favorites_count"
            },
            json={**query_json, "max_count": _limit(source, default=20, max_value=100)},
            timeout=20.0,
        )
        _raise_for_status(response, "TikTok Research")
        payload = response.json()
        items = []
        for video in payload.get("data", {}).get("videos", payload.get("videos", [])):
            video_id = str(video.get("id"))
            description = video.get("video_description") or "TikTok video"
            items.append(
                RawItemPayload(
                    external_id=video_id,
                    source_url=f"https://www.tiktok.com/@{video.get('username', 'user')}/video/{video_id}",
                    title=_first_line(description),
                    content_text=description,
                    author=video.get("username"),
                    published_at=_unix_datetime(video.get("create_time")),
                    raw_payload_json=video,
                    content_hash=stable_hash(source.id, video_id, description),
                    metrics=[
                        MetricPayload("tiktok_shares", int(video.get("share_count", 0))),
                        MetricPayload("tiktok_views", int(video.get("view_count", 0))),
                        MetricPayload("tiktok_likes", int(video.get("like_count", 0))),
                        MetricPayload("tiktok_comments", int(video.get("comment_count", 0))),
                        MetricPayload("tiktok_favorites", int(video.get("favorites_count", 0))),
                    ],
                )
            )
        return ConnectorFetchResult(items=items)


def _env_secret(source: Source, config_key: str, default_env_key: str) -> str:
    env_key = str(source.config_json.get(config_key) or default_env_key)
    value = getenv(env_key, "").strip()
    if not value:
        raise ConnectorError(f"Missing required environment variable: {env_key}")
    return value


def _raise_for_status(response: httpx.Response, provider: str) -> None:
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        status_code = exc.response.status_code
        if status_code == 429:
            reset = exc.response.headers.get("x-rate-limit-reset")
            suffix = f", reset={reset}" if reset else ""
            raise ConnectorError(f"{provider} rate limit or quota exhausted: HTTP 429{suffix}") from exc
        if status_code in {401, 403}:
            raise ConnectorError(f"{provider} credential or permission rejected: HTTP {status_code}") from exc
        raise ConnectorError(f"{provider} API request failed: HTTP {status_code}") from exc


def _required_config(source: Source, key: str) -> str:
    value = source.config_json.get(key)
    if value is None or str(value).strip() == "":
        raise ConnectorError(f"{source.type} source requires {key}")
    return str(value).strip()


def _limit(source: Source, *, default: int, max_value: int) -> int:
    try:
        value = int(source.config_json.get("limit", default))
    except (TypeError, ValueError):
        value = default
    return max(1, min(value, max_value))


def _int_config(source: Source, key: str, *, default: int, min_value: int, max_value: int) -> int:
    try:
        value = int(source.config_json.get(key, default))
    except (TypeError, ValueError):
        value = default
    return max(min_value, min(value, max_value))


def _first_line(value: str) -> str:
    return " ".join(value.strip().split())[:180]


def _unix_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    try:
        return datetime.fromtimestamp(int(value), timezone.utc)
    except (TypeError, ValueError, OSError):
        return None


def _millis_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    try:
        timestamp = int(value)
        if timestamp > 10_000_000_000:
            timestamp = timestamp // 1000
        return datetime.fromtimestamp(timestamp, timezone.utc)
    except (TypeError, ValueError, OSError):
        return None


def _slack_ts_datetime(value: str) -> datetime | None:
    try:
        return datetime.fromtimestamp(float(value), timezone.utc)
    except (TypeError, ValueError, OSError):
        return None


def _reaction_count(value: Any) -> int:
    if not isinstance(value, list):
        return 0
    total = 0
    for item in value:
        if isinstance(item, dict):
            total += int(item.get("count", 0) or 0)
    return total


def _summary_count(payload: dict[str, Any], summary_key: str, count_key: str) -> int:
    summary = payload.get(summary_key)
    if not isinstance(summary, dict):
        return 0
    return int(summary.get(count_key, 0) or 0)


def _telegram_message_url(chat: dict, message: dict) -> str | None:
    username = chat.get("username")
    if username:
        return f"https://t.me/{username}/{message.get('message_id')}"
    return None
