from app.services.ai import AiCandidate, OpenAICompatibleAiProvider


class FakeSettings:
    ai_api_key = "test-key"
    ai_model = "deepseek-v4-flash"
    ai_fast_model = "deepseek-v4-flash"
    ai_high_model = "deepseek-v4-pro"
    ai_base_url = "https://api.deepseek.com"


class FakeResponse:
    def __init__(self, content: str) -> None:
        self._content = content

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return {"choices": [{"message": {"content": self._content}}]}


def test_deepseek_model_routing_uses_fast_for_internal_and_high_for_user_outputs(monkeypatch):
    calls: list[dict] = []

    def fake_post(url, headers, json, timeout):
        calls.append(json)
        if "Classify one intelligence event" in json["messages"][0]["content"]:
            return FakeResponse(
                '{"industries":["ai"],"confidence":88,"reason":"模型发布相关","noise":false,"off_topic":false}'
            )
        if "Translate intelligence event fields" in json["messages"][0]["content"]:
            return FakeResponse('{"title":"中文标题","summary":"中文摘要"}')
        if "You generate a Chinese industry intelligence report" in json["messages"][0]["content"]:
            return FakeResponse("# 中文报告")
        return FakeResponse('{"title":"聚类标题","summary":"聚类摘要","confidence":80,"candidate_ids":["c1"]}')

    monkeypatch.setattr("app.services.ai.httpx.post", fake_post)

    provider = OpenAICompatibleAiProvider(FakeSettings())
    provider.summarize_cluster([AiCandidate("c1", "OpenAI launches model", "content", "OpenAI", "https://example.com")])
    provider.classify_event(
        title="OpenAI launches model",
        summary="content",
        source_names=["OpenAI"],
        source_industries=["ai"],
        evidence=[{"title": "OpenAI launches model", "content": "content", "sourceName": "OpenAI", "url": "https://example.com"}],
    )
    provider.translate_event(title="OpenAI launches model", summary="content")
    provider.generate_report({"title": "AI 行业日报", "events": []})

    assert [call["model"] for call in calls] == [
        "deepseek-v4-flash",
        "deepseek-v4-flash",
        "deepseek-v4-pro",
        "deepseek-v4-pro",
    ]
    assert calls[0]["thinking"] == {"type": "disabled"}
    assert calls[1]["thinking"] == {"type": "disabled"}
    assert calls[2]["thinking"] == {"type": "disabled"}
    assert calls[3]["thinking"] == {"type": "enabled", "reasoning_effort": "high"}
