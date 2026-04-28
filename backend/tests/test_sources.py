def test_source_crud(client):
    create_response = client.post(
        "/api/sources",
        json={
            "type": "rss",
            "name": "Example RSS",
            "url": "https://example.com/feed.xml",
            "enabled": True,
            "weight": 2,
            "pollIntervalMinutes": 30,
            "configJson": {"category": "ai"},
        },
    )
    assert create_response.status_code == 201
    created = create_response.json()
    source_id = created["id"]
    assert created["name"] == "Example RSS"
    assert created["pollIntervalMinutes"] == 30

    list_response = client.get("/api/sources")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    get_response = client.get(f"/api/sources/{source_id}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == source_id

    update_response = client.patch(
        f"/api/sources/{source_id}",
        json={"enabled": False, "pollIntervalMinutes": 45},
    )
    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["enabled"] is False
    assert updated["pollIntervalMinutes"] == 45

    delete_response = client.delete(f"/api/sources/{source_id}")
    assert delete_response.status_code == 204

    missing_response = client.get(f"/api/sources/{source_id}")
    assert missing_response.status_code == 404
