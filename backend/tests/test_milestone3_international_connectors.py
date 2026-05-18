from dataclasses import dataclass
from datetime import timezone

from sqlalchemy import select

from app.db.models import MetricSnapshot, RawItem, Source
from app.services.connector_runner import run_source_fetch


@dataclass
class FakeResponse:
    payload: object

    def json(self):
        return self.payload

    def raise_for_status(self):
        return None


def metric_values(db_session) -> dict[str, int]:
    metrics = db_session.scalars(select(MetricSnapshot)).all()
    return {metric.metric_type: metric.value for metric in metrics}


def test_international_connector_missing_credential_records_fetchrun_failure(monkeypatch, db_session):
    monkeypatch.delenv("X_BEARER_TOKEN", raising=False)
    source = Source(
        type="x_recent_search",
        name="X AI",
        config_json={"query": "ai", "retryAttempts": 1},
    )
    db_session.add(source)
    db_session.commit()

    run = run_source_fetch(db_session, source)

    assert run.status == "failed"
    assert "Missing required environment variable: X_BEARER_TOKEN" in (run.error_message or "")
    assert source.last_error == run.error_message


def test_x_recent_search_connector_writes_raw_items_and_metrics(monkeypatch, db_session):
    monkeypatch.setenv("X_BEARER_TOKEN", "token")

    def fake_get(url, **kwargs):
        assert url == "https://api.x.com/2/tweets/search/recent"
        assert kwargs["headers"]["Authorization"] == "Bearer token"
        assert kwargs["params"]["query"] == "open source ai -is:retweet -is:reply"
        assert kwargs["params"]["expansions"] == "author_id,attachments.media_keys"
        return FakeResponse(
            {
                "data": [
                    {
                        "id": "tweet-1",
                        "text": "Open source AI launch",
                        "author_id": "author-1",
                        "created_at": "2026-01-01T00:00:00Z",
                        "public_metrics": {
                            "retweet_count": 3,
                            "reply_count": 4,
                            "like_count": 5,
                            "quote_count": 6,
                        },
                    }
                ]
            }
        )

    monkeypatch.setattr("app.connectors.international.httpx.get", fake_get)
    source = Source(type="x_recent_search", name="X AI", config_json={"query": "open source ai", "limit": 1})
    db_session.add(source)
    db_session.commit()

    run = run_source_fetch(db_session, source)

    assert run.status == "success"
    assert run.items_created == 1
    item = db_session.scalar(select(RawItem))
    assert item is not None
    assert item.source_url == "https://x.com/i/web/status/tweet-1"
    assert metric_values(db_session) == {
        "x_retweets": 3,
        "x_replies": 4,
        "x_likes": 5,
        "x_quotes": 6,
    }


def test_x_recent_search_connector_fetches_source_library_handles_via_timelines(monkeypatch, db_session):
    monkeypatch.setenv("X_BEARER_TOKEN", "token")
    requests = []

    def fake_get(url, **kwargs):
        requests.append((url, kwargs))
        assert kwargs["headers"]["Authorization"] == "Bearer token"
        if url == "https://api.x.com/2/users/by/username/OpenAIDevs":
            return FakeResponse({"data": {"id": "2244994945", "username": "OpenAIDevs", "name": "OpenAI Developers"}})
        if url == "https://api.x.com/2/users/2244994945/tweets":
            assert kwargs["params"]["exclude"] == "retweets,replies"
            assert kwargs["params"]["max_results"] == 5
            return FakeResponse(
                {
                    "data": [
                        {
                            "id": "100",
                            "text": "New API tools are available",
                            "author_id": "2244994945",
                            "created_at": "2026-01-01T00:00:00Z",
                            "public_metrics": {
                                "retweet_count": 7,
                                "reply_count": 8,
                                "like_count": 9,
                                "quote_count": 10,
                            },
                        }
                    ],
                    "includes": {
                        "users": [
                            {
                                "id": "2244994945",
                                "username": "OpenAIDevs",
                                "name": "OpenAI Developers",
                            }
                        ]
                    },
                }
            )
        raise AssertionError(f"unexpected url: {url}")

    monkeypatch.setattr("app.connectors.international.httpx.get", fake_get)
    source = Source(
        type="x_recent_search",
        name="P0 / OpenAI Developers (@OpenAIDevs)",
        config_json={"handle": "OpenAIDevs", "query": "from:OpenAIDevs", "limit": 5, "perHandleLimit": 5, "retryAttempts": 1},
    )
    db_session.add(source)
    db_session.commit()

    run = run_source_fetch(db_session, source)
    db_session.refresh(source)

    assert run.status == "success"
    assert run.items_created == 1
    assert source.config_json["lastXFetchMode"] == "user_timelines"
    assert source.config_json["userIdsByHandle"]["openaidevs"] == "2244994945"
    assert source.config_json["latestTweetIdsByHandle"]["openaidevs"] == "100"
    item = db_session.scalar(select(RawItem))
    assert item is not None
    assert item.author == "OpenAIDevs"
    assert item.source_url == "https://x.com/OpenAIDevs/status/100"
    assert len(requests) == 2
    assert metric_values(db_session) == {
        "x_retweets": 7,
        "x_replies": 8,
        "x_likes": 9,
        "x_quotes": 10,
    }


def test_youtube_channel_connector_writes_raw_items_and_metrics(monkeypatch, db_session):
    monkeypatch.setenv("YOUTUBE_API_KEY", "yt-key")

    def fake_get(url, **kwargs):
        assert url == "https://www.googleapis.com/youtube/v3/search"
        assert kwargs["params"]["channelId"] == "channel-1"
        assert kwargs["params"]["key"] == "yt-key"
        return FakeResponse(
            {
                "items": [
                    {
                        "id": {"videoId": "video-1"},
                        "snippet": {
                            "title": "Research update",
                            "description": "Video notes",
                            "channelTitle": "AI Lab",
                            "publishedAt": "2026-01-01T00:00:00Z",
                        },
                    }
                ]
            }
        )

    monkeypatch.setattr("app.connectors.international.httpx.get", fake_get)
    source = Source(type="youtube_channel", name="YouTube AI", config_json={"channelId": "channel-1", "limit": 1})
    db_session.add(source)
    db_session.commit()

    run = run_source_fetch(db_session, source)

    assert run.status == "success"
    item = db_session.scalar(select(RawItem))
    assert item is not None
    assert item.source_url == "https://www.youtube.com/watch?v=video-1"
    assert metric_values(db_session) == {"youtube_search_rank": 1}


def test_telegram_updates_connector_writes_raw_items_metrics_and_offset(monkeypatch, db_session):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "tg-token")

    def fake_get(url, **kwargs):
        assert url == "https://api.telegram.org/bottg-token/getUpdates"
        assert kwargs["params"]["limit"] == 1
        return FakeResponse(
            {
                "ok": True,
                "result": [
                    {
                        "update_id": 100,
                        "channel_post": {
                            "message_id": 5,
                            "date": 1_700_000_000,
                            "text": "Telegram channel update",
                            "views": 9,
                            "chat": {"id": -100, "username": "research_channel", "title": "Research Channel"},
                        },
                    }
                ],
            }
        )

    monkeypatch.setattr("app.connectors.international.httpx.get", fake_get)
    source = Source(
        type="telegram_updates",
        name="Telegram Research",
        config_json={"chatId": "-100", "limit": 1},
    )
    db_session.add(source)
    db_session.commit()

    run = run_source_fetch(db_session, source)
    db_session.refresh(source)

    assert run.status == "success"
    assert source.config_json["offset"] == 101
    item = db_session.scalar(select(RawItem))
    assert item is not None
    assert item.source_url == "https://t.me/research_channel/5"
    assert item.published_at is not None
    assert item.published_at.replace(tzinfo=timezone.utc).timestamp() == 1_700_000_000
    assert metric_values(db_session) == {"telegram_views": 9}


def test_discord_channel_connector_writes_raw_items_and_metrics(monkeypatch, db_session):
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "discord-token")

    def fake_get(url, **kwargs):
        assert url == "https://discord.com/api/v10/channels/channel-1/messages"
        assert kwargs["headers"]["Authorization"] == "Bot discord-token"
        return FakeResponse(
            [
                {
                    "id": "message-1",
                    "content": "Discord update",
                    "timestamp": "2026-01-01T00:00:00Z",
                    "author": {"username": "bot-user"},
                    "reactions": [{"count": 2}],
                    "attachments": [{"id": "attachment-1"}],
                }
            ]
        )

    monkeypatch.setattr("app.connectors.international.httpx.get", fake_get)
    source = Source(
        type="discord_channel",
        name="Discord Research",
        config_json={"channelId": "channel-1", "guildId": "guild-1", "limit": 1},
    )
    db_session.add(source)
    db_session.commit()

    run = run_source_fetch(db_session, source)

    assert run.status == "success"
    item = db_session.scalar(select(RawItem))
    assert item is not None
    assert item.source_url == "https://discord.com/channels/guild-1/channel-1/message-1"
    assert metric_values(db_session) == {"discord_reactions": 2, "discord_attachments": 1}


def test_slack_channel_connector_writes_raw_items_and_metrics(monkeypatch, db_session):
    monkeypatch.setenv("SLACK_BOT_TOKEN", "slack-token")

    def fake_post(url, **kwargs):
        assert url == "https://slack.com/api/conversations.history"
        assert kwargs["headers"]["Authorization"] == "Bearer slack-token"
        assert kwargs["data"]["channel"] == "channel-1"
        return FakeResponse(
            {
                "ok": True,
                "messages": [
                    {
                        "ts": "1700000000.000100",
                        "text": "Slack workspace update",
                        "user": "user-1",
                        "reactions": [{"count": 4}],
                    }
                ],
            }
        )

    monkeypatch.setattr("app.connectors.international.httpx.post", fake_post)
    source = Source(type="slack_channel", name="Slack Research", config_json={"channelId": "channel-1", "limit": 1})
    db_session.add(source)
    db_session.commit()

    run = run_source_fetch(db_session, source)

    assert run.status == "success"
    item = db_session.scalar(select(RawItem))
    assert item is not None
    assert item.source_url == "https://slack.com/app_redirect?channel=channel-1&message_ts=1700000000.000100"
    assert metric_values(db_session) == {"slack_reactions": 4}


def test_linkedin_posts_connector_writes_raw_items_and_metrics(monkeypatch, db_session):
    monkeypatch.setenv("LINKEDIN_ACCESS_TOKEN", "linkedin-token")

    def fake_get(url, **kwargs):
        assert url == "https://api.linkedin.com/rest/posts"
        assert kwargs["headers"]["Authorization"] == "Bearer linkedin-token"
        assert kwargs["params"]["author"] == "urn:li:organization:1"
        return FakeResponse(
            {
                "elements": [
                    {
                        "id": "urn:li:share:1",
                        "author": "urn:li:organization:1",
                        "commentary": {"text": "LinkedIn product update"},
                        "createdAt": 1_700_000_000_000,
                        "permalink": "https://www.linkedin.com/feed/update/urn:li:share:1",
                        "likesSummary": {"totalLikes": 8},
                        "commentsSummary": {"totalFirstLevelComments": 3},
                    }
                ]
            }
        )

    monkeypatch.setattr("app.connectors.international.httpx.get", fake_get)
    source = Source(
        type="linkedin_posts",
        name="LinkedIn Research",
        config_json={"authorUrn": "urn:li:organization:1", "limit": 1},
    )
    db_session.add(source)
    db_session.commit()

    run = run_source_fetch(db_session, source)

    assert run.status == "success"
    item = db_session.scalar(select(RawItem))
    assert item is not None
    assert item.title == "LinkedIn product update"
    assert metric_values(db_session) == {"linkedin_likes": 8, "linkedin_comments": 3}


def test_tiktok_research_connector_writes_raw_items_and_metrics(monkeypatch, db_session):
    monkeypatch.setenv("TIKTOK_RESEARCH_ACCESS_TOKEN", "tiktok-token")

    def fake_post(url, **kwargs):
        assert url == "https://open.tiktokapis.com/v2/research/video/query/"
        assert kwargs["headers"]["Authorization"] == "Bearer tiktok-token"
        assert kwargs["json"]["max_count"] == 1
        return FakeResponse(
            {
                "data": {
                    "videos": [
                        {
                            "id": "video-1",
                            "video_description": "TikTok research signal",
                            "create_time": 1_700_000_000,
                            "username": "researcher",
                            "share_count": 1,
                            "view_count": 2,
                            "like_count": 3,
                            "comment_count": 4,
                            "favorites_count": 5,
                        }
                    ]
                }
            }
        )

    monkeypatch.setattr("app.connectors.international.httpx.post", fake_post)
    source = Source(
        type="tiktok_research",
        name="TikTok Research",
        config_json={"queryJson": {"query": {"and": [{"operation": "EQ", "field_name": "keyword", "field_values": ["ai"]}]}}, "limit": 1},
    )
    db_session.add(source)
    db_session.commit()

    run = run_source_fetch(db_session, source)

    assert run.status == "success"
    item = db_session.scalar(select(RawItem))
    assert item is not None
    assert item.source_url == "https://www.tiktok.com/@researcher/video/video-1"
    assert item.published_at is not None
    assert item.published_at.replace(tzinfo=timezone.utc).timestamp() == 1_700_000_000
    assert metric_values(db_session) == {
        "tiktok_shares": 1,
        "tiktok_views": 2,
        "tiktok_likes": 3,
        "tiktok_comments": 4,
        "tiktok_favorites": 5,
    }
