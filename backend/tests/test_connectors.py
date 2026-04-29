from app.connectors.youtube_placeholder import fetch_youtube_placeholder
from app.connectors.core import PlaceholderFetchError


def test_youtube_placeholder_is_registered_without_fetch(client):
    response = client.get("/api/connectors")

    assert response.status_code == 200
    payload = {item["type"]: item for item in response.json()}
    assert payload["youtube_placeholder"] == {
        "type": "youtube_placeholder",
        "name": "YouTube placeholder",
        "capabilities": [],
        "realFetchEnabled": False,
    }
    assert payload["rss"]["realFetchEnabled"] is True
    assert payload["hacker_news"]["realFetchEnabled"] is True
    assert payload["github_repo"]["realFetchEnabled"] is True
    assert payload["github_release"]["realFetchEnabled"] is True
    assert payload["webpage"]["realFetchEnabled"] is True
    assert payload["reddit_subreddit"]["realFetchEnabled"] is True
    assert payload["bluesky_search"]["realFetchEnabled"] is True
    assert payload["bluesky_actor_feed"]["realFetchEnabled"] is True
    assert payload["mastodon_timeline"]["realFetchEnabled"] is True


def test_youtube_placeholder_fetch_is_blocked():
    try:
        fetch_youtube_placeholder()
    except PlaceholderFetchError as exc:
        assert "out of scope" in str(exc)
    else:
        raise AssertionError("YouTube placeholder must not perform real fetching")
