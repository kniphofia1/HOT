from app.connectors.youtube_placeholder import fetch_youtube_placeholder
from app.connectors.core import PlaceholderFetchError


def test_youtube_placeholder_is_registered_without_fetch(client):
    response = client.get("/api/connectors")

    assert response.status_code == 200
    payload = response.json()
    assert payload == [
        {
            "type": "youtube_placeholder",
            "name": "YouTube placeholder",
            "capabilities": [],
            "realFetchEnabled": False,
        }
    ]


def test_youtube_placeholder_fetch_is_blocked():
    try:
        fetch_youtube_placeholder()
    except PlaceholderFetchError as exc:
        assert "out of scope" in str(exc)
    else:
        raise AssertionError("YouTube placeholder must not perform real fetching")
