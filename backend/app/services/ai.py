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


@dataclass(frozen=True)
class AiTranslation:
    title: str
    summary: str


@dataclass(frozen=True)
class AiEditorial:
    title: str
    summary: str
    category: str
    tags: list[str]
    priority: int


class AiProvider(Protocol):
    model: str | None

    def summarize_cluster(self, candidates: list[AiCandidate]) -> AiClusterSummary:
        ...

    def translate_event(self, *, title: str, summary: str | None) -> AiTranslation:
        ...

    def edit_event(
        self,
        *,
        title: str,
        summary: str | None,
        source_names: list[str],
        source_types: list[str],
        source_weight: int,
        evidence_count: int,
    ) -> AiEditorial:
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
                        "Return compact JSON with title, summary, confidence, candidate_ids. "
                        "The title and summary must be written in concise Simplified Chinese. "
                        "Keep product names, model names, company names, repo names, and URLs unchanged."
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
        parsed = _parse_json_object(content)
        candidate_ids = [str(candidate_id) for candidate_id in parsed.get("candidate_ids", [])]
        return AiClusterSummary(
            title=str(parsed.get("title") or candidates[0].title),
            summary=str(parsed.get("summary") or candidates[0].content_text or candidates[0].title),
            confidence=_clamp_confidence(parsed.get("confidence", 70)),
            candidate_ids=candidate_ids,
        )

    def translate_event(self, *, title: str, summary: str | None) -> AiTranslation:
        payload = {
            "model": self.model,
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Translate intelligence event fields into concise Simplified Chinese. "
                        "Keep product names, model names, company names, repo names, and URLs unchanged. "
                        "Do not add facts or analysis. Return compact JSON with title and summary."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "title": title,
                            "summary": summary or "",
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
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        parsed = _parse_json_object(content)
        translated_title = str(parsed.get("title") or title).strip() or title
        translated_summary = str(parsed.get("summary") or summary or title).strip()
        return AiTranslation(title=translated_title, summary=translated_summary)

    def edit_event(
        self,
        *,
        title: str,
        summary: str | None,
        source_names: list[str],
        source_types: list[str],
        source_weight: int,
        evidence_count: int,
    ) -> AiEditorial:
        payload = {
            "model": self.model,
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are an editor for an AI technology intelligence feed. "
                        "Rewrite the event for a lightweight Chinese news card. "
                        "Prioritize major AI/tech news first, then business/investment value, "
                        "then tracked source updates, then technical project updates. "
                        "Do not add facts. Do not provide investment advice. "
                        "Return compact JSON with title, summary, category, tags, priority. "
                        "category must be one of ai_big_news, commercial_value, watchlist_update, "
                        "tech_project, other. summary should only say what happened in 1-2 sentences. "
                        "Keep product names, company names, model names, repo names, and URLs unchanged."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "title": title,
                            "summary": summary or "",
                            "sourceNames": source_names,
                            "sourceTypes": source_types,
                            "sourceWeight": source_weight,
                            "evidenceCount": evidence_count,
                            "priorityGuidance": {
                                "ai_big_news": "80-100",
                                "commercial_value": "70-95",
                                "watchlist_update": "55-85",
                                "tech_project": "35-75",
                                "other": "0-50",
                            },
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
            timeout=45,
        )
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        parsed = _parse_json_object(content)
        editorial_title = str(parsed.get("title") or title).strip() or title
        editorial_summary = str(parsed.get("summary") or summary or title).strip()
        category = _normalize_editorial_category(parsed.get("category"))
        tags = _normalize_tags(parsed.get("tags"), category=category)
        priority = _clamp_priority(parsed.get("priority", 0))
        return AiEditorial(
            title=editorial_title,
            summary=editorial_summary,
            category=category,
            tags=tags,
            priority=priority,
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


def _clamp_priority(value: object) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = 0
    return max(0, min(100, number))


def _normalize_editorial_category(value: object) -> str:
    category = str(value or "").strip()
    allowed = {"ai_big_news", "commercial_value", "watchlist_update", "tech_project", "other"}
    return category if category in allowed else "other"


def _normalize_tags(value: object, *, category: str) -> list[str]:
    if not isinstance(value, list):
        value = []
    tags: list[str] = []
    for item in value:
        tag = str(item).strip()
        if tag and tag not in tags:
            tags.append(tag)
        if len(tags) >= 5:
            break
    if not tags:
        fallback = {
            "ai_big_news": "AI大新闻",
            "commercial_value": "商业价值",
            "watchlist_update": "重点源",
            "tech_project": "技术项目",
            "other": "其他",
        }
        tags.append(fallback[category])
    return tags


def _parse_json_object(content: str) -> dict:
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        cleaned = content.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        parsed = json.loads(cleaned)
    if not isinstance(parsed, dict):
        raise ValueError("AI response must be a JSON object")
    return parsed
