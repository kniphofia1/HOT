from sqlalchemy import select

from app.db.models import EventCandidate, RawItem, Source


def test_source_market_exposes_available_and_deferred_platforms(client):
    response = client.get("/api/source-market")

    assert response.status_code == 200
    payload = response.json()
    by_platform = {item["platform"]: item for item in payload}
    assert by_platform["Reddit"]["status"] == "available"
    assert by_platform["X"]["status"] == "available"
    assert by_platform["X"]["requiresCredential"] is True
    assert by_platform["知乎"]["automationLevel"] == "manual"
    assert by_platform["YouTube"]["requiresCredential"] is True


def test_manual_link_ingestion_creates_raw_item_and_candidate(client, db_session):
    response = client.post(
        "/api/items/manual",
        json={
            "title": "Manual evidence item",
            "sourceUrl": "https://example.com/manual",
            "contentText": "Manual evidence quote",
            "sourceName": "Manual Research",
            "author": "analyst",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["title"] == "Manual evidence item"
    source = db_session.scalar(select(Source).where(Source.type == "manual_link"))
    assert source is not None
    assert source.name == "Manual Research"
    raw_item = db_session.scalar(select(RawItem).where(RawItem.source_id == source.id))
    assert raw_item is not None
    assert raw_item.source_url == "https://example.com/manual"
    candidate = db_session.scalar(select(EventCandidate).where(EventCandidate.raw_item_id == raw_item.id))
    assert candidate is not None


def test_manual_link_ingestion_deduplicates_same_url(client, db_session):
    body = {
        "title": "Manual duplicate",
        "sourceUrl": "https://example.com/duplicate",
        "contentText": "First quote",
        "sourceName": "Manual Research",
    }
    assert client.post("/api/items/manual", json=body).status_code == 201
    body["contentText"] = "Updated quote"
    assert client.post("/api/items/manual", json=body).status_code == 201

    items = db_session.scalars(select(RawItem)).all()
    assert len(items) == 1
    assert items[0].content_text == "Updated quote"
