"""Explainable final score calculation for event clusters.

The stored field is still ``EventCluster.hot_score`` for compatibility, but its
meaning is now the single final score used by both the feed and reports.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import EventCluster, Evidence, RawItem, Source
from app.services.event_intelligence import apply_event_intelligence
from app.services.industry_taxonomy import (
    INDUSTRY_LABELS,
    classification_primary_industry,
    industry_classification_blocks_source_fallback,
    industry_values_from_config,
    industry_values_from_domains,
)


AI_RELEVANCE_HIGH_TERMS = {
    "agent",
    "ai agent",
    " ai ",
    "ai release",
    "ai coding",
    "coding agent",
    "model release",
    "inference",
    "reasoning",
    "multimodal",
    "mcp",
    "tool calling",
    "llm",
    "artificial intelligence",
    "openai",
    "anthropic",
    "claude",
    "gpt",
    "responses api",
    "api",
    "gpu",
    "hbm",
    "ai chip",
    "datacenter",
    "data center",
    "humanoid",
    "embodied",
    "robot",
    "grid",
    "power",
    "storage",
    "semiconductor",
    "chip",
    "memory",
    "solar",
    "photovoltaic",
    "battery",
    "energy",
    "pv",
    "programming language",
    "database",
    "cloud native",
    "kubernetes",
    "rust",
    "python",
    "node.js",
    "security",
    "vulnerability",
    "devtools",
    "developer tool",
    "framework",
    "compiler",
    "operating system",
    "windows",
    "macos",
    "laptop",
    "pc",
    "consumer electronics",
    "smartphone",
    "product launch",
    "hardware launch",
    "agentic",
    "ai应用",
    "ai投入",
    "ai助手",
    "ai工具",
    "ai模型",
    "人工智能",
    "芯片",
    "内存",
    "光伏",
    "电池",
    "能源",
    "机器人",
    "智能体",
    "AI 编程",
    "模型发布",
    "推理",
    "多模态",
    "工具调用",
    "大模型",
    "算力",
    "半导体",
    "数据中心",
    "人形机器人",
    "具身智能",
    "电力",
    "储能",
    "编程语言",
    "数据库",
    "云原生",
    "开源基础设施",
    "网络安全",
    "漏洞",
    "操作系统",
    "开发者工具",
    "框架",
    "电脑",
    "笔记本",
    "手机",
    "消费电子",
    "硬件新品",
    "产品发布",
}

LOW_RELEVANCE_TERMS = {
    "consumer electronics",
    "smartphone",
    "car review",
    "phone",
    "keyboard",
    "headphone",
    "earbuds",
    "camera",
    "lens",
    "telecom",
    "e-commerce",
    "ordinary business news",
    "手机",
    "消费电子",
    "机械键盘",
    "耳机",
    "镜头",
    "相机",
    "运营商",
    "普通商业新闻",
    "相亲",
    "奖金",
    "婚姻",
    "热梗",
    "穿搭",
    "普通商业新闻",
    "消费电子",
    "泛科技",
    "汽车",
}

LOW_RELEVANCE_TERMS -= {
    "consumer electronics",
    "smartphone",
    "phone",
    "手机",
    "消费电子",
}

STRATEGIC_TERMS = {
    "openai",
    "anthropic",
    "xai",
    "google",
    "deepmind",
    "meta",
    "nvidia",
    "microsoft",
    "product line",
    "pricing",
    "api strategy",
    "platform strategy",
    "capex",
    "supply chain",
    "regulation",
    "policy",
    "earnings",
    "filing",
    "acquisition",
    "funding",
    "重大动作",
    "产品线",
    "能力跃迁",
    "定价",
    "平台策略",
    "资本开支",
    "供应链",
    "政策",
    "监管",
    "融资",
}

NOVELTY_TERMS = {
    "launch",
    "launched",
    "release",
    "released",
    "new model",
    "new version",
    "new feature",
    "preview",
    "beta",
    "ga",
    "first",
    "breaking",
    "首次",
    "新版本",
    "新模型",
    "新功能",
    "突发",
    "发布",
    "上线",
}

ACTIONABILITY_TERMS = {
    "try",
    "demo",
    "repo",
    "github",
    "code",
    "sdk",
    "api",
    "workflow",
    "tutorial",
    "guide",
    "benchmark",
    "pricing",
    "download",
    "open source",
    "可以试用",
    "代码",
    "仓库",
    "教程",
    "工作流",
    "开源",
    "定价",
    "部署",
}

TECHNICAL_DENSITY_TERMS = {
    "architecture",
    "parameter",
    "benchmark",
    "api",
    "sdk",
    "latency",
    "throughput",
    "inference",
    "training",
    "deployment",
    "github",
    "arxiv",
    "mlperf",
    "参数",
    "架构",
    "基准",
    "部署",
    "推理",
    "训练",
    "接口",
    "性能",
}

AUDIENCE_FIT_TERMS = {
    "developer",
    "product",
    "engineer",
    "investor",
    "research",
    "industry",
    "startup",
    "开发者",
    "产品经理",
    "工程",
    "投资",
    "行研",
    "研究",
}

NOISE_TERMS = {
    "lol",
    "wow",
    "hot take",
    "thoughts?",
    "what do you think",
    "random thought",
    "相亲",
    "奖金",
    "婚姻",
    "热梗",
    "穿搭",
    "纯转发",
    "转发",
    "无信息量",
    "标题党",
    "怎么看",
    "感觉",
    "achievement",
    "badge",
    "certification",
    "microsoftlearn",
    "alwayslearning",
    "empty page content",
    "login required",
    "register prompt",
    "boilerplate",
    "navigation",
    "privacy policy",
    "cookie policy",
    "subscribe",
    "sign in",
    "log in",
    "no substantive news",
    "空页面",
    "登录",
    "注册",
    "导航",
    "样板内容",
}

GENERIC_PAGE_TERMS = {
    "page overview",
    "page update",
    "home page",
    "homepage information",
    "official website homepage",
    "website update",
    "tracked source",
    "lists investor relations content",
    "skip to main content",
    "saved jobs",
    "board of directors",
    "policies and guidelines",
    "search jobs",
    "only navigation",
    "no substantive",
    "no specific",
    "no specific recent news",
    "no substantive news",
    "首页信息",
    "官网首页",
    "官方网站首页",
    "网站更新",
    "页面内容更新",
    "页面发布",
    "未提及具体",
    "无具体",
    "仅展示",
    "订阅服务",
}

EMOJI_ONLY_PATTERN = re.compile(r"^[\W_]+$", re.UNICODE)
CONCRETE_PATTERN = re.compile(
    r"(\b\d+(?:\.\d+)?\b|\$|%|\bv\d+(?:\.\d+)*\b|\bapi\b|\bsdk\b|\bgithub\b|\barxiv\b|"
    r"\bbenchmark\b|\bmlperf\b|\brelease\b|\blaunch(?:ed)?\b|发布|开源|上线|定价|模型|参数|基准)",
    re.IGNORECASE,
)

FIRST_PARTY_SOURCE_TYPES = {
    "rss",
    "webpage",
    "github_release",
    "sec_edgar_filings",
    "manual_link",
}

SOCIAL_SOURCE_TYPES = {
    "x_recent_search",
    "reddit_subreddit",
    "bluesky_search",
    "bluesky_actor_feed",
    "mastodon_timeline",
    "linkedin_posts",
    "telegram_updates",
    "discord_channel",
    "slack_channel",
}


@dataclass
class ScoreRunResult:
    clusters_scored: int
    cluster_count: int = 0


def calculate_hot_score(
    cluster: EventCluster,
    raw_items: list[RawItem],
    sources_by_id: dict[str, Source],
    *,
    now: datetime | None = None,
) -> tuple[int, list[dict[str, object]]]:
    reference_now = now or datetime.now(UTC)
    text = _event_text(cluster, raw_items)
    source_types = _source_types(raw_items, sources_by_id)
    industries = _cluster_industries(cluster, raw_items, sources_by_id)

    ai_relevance = _ai_relevance_score(cluster, raw_items, sources_by_id, text, industries=industries)
    strategic_importance = _strategic_importance_score(cluster, text)
    novelty = _novelty_score(raw_items, text, reference_now)
    source_authority = _source_authority_score(raw_items, sources_by_id)
    actionability = _actionability_score(text)
    technical_density = _technical_density_score(text)
    discussion_signal = _discussion_signal_score(cluster, raw_items, sources_by_id, reference_now)
    audience_fit = _audience_fit_score(text)
    noise_penalty = _noise_penalty(raw_items, source_types, text)
    duplicate_penalty = _duplicate_penalty(raw_items, sources_by_id, text)
    off_topic_penalty = _off_topic_penalty(ai_relevance, text, industries)

    total = round(
        ai_relevance
        + strategic_importance
        + novelty
        + source_authority
        + actionability
        + technical_density
        + discussion_signal
        + audience_fit
        - noise_penalty
        - duplicate_penalty
        - off_topic_penalty
    )
    final_score = max(0, min(100, total))

    reasons: list[dict[str, object]] = [
        _reason("ai_relevance", "行业相关性", ai_relevance, "AI、半导体、具身智能、新能源、计算机技术和产品发布等主题越明确，分数越高。"),
        _reason("strategic_importance", "战略重要性", strategic_importance, "重点公司动作、模型能力跃迁、定价、API/平台策略、资本开支、政策和供应链事件会加权。"),
        _reason("novelty", "新颖度", novelty, "首次发布、新版本、新模型、新功能和突发事件会加权，新鲜度只作为其中一部分。"),
        _reason("source_authority", "信源权威性", source_authority, "官方 Blog、GitHub Release、官方 X、研究机构、一手技术报告和高权重来源优先。"),
        _reason("actionability", "可行动性", actionability, "能马上试用、有代码、repo、demo、教程、工作流或直接启发产品/工程/投资判断的内容加权。"),
        _reason("technical_density", "技术密度", technical_density, "包含架构、参数、benchmark、API、部署方式或明确技术变化的内容加权。"),
        _reason("discussion_signal", "讨论信号", discussion_signal, "多信源同时讨论、官方消息被高质量账号解读或有连续关联讨论时加权。"),
        _reason("audience_fit", "读者匹配度", audience_fit, "适合 AI 从业者、产品经理、开发者、投资或行研人员的内容加权。"),
    ]
    for key, label, penalty, detail in [
        ("noise_penalty", "噪声扣分", noise_penalty, "纯表情、纯转发、无信息量观点、标题党和低价值闲聊会扣分。"),
        ("duplicate_penalty", "重复扣分", duplicate_penalty, "同一事件低质量二次转载、重复转述或无增量内容会扣分。"),
        ("off_topic_penalty", "跑题扣分", off_topic_penalty, "非 AI/半导体/具身智能/新能源/技术/产品主线的泛资讯或无关内容会扣分。"),
    ]:
        if penalty > 0:
            reasons.append(_reason(key, label, -penalty, detail))

    return final_score, reasons


def recompute_hot_scores(session: Session, *, now: datetime | None = None) -> ScoreRunResult:
    clusters = session.scalars(select(EventCluster)).all()
    scored_count = 0
    now = now or datetime.now(UTC)

    for cluster in clusters:
        evidence_items = session.scalars(
            select(Evidence).where(Evidence.event_cluster_id == cluster.id)
        ).all()
        raw_ids = [e.raw_item_id for e in evidence_items]
        if not raw_ids:
            cluster.hot_score = 0
            cluster.score_reason_json = []
            continue

        raw_items = session.scalars(select(RawItem).where(RawItem.id.in_(raw_ids))).all()
        source_ids = {item.source_id for item in raw_items}
        sources = session.scalars(select(Source).where(Source.id.in_(source_ids))).all()
        sources_by_id = {source.id: source for source in sources}

        apply_event_intelligence(session, cluster, evidence_items, now=now)
        score, reasons = calculate_hot_score(cluster, raw_items, sources_by_id, now=now)
        cluster.hot_score = score
        cluster.score_reason_json = reasons
        scored_count += 1

    session.commit()
    return ScoreRunResult(clusters_scored=scored_count, cluster_count=len(clusters))


def _ai_relevance_score(
    cluster: EventCluster,
    raw_items: list[RawItem],
    sources_by_id: dict[str, Source],
    text: str,
    *,
    industries: list[str] | None = None,
) -> int:
    industries = industries if industries is not None else _cluster_industries(cluster, raw_items, sources_by_id)
    term_score = min(15, _term_hits(text, AI_RELEVANCE_HIGH_TERMS) * 4)
    score = term_score
    if industries and term_score > 0:
        score += 7
    elif industries:
        score += 2
    if "ai" in industries and term_score >= 2:
        score += 3
    if _contains_any(text, LOW_RELEVANCE_TERMS) and "products" not in industries:
        score = min(max(0, score - 10), 7)
    elif _contains_any(text, LOW_RELEVANCE_TERMS):
        score = max(0, score - 10)
    return min(25, score)


def _strategic_importance_score(cluster: EventCluster, text: str) -> int:
    score = min(14, _term_hits(text, STRATEGIC_TERMS) * 3)
    entities = {str(entity).lower() for entity in cluster.entities_json or []}
    if entities.intersection({"openai", "anthropic", "xai", "google", "meta", "nvidia", "microsoft"}):
        score += 4
    if (cluster.credibility_score or 0) >= 70:
        score += 2
    return min(20, score)


def _novelty_score(raw_items: list[RawItem], text: str, now: datetime) -> int:
    score = min(6, _term_hits(text, NOVELTY_TERMS) * 2)
    latest = _latest_seen(raw_items)
    if latest is not None:
        age_hours = max(0.0, (now - _ensure_aware(latest)).total_seconds() / 3600)
        if age_hours <= 6:
            score += 4
        elif age_hours <= 24:
            score += 3
        elif age_hours <= 72:
            score += 1
    return min(10, score)


def _source_authority_score(raw_items: list[RawItem], sources_by_id: dict[str, Source]) -> int:
    sources = _sources(raw_items, sources_by_id)
    if not sources:
        return 0
    score = min(4, sum(max(source.weight or 0, 0) for source in sources))
    groups = {str((source.config_json or {}).get("sourceGroup") or "") for source in sources}
    tiers = {str((source.config_json or {}).get("sourceTier") or (source.config_json or {}).get("priority") or "") for source in sources}
    types = {source.type for source in sources}
    if types.intersection(FIRST_PARTY_SOURCE_TYPES) or groups.intersection({"official_rss", "official_web", "company_official", "github_release", "filings", "research_institute", "benchmark_data"}):
        score += 4
    if "P0" in {tier[:2].upper() for tier in tiers}:
        score += 2
    elif groups.intersection({"expert_x", "industry_media", "technical_media"}):
        score += 1
    return min(10, score)


def _actionability_score(text: str) -> int:
    score = min(10, _term_hits(text, ACTIONABILITY_TERMS) * 3)
    if CONCRETE_PATTERN.search(text):
        score += 5
    return min(15, score)


def _technical_density_score(text: str) -> int:
    score = min(7, _term_hits(text, TECHNICAL_DENSITY_TERMS) * 2)
    if CONCRETE_PATTERN.search(text):
        score += 3
    return min(10, score)


def _discussion_signal_score(
    cluster: EventCluster,
    raw_items: list[RawItem],
    sources_by_id: dict[str, Source],
    now: datetime,
) -> int:
    sources = _sources(raw_items, sources_by_id)
    source_types = {source.type for source in sources}
    recent_count = sum(1 for item in raw_items if _hours_since(item.published_at or item.fetched_at, now) <= 24)
    score = 0
    if len(raw_items) >= 2:
        score += 2
    if len(source_types) >= 2:
        score += 1
    if recent_count >= 2:
        score += 1
    if (cluster.propagation_score or 0) >= 70:
        score += 1
    return min(5, score)


def _audience_fit_score(text: str) -> int:
    score = min(4, _term_hits(text, AUDIENCE_FIT_TERMS))
    if _contains_any(text, AI_RELEVANCE_HIGH_TERMS):
        score += 1
    return min(5, score)


def _noise_penalty(raw_items: list[RawItem], source_types: set[str], text: str) -> int:
    body = " ".join([item.content_text or "" for item in raw_items]).strip()
    if EMOJI_ONLY_PATTERN.match(body or text):
        return 20
    penalty = 0
    if any(term in text for term in {"achievement", "badge", "certification", "microsoftlearn", "alwayslearning"}):
        penalty += 20
    if any(
        term in text
        for term in {
            "empty page content",
            "login required",
            "register prompt",
            "boilerplate",
            "navigation",
            "privacy policy",
            "cookie policy",
            "no substantive news",
            "登录",
            "注册",
            "导航",
            "样板内容",
        }
    ):
        penalty += 25
    if any(term in text for term in {"相亲", "奖金", "婚姻", "热梗", "穿搭"}):
        penalty += 15
    if _contains_any(text, GENERIC_PAGE_TERMS):
        penalty += 20
    if _contains_any(text, NOISE_TERMS) and not CONCRETE_PATTERN.search(text):
        penalty += 15
    if len(body) < 60 and not CONCRETE_PATTERN.search(text):
        penalty += 10
    if len(raw_items) == 1 and source_types.issubset(SOCIAL_SOURCE_TYPES) and not CONCRETE_PATTERN.search(text):
        penalty += 10
    return min(35, penalty)


def _duplicate_penalty(raw_items: list[RawItem], sources_by_id: dict[str, Source], text: str) -> int:
    if len(raw_items) <= 1:
        return 0
    titles = [_normalize_text(item.title) for item in raw_items]
    duplicate_titles = len(titles) - len(set(titles))
    groups = {
        str((source.config_json or {}).get("sourceGroup") or "")
        for source in _sources(raw_items, sources_by_id)
    }
    penalty = min(15, duplicate_titles * 5)
    if groups.issubset({"public_social", "expert_x"}) and not CONCRETE_PATTERN.search(text):
        penalty += 10
    if "repost" in text or "via " in text or "转述" in text:
        penalty += 10
    return min(25, penalty)


def _off_topic_penalty(ai_relevance: int, text: str, industries: list[str]) -> int:
    if ai_relevance >= 8:
        return 0
    if "products" in industries and _contains_any(text, LOW_RELEVANCE_TERMS):
        return 0
    if _contains_any(text, LOW_RELEVANCE_TERMS):
        return 30
    if ai_relevance == 0:
        return 50
    return 15


def _event_text(cluster: EventCluster, raw_items: list[RawItem]) -> str:
    parts: list[str] = [
        cluster.title or "",
        cluster.summary or "",
        cluster.editorial_category or "",
        " ".join(_json_strings(cluster.editorial_tags_json)),
        " ".join(_json_strings(cluster.impact_domains_json)),
        " ".join(_json_strings(cluster.entities_json)),
    ]
    for item in raw_items:
        parts.extend([item.title or "", item.content_text or "", item.source_url or ""])
    return " ".join(part for part in parts if part).lower()


def _cluster_industries(
    cluster: EventCluster,
    raw_items: list[RawItem],
    sources_by_id: dict[str, Source],
) -> list[str]:
    if cluster.primary_industry in INDUSTRY_LABELS:
        return [cluster.primary_industry]
    primary_from_reason = classification_primary_industry(cluster.intelligence_reason_json)
    if primary_from_reason:
        return [primary_from_reason]
    if industry_classification_blocks_source_fallback(cluster.intelligence_reason_json):
        return []
    classified = industry_values_from_domains(cluster.impact_domains_json)
    if classified:
        return classified[:1]

    values: list[str] = []
    for source in _sources(raw_items, sources_by_id):
        values.extend(industry_values_from_config(source.config_json))
    return _dedupe(values)


def _sources(raw_items: list[RawItem], sources_by_id: dict[str, Source]) -> list[Source]:
    unique: list[Source] = []
    seen: set[str] = set()
    for item in raw_items:
        source = sources_by_id.get(item.source_id)
        if source is not None and source.id not in seen:
            unique.append(source)
            seen.add(source.id)
    return unique


def _source_types(raw_items: list[RawItem], sources_by_id: dict[str, Source]) -> set[str]:
    return {
        sources_by_id[item.source_id].type
        for item in raw_items
        if item.source_id in sources_by_id
    }


def _latest_seen(raw_items: list[RawItem]) -> datetime | None:
    return max((_ensure_aware(item.published_at or item.fetched_at) for item in raw_items), default=None)


def _contains_any(text: str, terms: set[str]) -> bool:
    return any(term.lower() in text for term in terms)


def _term_hits(text: str, terms: set[str]) -> int:
    return sum(1 for term in terms if term.lower() in text)


def _json_strings(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(item).lower() for item in value if item]
    if isinstance(value, dict):
        return [str(key).lower() for key in value.keys()]
    return [str(value).lower()]


def _dedupe(values: list[str]) -> list[str]:
    unique: list[str] = []
    for value in values:
        if value and value not in unique:
            unique.append(value)
    return unique


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def _reason(key: str, label: str, score: int, detail: str) -> dict[str, object]:
    return {"key": key, "label": label, "score": score, "detail": detail}


def _ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _hours_since(value: datetime, now: datetime) -> float:
    return max(0.0, (now - _ensure_aware(value)).total_seconds() / 3600)
