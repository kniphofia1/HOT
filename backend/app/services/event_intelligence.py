from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import EventCluster, Evidence, RawItem, Source
from app.services.industry_taxonomy import INDUSTRY_CLASSIFICATION_REASON_KEY, industry_values_from_domains


@dataclass(frozen=True)
class EventIntelligence:
    event_phase: str
    credibility_score: int
    propagation_score: int
    impact_domains_json: list[str]
    entities_json: list[str]
    historical_matches_json: list[dict[str, Any]]
    intelligence_reason_json: list[dict[str, Any]]


DOMAIN_KEYWORDS: dict[str, set[str]] = {
    "ai_tech": {"ai", "artificial intelligence", "llm", "model", "agent", "openai", "anthropic", "qwen", "deepmind", "人工智能", "模型"},
    "developer_platform": {"github", "repository", "release", "api", "sdk", "framework", "developer", "开源", "代码", "开发者"},
    "product_business": {"launch", "pricing", "product", "customer", "revenue", "market", "发布", "产品", "商业", "定价"},
    "capital_market": {"funding", "ipo", "stock", "investor", "valuation", "acquisition", "融资", "上市", "估值", "投资"},
    "policy_risk": {"regulation", "policy", "lawsuit", "ban", "risk", "safety", "compliance", "监管", "政策", "风险", "安全"},
    "social_signal": {"x", "twitter", "reddit", "telegram", "discord", "slack", "youtube", "tiktok", "weibo", "zhihu", "小红书", "抖音"},
    "semiconductor": {
        "gpu",
        "hbm",
        "cowos",
        "semiconductor",
        "datacenter",
        "data center",
        "liquid cooling",
        "capex",
        "nvidia",
        "amd",
        "tsmc",
        "asml",
        "算力",
        "半导体",
        "数据中心",
        "先进封装",
        "液冷",
    },
    "embodied_ai": {
        "robot",
        "robotics",
        "humanoid",
        "embodied",
        "optimus",
        "atlas",
        "digit",
        "unitree",
        "灵巧手",
        "具身智能",
        "机器人",
        "人形机器人",
        "工业机器人",
    },
    "energy": {
        "energy",
        "electricity",
        "power",
        "grid",
        "storage",
        "battery",
        "solar",
        "wind",
        "renewable",
        "megapack",
        "能源",
        "电力",
        "电网",
        "储能",
        "光伏",
        "风电",
        "电池",
    },
}

KNOWN_ENTITIES = [
    "OpenAI",
    "Anthropic",
    "Claude",
    "Google DeepMind",
    "DeepMind",
    "Google",
    "Microsoft",
    "Meta",
    "Apple",
    "Amazon",
    "NVIDIA",
    "AMD",
    "TSMC",
    "ASML",
    "SK hynix",
    "Micron",
    "Samsung Semiconductor",
    "Intel",
    "Broadcom",
    "Marvell",
    "Figure AI",
    "Agility Robotics",
    "Boston Dynamics",
    "Tesla",
    "Unitree",
    "UBTECH",
    "Fourier Intelligence",
    "Apptronik",
    "Sanctuary AI",
    "CATL",
    "Sungrow",
    "LONGi",
    "First Solar",
    "NextEra Energy",
    "Dominion Energy",
    "GitHub",
    "Hugging Face",
    "Qwen",
    "Alibaba",
    "ByteDance",
    "TikTok",
    "YouTube",
    "LinkedIn",
    "Telegram",
    "Discord",
    "Slack",
    "Reddit",
    "Bluesky",
    "Mastodon",
    "微博",
    "B站",
    "知乎",
    "微信公众号",
    "小红书",
    "抖音",
    "快手",
]

ENTITY_STOPWORDS = {
    "AI",
    "API",
    "RSS",
    "HN",
    "The",
    "This",
    "That",
    "New",
    "Show",
    "Release",
    "Research",
    "Update",
}


def calculate_event_intelligence(
    db: Session,
    cluster: EventCluster,
    evidence_items: list[Evidence],
    now: datetime | None = None,
) -> EventIntelligence:
    now = now or datetime.now(timezone.utc)
    raw_items = _raw_items_for_evidence(db, evidence_items)
    sources = _sources_for_raw_items(db, raw_items)
    source_types = {source.type for source in sources.values()}
    first_seen = cluster.first_seen_at or _first_seen(raw_items)
    last_seen = cluster.last_seen_at or _last_seen(raw_items)
    recent_count = _recent_item_count(raw_items, now)
    phase = _event_phase(first_seen, last_seen, recent_count, len(source_types), len(raw_items), now)
    credibility = _credibility_score(evidence_items, sources)
    propagation = _propagation_score(raw_items, source_types, recent_count, first_seen, last_seen, now)
    text = _cluster_text(cluster, raw_items)
    domains = _impact_domains(text)
    entities = _entities(text)
    historical_matches = _historical_matches(db, cluster, domains, entities)
    reasons = _intelligence_reasons(
        phase=phase,
        credibility=credibility,
        propagation=propagation,
        source_count=len(sources),
        source_type_count=len(source_types),
        evidence_count=len(evidence_items),
        recent_count=recent_count,
        domains=domains,
        entities=entities,
        historical_match_count=len(historical_matches),
    )
    return EventIntelligence(
        event_phase=phase,
        credibility_score=credibility,
        propagation_score=propagation,
        impact_domains_json=domains,
        entities_json=entities,
        historical_matches_json=historical_matches,
        intelligence_reason_json=reasons,
    )


def apply_event_intelligence(
    db: Session,
    cluster: EventCluster,
    evidence_items: list[Evidence],
    now: datetime | None = None,
) -> EventCluster:
    classified_industries = industry_values_from_domains(cluster.impact_domains_json)
    classification_reasons = [
        reason
        for reason in cluster.intelligence_reason_json or []
        if isinstance(reason, dict) and reason.get("key") == INDUSTRY_CLASSIFICATION_REASON_KEY
    ]
    intelligence = calculate_event_intelligence(db, cluster, evidence_items, now)
    cluster.event_phase = intelligence.event_phase
    cluster.credibility_score = intelligence.credibility_score
    cluster.propagation_score = intelligence.propagation_score
    cluster.impact_domains_json = _dedupe([*intelligence.impact_domains_json, *classified_industries])
    cluster.entities_json = intelligence.entities_json
    cluster.historical_matches_json = intelligence.historical_matches_json
    cluster.intelligence_reason_json = [*intelligence.intelligence_reason_json, *classification_reasons]
    return cluster


def _raw_items_for_evidence(db: Session, evidence_items: list[Evidence]) -> list[RawItem]:
    raw_items: list[RawItem] = []
    for evidence in evidence_items:
        raw_item = db.get(RawItem, evidence.raw_item_id)
        if raw_item is not None:
            raw_items.append(raw_item)
    return raw_items


def _sources_for_raw_items(db: Session, raw_items: list[RawItem]) -> dict[str, Source]:
    sources: dict[str, Source] = {}
    for raw_item in raw_items:
        source = db.get(Source, raw_item.source_id)
        if source is not None:
            sources[source.id] = source
    return sources


def _event_phase(
    first_seen: datetime | None,
    last_seen: datetime | None,
    recent_count: int,
    source_type_count: int,
    item_count: int,
    now: datetime,
) -> str:
    if last_seen is None:
        return "unknown"
    age = now - _ensure_aware(last_seen)
    if age > timedelta(hours=72):
        return "decaying"
    if item_count >= 3 and recent_count >= 2 and source_type_count >= 2:
        return "peaking"
    if item_count >= 2 or source_type_count >= 2:
        return "spreading"
    if first_seen is not None and now - _ensure_aware(first_seen) <= timedelta(hours=24):
        return "emerging"
    return "tracking"


def _credibility_score(evidence_items: list[Evidence], sources: dict[str, Source]) -> int:
    source_weight_score = min(sum(max(source.weight, 0) for source in sources.values()) * 5, 40)
    source_type_score = min(len({source.type for source in sources.values()}) * 12, 30)
    evidence_score = min(len(evidence_items) * 5, 15)
    confidence_values = [max(0, evidence.confidence) for evidence in evidence_items]
    confidence_score = min(sum(confidence_values) // max(len(confidence_values), 1) // 10, 15)
    return min(source_weight_score + source_type_score + evidence_score + confidence_score, 100)


def _propagation_score(
    raw_items: list[RawItem],
    source_types: set[str],
    recent_count: int,
    first_seen: datetime | None,
    last_seen: datetime | None,
    now: datetime,
) -> int:
    mention_score = min(len(raw_items) * 8, 30)
    recent_score = min(recent_count * 12, 35)
    platform_score = min(len(source_types) * 10, 25)
    span_score = 0
    if first_seen is not None and last_seen is not None and len(raw_items) >= 2:
        span = _ensure_aware(last_seen) - _ensure_aware(first_seen)
        if span <= timedelta(hours=6):
            span_score = 10
        elif span <= timedelta(hours=24):
            span_score = 6
    if last_seen is not None and now - _ensure_aware(last_seen) > timedelta(hours=48):
        recent_score = max(0, recent_score - 12)
    return min(mention_score + recent_score + platform_score + span_score, 100)


def _impact_domains(text: str) -> list[str]:
    normalized = text.lower()
    matched = [
        domain
        for domain, keywords in DOMAIN_KEYWORDS.items()
        if any(keyword.lower() in normalized for keyword in keywords)
    ]
    return matched[:6]


def _dedupe(values: list[str]) -> list[str]:
    unique: list[str] = []
    for value in values:
        if value and value not in unique:
            unique.append(value)
    return unique


def _entities(text: str) -> list[str]:
    found: list[str] = []
    lower_text = text.lower()
    for entity in KNOWN_ENTITIES:
        if entity.lower() in lower_text and entity not in found:
            found.append(entity)
    for match in re.findall(r"\b[A-Z][A-Za-z0-9]+(?:\s+[A-Z][A-Za-z0-9]+){0,2}\b", text):
        cleaned = match.strip()
        if cleaned not in ENTITY_STOPWORDS and cleaned not in found:
            found.append(cleaned)
    return found[:12]


def _historical_matches(
    db: Session,
    cluster: EventCluster,
    domains: list[str],
    entities: list[str],
) -> list[dict[str, Any]]:
    current_tokens = _tokens(cluster.title, cluster.summary or "")
    matches: list[dict[str, Any]] = []
    for other in db.scalars(select(EventCluster).where(EventCluster.id != cluster.id)).all():
        if _ensure_aware(other.created_at) >= _ensure_aware(cluster.created_at):
            continue
        other_domains = set(other.impact_domains_json or [])
        other_entities = set(other.entities_json or [])
        entity_overlap = len(set(entities) & other_entities)
        domain_overlap = len(set(domains) & other_domains)
        token_overlap = _jaccard(current_tokens, _tokens(other.title, other.summary or ""))
        score = min(entity_overlap * 35 + domain_overlap * 15 + int(token_overlap * 40), 100)
        if score < 30:
            continue
        matches.append(
            {
                "clusterId": other.id,
                "title": other.editorial_title or other.translated_title or other.title,
                "score": score,
                "lastSeenAt": _isoformat(other.last_seen_at),
            }
        )
    return sorted(matches, key=lambda item: item["score"], reverse=True)[:3]


def _intelligence_reasons(
    *,
    phase: str,
    credibility: int,
    propagation: int,
    source_count: int,
    source_type_count: int,
    evidence_count: int,
    recent_count: int,
    domains: list[str],
    entities: list[str],
    historical_match_count: int,
) -> list[dict[str, Any]]:
    return [
        {
            "key": "lifecycle",
            "label": "事件生命周期",
            "score": _phase_score(phase),
            "detail": f"当前阶段为 {phase}，过去 24 小时新增 {recent_count} 条证据。",
        },
        {
            "key": "coverage",
            "label": "跨平台覆盖",
            "score": min(source_type_count * 15 + evidence_count * 5, 100),
            "detail": f"覆盖 {source_type_count} 类平台、{source_count} 个信源、{evidence_count} 条证据。",
        },
        {
            "key": "credibility",
            "label": "可信度",
            "score": credibility,
            "detail": f"多源权重、证据数量和 Evidence 置信度合成可信度 {credibility}。",
        },
        {
            "key": "propagation",
            "label": "传播速度",
            "score": propagation,
            "detail": f"传播速度评分 {propagation}，用于判断事件是否正在扩散。",
        },
        {
            "key": "impact",
            "label": "影响范围",
            "score": min(len(domains) * 16 + len(entities) * 4 + historical_match_count * 10, 100),
            "detail": f"识别领域 {', '.join(domains) or 'unknown'}；实体 {', '.join(entities[:5]) or 'unknown'}。",
        },
    ]


def _phase_score(phase: str) -> int:
    return {
        "unknown": 0,
        "decaying": 20,
        "tracking": 35,
        "emerging": 55,
        "spreading": 75,
        "peaking": 90,
    }.get(phase, 0)


def _cluster_text(cluster: EventCluster, raw_items: list[RawItem]) -> str:
    parts = [cluster.title, cluster.summary or ""]
    for raw_item in raw_items:
        parts.append(raw_item.title)
        parts.append(raw_item.content_text or "")
    return "\n".join(parts)


def _first_seen(raw_items: list[RawItem]) -> datetime | None:
    seen_values = [raw_item.published_at or raw_item.fetched_at for raw_item in raw_items]
    return min(seen_values) if seen_values else None


def _last_seen(raw_items: list[RawItem]) -> datetime | None:
    seen_values = [raw_item.published_at or raw_item.fetched_at for raw_item in raw_items]
    return max(seen_values) if seen_values else None


def _recent_item_count(raw_items: list[RawItem], now: datetime) -> int:
    cutoff = now - timedelta(hours=24)
    return sum(1 for raw_item in raw_items if _ensure_aware(raw_item.published_at or raw_item.fetched_at) >= cutoff)


def _tokens(*parts: str) -> set[str]:
    text = " ".join(parts).lower()
    return {token for token in re.findall(r"[a-z0-9\u4e00-\u9fff]{2,}", text) if len(token) > 1}


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def _isoformat(value: datetime | None) -> str | None:
    return _ensure_aware(value).isoformat() if value is not None else None


def _ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value
