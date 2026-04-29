from dataclasses import dataclass

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


def test_reddit_subreddit_connector_writes_raw_items_and_metrics(monkeypatch, db_session):
    monkeypatch.delenv("REDDIT_CLIENT_ID", raising=False)
    monkeypatch.delenv("REDDIT_CLIENT_SECRET", raising=False)

    def fake_get(url, **kwargs):
        assert url == "https://www.reddit.com/r/MachineLearning/hot.json"
        return FakeResponse(
            payload={
                "data": {
                    "children": [
                        {
                            "data": {
                                "name": "t3_abc",
                                "id": "abc",
                                "title": "Open model benchmark discussion",
                                "permalink": "/r/MachineLearning/comments/abc/open_model/",
                                "url": "https://example.com/model",
                                "selftext": "Detailed discussion",
                                "subreddit": "MachineLearning",
                                "score": 123,
                                "num_comments": 45,
                                "author": "researcher",
                                "created_utc": 1_700_000_000,
                            }
                        }
                    ]
                }
            }
        )

    monkeypatch.setattr("app.connectors.social.httpx.get", fake_get)
    source = Source(
        type="reddit_subreddit",
        name="Reddit ML",
        config_json={"subreddit": "MachineLearning", "sort": "hot", "limit": 1},
    )
    db_session.add(source)
    db_session.commit()

    run = run_source_fetch(db_session, source)

    assert run.status == "success"
    assert run.items_created == 1
    item = db_session.scalar(select(RawItem))
    assert item is not None
    assert item.title == "Reddit: Open model benchmark discussion"
    assert item.source_url == "https://www.reddit.com/r/MachineLearning/comments/abc/open_model/"
    metrics = db_session.scalars(select(MetricSnapshot)).all()
    assert {metric.metric_type for metric in metrics} == {"reddit_score", "reddit_comments"}


def test_bluesky_search_connector_writes_raw_items_and_metrics(monkeypatch, db_session):
    def fake_get(url, **kwargs):
        assert url == "https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts"
        assert kwargs["params"]["q"] == "open source AI"
        return FakeResponse(
            payload={
                "posts": [
                    {
                        "uri": "at://did:plc:test/app.bsky.feed.post/3abc",
                        "cid": "cid-1",
                        "author": {"handle": "example.bsky.social"},
                        "record": {"text": "Open source AI systems are moving fast", "createdAt": "2026-01-01T00:00:00Z"},
                        "replyCount": 2,
                        "repostCount": 3,
                        "likeCount": 5,
                    }
                ]
            }
        )

    monkeypatch.setattr("app.connectors.social.httpx.get", fake_get)
    source = Source(
        type="bluesky_search",
        name="Bluesky AI",
        config_json={"query": "open source AI", "limit": 1},
    )
    db_session.add(source)
    db_session.commit()

    run = run_source_fetch(db_session, source)

    assert run.status == "success"
    assert run.items_created == 1
    item = db_session.scalar(select(RawItem))
    assert item is not None
    assert item.title.startswith("Bluesky: Open source AI systems")
    assert item.source_url == "https://bsky.app/profile/example.bsky.social/post/3abc"
    metrics = db_session.scalars(select(MetricSnapshot)).all()
    assert {metric.metric_type for metric in metrics} == {
        "bluesky_replies",
        "bluesky_reposts",
        "bluesky_likes",
    }


def test_bluesky_actor_feed_connector_writes_raw_items_and_metrics(monkeypatch, db_session):
    def fake_get(url, **kwargs):
        assert url == "https://public.api.bsky.app/xrpc/app.bsky.feed.getAuthorFeed"
        assert kwargs["params"]["actor"] == "bsky.app"
        return FakeResponse(
            payload={
                "feed": [
                    {
                        "post": {
                            "uri": "at://did:plc:test/app.bsky.feed.post/3feed",
                            "cid": "cid-feed",
                            "author": {"handle": "bsky.app"},
                            "record": {"text": "A public Bluesky product update", "createdAt": "2026-01-01T00:00:00Z"},
                            "replyCount": 7,
                            "repostCount": 11,
                            "likeCount": 13,
                        }
                    }
                ]
            }
        )

    monkeypatch.setattr("app.connectors.social.httpx.get", fake_get)
    source = Source(
        type="bluesky_actor_feed",
        name="Bluesky official",
        config_json={"actor": "bsky.app", "limit": 1},
    )
    db_session.add(source)
    db_session.commit()

    run = run_source_fetch(db_session, source)

    assert run.status == "success"
    assert run.items_created == 1
    item = db_session.scalar(select(RawItem))
    assert item is not None
    assert item.title == "Bluesky: A public Bluesky product update"
    assert item.source_url == "https://bsky.app/profile/bsky.app/post/3feed"
    metrics = db_session.scalars(select(MetricSnapshot)).all()
    assert {metric.metric_type for metric in metrics} == {
        "bluesky_replies",
        "bluesky_reposts",
        "bluesky_likes",
    }


def test_mastodon_timeline_connector_writes_raw_items_and_metrics(monkeypatch, db_session):
    def fake_get(url, **kwargs):
        assert url == "https://mastodon.social/api/v1/timelines/tag/ai"
        assert kwargs["params"]["limit"] == 1
        return FakeResponse(
            payload=[
                {
                    "id": "status-1",
                    "url": "https://mastodon.social/@researcher/1",
                    "uri": "tag:mastodon.social,2026-01-01:objectId=1",
                    "content": "<p>AI research update<br />with public notes</p>",
                    "created_at": "2026-01-01T00:00:00Z",
                    "account": {"acct": "researcher"},
                    "replies_count": 4,
                    "reblogs_count": 6,
                    "favourites_count": 8,
                }
            ]
        )

    monkeypatch.setattr("app.connectors.social.httpx.get", fake_get)
    source = Source(
        type="mastodon_timeline",
        name="Mastodon AI",
        url="https://mastodon.social",
        config_json={"instanceUrl": "https://mastodon.social", "mode": "tag", "tag": "ai", "limit": 1},
    )
    db_session.add(source)
    db_session.commit()

    run = run_source_fetch(db_session, source)

    assert run.status == "success"
    assert run.items_created == 1
    item = db_session.scalar(select(RawItem))
    assert item is not None
    assert item.title == "Mastodon: AI research update with public notes"
    assert item.content_text is not None
    assert "AI research update with public notes" in item.content_text
    metrics = db_session.scalars(select(MetricSnapshot)).all()
    assert {metric.metric_type for metric in metrics} == {
        "mastodon_replies",
        "mastodon_reblogs",
        "mastodon_favourites",
    }
