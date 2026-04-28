from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Protocol

import httpx

from app.core.config import Settings, get_settings


class MissingAiConfigurationError(RuntimeError):
    pass


@dataclass(frozen=True)
class AiCandidate:
    id: str
    title: str
    content_text: str | None
    source_name: str
    source_url: str | None


@dataclass(frozen=True)
class AiClusterSummary:
    title: str
    summary: str
    confidence: int
    candidate_ids: list[str]


class AiProvider(Protocol):
    model: str | None

    def summarize_cluster(self, candidates: list[AiCandidate]) -> AiClusterSummary:
        ...


class OpenAICompatibleAiProvider:
    def __init__(self, settings: Settings) -> None:
        if not settings.ai_api_key or not settings.ai_model:
            raise MissingAiConfigurationError("AI provider is not configured: AI_API_KEY and AI_MODEL are required")
        self.model = settings.ai_model
        self._api_key = settings.ai_api_key
        self._base_url = settings.ai_base_url.rstrip("/")

    def summarize_cluster(self, candidates: list[AiCandidate]) -> AiClusterSummary:
        payload = {
            "model": self.model,
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You merge intelligence items into one event. "
                        "Return compact JSON with title, summary, confidence, candidate_ids."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "candidates": [
                                {
                                    "id": item.id,
                                    "title": item.title,
                                    "content": item.content_text,
                                    "sourceName": item.source_name,
                                    "sourceUrl": item.source_url,
                                }
                                for item in candidates
                            ]
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
        }
        response = httpx.post(
            f"{self._base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self._api_key}"},
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        candidate_ids = [str(candidate_id) for candidate_id in parsed.get("candidate_ids", [])]
        return AiClusterSummary(
            title=str(parsed.get("title") or candidates[0].title),
            summary=str(parsed.get("summary") or candidates[0].content_text or candidates[0].title),
            confidence=_clamp_confidence(parsed.get("confidence", 70)),
            candidate_ids=candidate_ids,
        )


def build_ai_provider(settings: Settings | None = None) -> AiProvider:
    settings = settings or get_settings()
    provider = settings.ai_provider.lower()
    if provider not in {"openai", "openai_compatible"}:
        raise MissingAiConfigurationError("AI provider is not configured: set AI_PROVIDER to openai or openai_compatible")
    return OpenAICompatibleAiProvider(settings)


def _clamp_confidence(value: object) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = 70
    return max(0, min(100, number))
