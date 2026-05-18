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


def test_configure_default_sources_enables_registered_connectors(client):
    response = client.post("/api/sources/defaults")

    assert response.status_code == 200
    payload = response.json()
    source_types = {source["type"] for source in payload}
    assert {
        "rss",
        "webpage",
        "hacker_news",
        "github_release",
        "sec_edgar_filings",
        "x_recent_search",
    }.issubset(source_types)
    openai_source = next(source for source in payload if source["type"] == "rss" and source["name"] == "OpenAI News RSS")
    assert openai_source["configJson"]["industries"] == ["ai"]
    assert openai_source["configJson"]["sourceTier"] == "P0"
    assert openai_source["configJson"]["sourceGroup"] == "official_rss"
    claude_code_source = next(source for source in payload if source["type"] == "github_release" and source["name"] == "Claude Code GitHub Releases")
    assert claude_code_source["configJson"]["owner"] == "anthropics"
    assert claude_code_source["configJson"]["repo"] == "claude-code"
    product_x_source = next(source for source in payload if source["name"] == "X AI Product Company Accounts")
    assert product_x_source["configJson"]["sourceTier"] == "P1"
    assert product_x_source["configJson"]["fetchMode"] == "user_timelines"
    assert product_x_source["configJson"]["handles"]
    low_priority_x_source = next(source for source in payload if source["name"] == "X AI Low Priority / Noisy Accounts")
    assert low_priority_x_source["configJson"]["sourceTier"] == "P2"
    assert all(source["configJson"].get("industries") for source in payload)
    assert all(source["configJson"].get("sourceTier") in {"P0", "P1", "P2"} for source in payload)
    assert all(source["configJson"].get("sourceGroup") for source in payload)
    assert {"ai", "semiconductor", "embodied_ai", "energy", "technology", "products"}.issubset(
        {industry for source in payload for industry in source["configJson"].get("industries", [])}
    )
    github_changelog = next(source for source in payload if source["name"] == "GitHub Changelog")
    assert github_changelog["configJson"]["industry"] == "technology"
    apple_newsroom = next(source for source in payload if source["name"] == "Apple Newsroom")
    assert apple_newsroom["configJson"]["industry"] == "products"
    sec_source = next(source for source in payload if source["type"] == "sec_edgar_filings")
    assert sec_source["configJson"]["industry"] == "semiconductor"
    assert sec_source["configJson"]["sourceGroup"] == "company_filings"
    assert sec_source["configJson"]["companies"]
    assert all(source["enabled"] for source in payload)


def test_configure_default_sources_preserves_existing_config(client):
    create_response = client.post(
        "/api/sources",
        json={
            "type": "rss",
            "name": "OpenAI News RSS",
            "url": "https://custom.example.com/feed.xml",
            "enabled": False,
            "configJson": {"topic": "custom", "ownerNote": "keep"},
        },
    )
    assert create_response.status_code == 201

    response = client.post("/api/sources/defaults")

    assert response.status_code == 200
    openai_source = next(source for source in response.json() if source["type"] == "rss" and source["name"] == "OpenAI News RSS")
    assert openai_source["enabled"] is False
    assert openai_source["url"] == "https://custom.example.com/feed.xml"
    assert "custom" in openai_source["configJson"]["topics"]
    assert openai_source["configJson"]["ownerNote"] == "keep"
