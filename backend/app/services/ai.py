from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Literal, Protocol

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


@dataclass(frozen=True)
class AiClassification:
    industries: list[str]
    confidence: int
    reason: str
    noise: bool
    off_topic: bool
    primary_industry: str | None = None
    related_industries: list[str] | None = None


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

    def classify_event(
        self,
        *,
        title: str,
        summary: str | None,
        source_names: list[str],
        source_industries: list[str],
        evidence: list[dict[str, str | None]],
    ) -> AiClassification:
        ...

    def generate_report(self, payload: dict) -> str:
        ...


class OpenAICompatibleAiProvider:
    def __init__(self, settings: Settings) -> None:
        default_model = _default_model(settings)
        if not settings.ai_api_key or not default_model:
            raise MissingAiConfigurationError(
                "AI provider is not configured: AI_API_KEY and AI_MODEL or AI_FAST_MODEL/AI_HIGH_MODEL are required"
            )
        self.model = default_model
        self._fast_model = _fast_model(settings)
        self._high_model = _high_model(settings)
        self._api_key = settings.ai_api_key
        self._base_url = settings.ai_base_url.rstrip("/")

    def summarize_cluster(self, candidates: list[AiCandidate]) -> AiClusterSummary:
        payload = {
            "model": self._select_model("fast"),
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
        data = self._post_chat(payload, timeout=30, thinking=False)
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
            "model": self._select_model("high"),
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
        data = self._post_chat(payload, timeout=60, thinking=False)
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
            "model": self._select_model("high"),
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
        data = self._post_chat(payload, timeout=45, thinking=False)
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

    def classify_event(
        self,
        *,
        title: str,
        summary: str | None,
        source_names: list[str],
        source_industries: list[str],
        evidence: list[dict[str, str | None]],
    ) -> AiClassification:
        payload = {
            "model": self._select_model("fast"),
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Classify one intelligence event into exactly one primary industry. "
                        "Allowed industry keys: ai, semiconductor, embodied_ai, energy, technology, products. "
                        "Use source industries only as weak hints; classify by actual event content. "
                        "Return primary_industry as one allowed key or null, and related_industries as at most two secondary keys. "
                        "If the event is generic, noisy, or unrelated, return an empty industries list "
                        "and set off_topic or noise to true. Return compact JSON with primary_industry, related_industries, industries, "
                        "confidence, reason, noise, off_topic. The reason must be concise Simplified Chinese."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "title": title,
                            "summary": summary or "",
                            "sourceNames": source_names,
                            "sourceIndustryHints": source_industries,
                            "evidence": evidence[:5],
                            "industryDefinitions": {
                                "ai": "AI 产业情报：模型发布、Agent、AI 编程、多模态、推理能力、MCP / 工具调用、AI 公司、AI 开发者生态。只把 AI 作为事件主体时归入此类。",
                                "semiconductor": "GPU、AI 芯片、HBM、先进封装、数据中心、液冷、云厂商资本开支与电力约束。",
                                "embodied_ai": "人形机器人、工业机器人、仓储物流机器人、机器人基础模型、灵巧手与量产交付。",
                                "energy": "数据中心用电、电网扩容、储能订单、绿电直连、可再生能源、核电、光伏、风电与电池。",
                                "technology": "新发布或重要更新的计算机技术：编程语言、数据库、云原生、开源基础设施、网络安全、操作系统、开发者工具、框架、协议、平台工程。",
                                "products": "新发布或重要更新的产品：AI 应用、SaaS、电脑、手机、消费电子、硬件新品、应用发布、平台功能更新。产品是事件主体时归入此类。",
                            },
                            "classificationRules": [
                                "Pick exactly one primary_industry unless the event is off-topic or pure noise.",
                                "Do not classify by source alone. A product launch from an AI company can be products if the product itself is the main news.",
                                "Do not put AI infrastructure hardware into ai when the main subject is GPU, HBM, datacenter, capex, cooling, or chips; use semiconductor.",
                                "Do not put robotics into ai when the main subject is robots or embodied systems; use embodied_ai.",
                                "Do not put generic cloud, database, security, language, framework, or open-source infrastructure updates into ai; use technology.",
                                "Do not classify ordinary car, EV, robotaxi, real estate, lifestyle, entertainment, or generic business news as products unless the main subject is an AI/computer/electronics/software product.",
                            ],
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
        }
        data = self._post_chat(payload, timeout=45, thinking=False)
        content = data["choices"][0]["message"]["content"]
        parsed = _parse_json_object(content)
        primary_industry = _normalize_industry(parsed.get("primary_industry"))
        fallback_industries = _normalize_industries(parsed.get("industries"), limit=3)
        if primary_industry is None and fallback_industries:
            primary_industry = fallback_industries[0]
        related_industries = _normalize_industries(parsed.get("related_industries"), limit=2)
        related_industries = [industry for industry in related_industries if industry != primary_industry]
        industries = [industry for industry in [primary_industry, *related_industries] if industry]
        confidence = _clamp_confidence(parsed.get("confidence", 60))
        reason = str(parsed.get("reason") or "").strip()
        noise = _coerce_bool(parsed.get("noise"))
        off_topic = _coerce_bool(parsed.get("off_topic"))
        if not primary_industry and not (noise or off_topic):
            off_topic = True
        return AiClassification(
            industries=industries,
            confidence=confidence,
            reason=reason[:160] or "模型未给出明确分类理由。",
            noise=noise,
            off_topic=off_topic,
            primary_industry=primary_industry,
            related_industries=related_industries,
        )

    def generate_report(self, payload: dict) -> str:
        response_payload = {
            "model": self._select_model("high"),
            "temperature": 0.2,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You generate a Chinese industry intelligence report in Markdown. "
                        "Use only the supplied events and evidence. Do not add unverifiable facts. "
                        "Keep product names, company names, model names, repo names, handles, and URLs unchanged. "
                        "Return Markdown only, with the requested fixed section structure."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(payload, ensure_ascii=False),
                },
            ],
        }
        data = self._post_chat(response_payload, timeout=90, thinking=True)
        markdown = str(data["choices"][0]["message"]["content"]).strip()
        if not markdown:
            raise ValueError("AI report response is empty")
        return markdown

    def _select_model(self, tier: Literal["fast", "high"]) -> str:
        selected = self._fast_model if tier == "fast" else self._high_model
        self.model = selected
        return selected

    def _post_chat(self, payload: dict[str, Any], *, timeout: int, thinking: bool) -> dict[str, Any]:
        model = str(payload.get("model") or self.model or "")
        if _supports_deepseek_thinking(self._base_url, model):
            payload = {
                **payload,
                "thinking": {"type": "enabled", "reasoning_effort": "high"} if thinking else {"type": "disabled"},
            }
        response = httpx.post(
            f"{self._base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self._api_key}"},
            json=payload,
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json()


def build_ai_provider(settings: Settings | None = None) -> AiProvider:
    settings = settings or get_settings()
    provider = settings.ai_provider.lower()
    if provider not in {"openai", "openai_compatible"}:
        raise MissingAiConfigurationError("AI provider is not configured: set AI_PROVIDER to openai or openai_compatible")
    return OpenAICompatibleAiProvider(settings)


def _default_model(settings: Settings) -> str:
    return settings.ai_model or settings.ai_fast_model or settings.ai_high_model


def _fast_model(settings: Settings) -> str:
    return settings.ai_fast_model or settings.ai_model or settings.ai_high_model


def _high_model(settings: Settings) -> str:
    if settings.ai_high_model:
        return settings.ai_high_model
    if "api.deepseek.com" in settings.ai_base_url and (settings.ai_model or settings.ai_fast_model):
        return "deepseek-v4-pro"
    return settings.ai_model or settings.ai_fast_model


def _supports_deepseek_thinking(base_url: str, model: str) -> bool:
    return "api.deepseek.com" in base_url and model.startswith("deepseek-v4-")


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


def _coerce_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "y"}
    return bool(value)


def _normalize_industry(value: object) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    allowed = {"ai", "semiconductor", "embodied_ai", "energy", "technology", "products"}
    return normalized if normalized in allowed else None


def _normalize_industries(value: object, *, limit: int = 2) -> list[str]:
    allowed = {"ai", "semiconductor", "embodied_ai", "energy", "technology", "products"}
    if isinstance(value, str):
        values = [value]
    elif isinstance(value, list):
        values = value
    else:
        values = []
    industries: list[str] = []
    for item in values:
        industry = str(item).strip()
        if industry in allowed and industry not in industries:
            industries.append(industry)
        if len(industries) >= limit:
            break
    return industries


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
