from sqlalchemy import select

from app.db.models import RawItem, Source


def test_domestic_platform_policy_endpoint_exposes_compliance_boundaries(client):
    response = client.get("/api/domestic-platforms")

    assert response.status_code == 200
    payload = response.json()
    by_platform = {item["platform"]: item for item in payload}
    assert by_platform["微博"]["status"] == "official_auth_required"
    assert by_platform["知乎"]["automationLevel"] == "manual"
    assert by_platform["小红书"]["status"] == "manual_only"
    assert "cookie_capture" in by_platform["抖音"]["prohibitedPaths"]
    assert "manual_link" in by_platform["微信公众号"]["allowedPaths"]


def test_manual_domestic_link_records_platform_in_raw_payload(client, db_session):
    response = client.post(
        "/api/items/manual",
        json={
            "title": "Zhihu public answer",
            "sourceUrl": "https://www.zhihu.com/question/1/answer/2",
            "contentText": "Manual public evidence",
            "platform": "知乎",
            "sourceName": "Manual Zhihu",
        },
    )

    assert response.status_code == 201
    source = db_session.scalar(select(Source).where(Source.type == "manual_link", Source.name == "Manual Zhihu"))
    assert source is not None
    item = db_session.scalar(select(RawItem).where(RawItem.source_id == source.id))
    assert item is not None
    assert item.raw_payload_json["platform"] == "知乎"
    assert item.raw_payload_json["ingestionMode"] == "manual_link"
