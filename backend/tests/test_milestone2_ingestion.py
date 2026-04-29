from dataclasses import dataclass

import pytest
from sqlalchemy import select

from app.db.models import FetchRun, MetricSnapshot, RawItem, Source, WebMonitorTarget, WebpageSnapshot
from app.services.connector_runner import run_enabled_sources, run_source_fetch


@dataclass
class FakeResponse:
    payload: object | None = None
    text: str = ""
    content: bytes = b""

    def json(self):
        return self.payload

    def raise_for_status(self):
        return None


RSS_FEED = b"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0">
  <channel>
    <title>Example RSS</title>
    <item>
      <guid>item-1</guid>
      <title>First item</title>
      <link>https://example.com/first</link>
      <description>First summary</description>
    </item>
  </channel>
</rss>
"""


ATOM_FEED = b"""<?xml version="1.0" encoding="UTF-8" ?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Example Atom</title>
  <entry>
    <id>atom-1</id>
    <title>Atom item</title>
    <link href="https://example.com/atom" />
    <summary>Atom summary</summary>
  </entry>
</feed>
"""


RSS_FEED_2 = b"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0">
  <channel>
    <title>Example RSS 2</title>
    <item>
      <guid>item-2</guid>
      <title>Second item</title>
      <link>https://example.com/second</link>
      <description>Second summary</description>
    </item>
  </channel>
</rss>
"""


def test_rss_connector_parses_three_feed_shapes_and_deduplicates(monkeypatch, db_session):
    feeds = [RSS_FEED, ATOM_FEED, RSS_FEED_2]

    def fake_get(url, **kwargs):
        index = int(url.rsplit("/", 1)[-1])
        return FakeResponse(content=feeds[index])

    monkeypatch.setattr("app.connectors.rss.httpx.get", fake_get)

    sources = []
    for index in range(3):
        source = Source(type="rss", name=f"RSS {index}", url=f"https://example.com/{index}", config_json={})
        db_session.add(source)
        sources.append(source)
    db_session.commit()

    for source in sources:
        first_run = run_source_fetch(db_session, source)
        second_run = run_source_fetch(db_session, source)
        assert first_run.status == "success"
        assert first_run.items_created == 1
        assert second_run.status == "success"
        assert second_run.items_created == 0

    assert len(db_session.scalars(select(RawItem)).all()) == 3


def test_hacker_news_connector_writes_raw_items_and_metrics(monkeypatch, db_session):
    def fake_get(url, **kwargs):
        if url.endswith("topstories.json"):
            return FakeResponse(payload=[100, 200])
        story_id = url.rsplit("/", 1)[-1].split(".")[0]
        return FakeResponse(
            payload={
                "id": int(story_id),
                "type": "story",
                "title": f"HN story {story_id}",
                "url": f"https://example.com/{story_id}",
                "score": 42,
                "descendants": 7,
                "by": "tester",
            }
        )

    monkeypatch.setattr("app.connectors.hacker_news.httpx.get", fake_get)
    source = Source(
        type="hacker_news",
        name="HN top",
        url="https://news.ycombinator.com",
        config_json={"listType": "top", "limit": 2},
    )
    db_session.add(source)
    db_session.commit()

    run = run_source_fetch(db_session, source)

    assert run.status == "success"
    assert run.items_created == 2
    assert len(db_session.scalars(select(RawItem)).all()) == 2
    metrics = db_session.scalars(select(MetricSnapshot)).all()
    assert {metric.metric_type for metric in metrics} == {"hn_score", "hn_comments"}


def test_hacker_news_connector_supports_show_stories(monkeypatch, db_session):
    def fake_get(url, **kwargs):
        if url.endswith("showstories.json"):
            return FakeResponse(payload=[300])
        return FakeResponse(
            payload={
                "id": 300,
                "type": "story",
                "title": "Show HN: Example",
                "url": "https://example.com/show",
                "score": 9,
                "descendants": 2,
                "by": "maker",
            }
        )

    monkeypatch.setattr("app.connectors.hacker_news.httpx.get", fake_get)
    source = Source(
        type="hacker_news",
        name="HN show",
        url="https://news.ycombinator.com/show",
        config_json={"listType": "show", "limit": 1},
    )
    db_session.add(source)
    db_session.commit()

    run = run_source_fetch(db_session, source)

    assert run.status == "success"
    assert run.items_created == 1
    item = db_session.scalar(select(RawItem))
    assert item is not None
    assert item.title == "Show HN: Example"


def test_github_repo_and_release_connectors_write_metrics(monkeypatch, db_session):
    def fake_get(url, headers=None, timeout=None):
        if url.endswith("/releases"):
            return FakeResponse(
                payload=[
                    {
                        "id": 10,
                        "tag_name": "v1.0.0",
                        "html_url": "https://github.com/example/repo/releases/tag/v1.0.0",
                        "body": "Release body",
                        "author": None,
                        "assets": [{"download_count": 3}, {"download_count": 4}],
                    }
                ]
            )
        return FakeResponse(
            payload={
                "full_name": "example/repo",
                "html_url": "https://github.com/example/repo",
                "description": "Example repo",
                "stargazers_count": 11,
                "forks_count": 2,
                "open_issues_count": 1,
            }
        )

    monkeypatch.setattr("app.connectors.github.httpx.get", fake_get)
    repo_source = Source(
        type="github_repo",
        name="Repo",
        url="https://github.com/example/repo",
        config_json={},
    )
    release_source = Source(
        type="github_release",
        name="Release",
        url="https://github.com/example/repo",
        config_json={"limit": 1},
    )
    db_session.add_all([repo_source, release_source])
    db_session.commit()

    repo_run = run_source_fetch(db_session, repo_source)
    release_run = run_source_fetch(db_session, release_source)

    assert repo_run.status == "success"
    assert release_run.status == "success"
    metrics = db_session.scalars(select(MetricSnapshot)).all()
    assert {metric.metric_type for metric in metrics} == {
        "github_stars",
        "github_forks",
        "github_open_issues",
        "github_release_downloads",
    }


def test_webpage_connector_creates_snapshot_only_when_content_changes(monkeypatch, db_session):
    pages = [
        "<html><body><main>Alpha content</main></body></html>",
        "<html><body><main>Alpha content</main></body></html>",
        "<html><body><main>Beta content</main></body></html>",
    ]

    def fake_get(url, **kwargs):
        return FakeResponse(text=pages.pop(0))

    monkeypatch.setattr("app.connectors.webpage.httpx.get", fake_get)
    source = Source(
        type="webpage",
        name="Watched page",
        url="https://example.com/page",
        config_json={"cssSelector": "main"},
    )
    db_session.add(source)
    db_session.commit()

    first_run = run_source_fetch(db_session, source)
    second_run = run_source_fetch(db_session, source)
    third_run = run_source_fetch(db_session, source)

    assert first_run.items_created == 1
    assert second_run.items_created == 0
    assert third_run.items_created == 1
    assert len(db_session.scalars(select(WebMonitorTarget)).all()) == 1
    assert len(db_session.scalars(select(WebpageSnapshot)).all()) == 2
    assert len(db_session.scalars(select(RawItem)).all()) == 2


def test_failed_source_does_not_block_other_sources(monkeypatch, db_session):
    def fake_get(url, **kwargs):
        if "bad" in url:
            raise RuntimeError("network failed")
        return FakeResponse(content=RSS_FEED)

    monkeypatch.setattr("app.connectors.rss.httpx.get", fake_get)
    bad = Source(type="rss", name="Bad", url="https://example.com/bad", config_json={})
    good = Source(type="rss", name="Good", url="https://example.com/good", config_json={})
    db_session.add_all([bad, good])
    db_session.commit()

    runs = run_enabled_sources(db_session)

    assert sorted(run.status for run in runs) == ["failed", "success"]
    assert len(db_session.scalars(select(RawItem)).all()) == 1
    assert len(db_session.scalars(select(FetchRun)).all()) == 2


def test_refresh_enabled_sources_api_isolates_failures(monkeypatch, client):
    def fake_get(url, **kwargs):
        if "bad" in url:
            raise RuntimeError("network failed")
        return FakeResponse(content=RSS_FEED)

    monkeypatch.setattr("app.connectors.rss.httpx.get", fake_get)
    client.post(
        "/api/sources",
        json={"type": "rss", "name": "Bad", "url": "https://example.com/bad", "configJson": {}},
    )
    client.post(
        "/api/sources",
        json={"type": "rss", "name": "Good", "url": "https://example.com/good", "configJson": {}},
    )

    response = client.post("/api/sources/refresh")

    assert response.status_code == 200
    statuses = sorted(run["status"] for run in response.json())
    assert statuses == ["failed", "success"]
