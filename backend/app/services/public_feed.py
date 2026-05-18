from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from html import unescape
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import BriefExport, EventCluster, Evidence, RawItem, Source
from app.services.industry_taxonomy import (
    INDUSTRY_DESCRIPTIONS,
    INDUSTRY_ENGLISH_LABELS,
    INDUSTRY_LABELS,
    classification_primary_industry,
    classification_related_industries,
    industry_classification_blocks_source_fallback,
    industry_values_from_config,
    industry_values_from_domains,
    labels_for_industries,
    normalize_industry_key,
)


CATEGORY_LABELS = {
    "ai-models": "模型",
    "ai-products": "产品",
    "industry": "行业",
    "paper": "论文",
    "tip": "技巧",
}

SOCIAL_SOURCE_TYPES = {
    "reddit_subreddit",
    "bluesky_search",
    "bluesky_actor_feed",
    "mastodon_timeline",
    "x_recent_search",
    "linkedin_posts",
    "tiktok_research",
    "telegram_updates",
    "discord_channel",
    "slack_channel",
}

NEWS_SOURCE_TYPES = {"rss", "webpage", "hacker_news"}
FIRST_PARTY_SOURCE_TYPES = {"github_repo", "github_release", "youtube_channel", "manual_link", "sec_edgar_filings"}


@dataclass(frozen=True)
class PublicFeedPage:
    items: list[dict[str, Any]]
    total: int
    page: int
    take: int


def list_public_items(
    db: Session,
    *,
    mode: str = "selected",
    category: str | None = None,
    industry: str | None = None,
    source_kind: str | None = None,
    query: str | None = None,
    since: datetime | None = None,
    page: int = 1,
    take: int = 40,
) -> PublicFeedPage:
    clusters = list(db.scalars(select(EventCluster)).all())
    if mode == "selected":
        clusters = [cluster for cluster in clusters if _is_selected(cluster)]

    rows = [build_timeline_item(db, cluster) for cluster in clusters]
    if since is not None:
        cutoff = _ensure_aware(since)
        rows = [item for item in rows if _timeline_datetime(item) is not None and _timeline_datetime(item) >= cutoff]
    if category:
        rows = [item for item in rows if item["category"] == category]
    if industry:
        industry = normalize_industry_key(industry) or industry
        rows = [item for item in rows if industry in item["industries"]]
    if source_kind:
        rows = [item for item in rows if _matches_source_kind(item["sourceTypes"], source_kind)]
    if query:
        needle = query.strip().lower()
        rows = [item for item in rows if _matches_query(item, needle)]

    rows = sorted(rows, key=lambda item: (_timeline_timestamp(item), item["score"]), reverse=True)
    total = len(rows)
    start = (page - 1) * take
    return PublicFeedPage(items=rows[start : start + take], total=total, page=page, take=take)


def build_timeline_item(db: Session, cluster: EventCluster) -> dict[str, Any]:
    evidence_rows = _evidence_rows(db, cluster.id)
    primary = _primary_evidence_row(evidence_rows)
    primary_source, primary_raw_item, primary_evidence = primary if primary is not None else (None, None, None)
    source_names = sorted({source.name for source, _, _ in evidence_rows})
    source_types = sorted({source.type for source, _, _ in evidence_rows})
    industries = _industry_keys_for_rows(evidence_rows, cluster)
    related_industries = _related_industry_keys(cluster)
    raw_items = [raw_item for _, raw_item, _ in evidence_rows]
    category = classify_cluster(cluster)
    reason = _primary_reason(cluster, source_names=source_names, industries=industries)
    tags = _timeline_tags(cluster, category)
    published_at = _aware_or_none(primary_raw_item.published_at if primary_raw_item is not None else None)
    last_seen_at = _aware_or_none(cluster.last_seen_at)
    seen_at = _ensure_aware(cluster.last_seen_at or cluster.first_seen_at or cluster.created_at)
    displayed_at = published_at or seen_at
    source_url = (
        primary_raw_item.source_url
        if primary_raw_item is not None and primary_raw_item.source_url
        else primary_evidence.source_url
        if primary_evidence is not None
        else None
    )
    return {
        "id": cluster.id,
        "displayTitle": cluster.editorial_title or cluster.translated_title or cluster.title,
        "displaySummary": cluster.editorial_summary or cluster.translated_summary or cluster.summary,
        "sourceName": primary_source.name if primary_source is not None else "未记录来源",
        "sourceType": primary_source.type if primary_source is not None else None,
        "sourceNames": source_names,
        "sourceTypes": source_types,
        "industries": industries,
        "industryLabels": labels_for_industries(industries),
        "primaryIndustry": industries[0] if industries else None,
        "primaryIndustryLabel": labels_for_industries(industries[:1])[0] if industries else None,
        "relatedIndustries": related_industries,
        "relatedIndustryLabels": labels_for_industries(related_industries),
        "author": primary_raw_item.author if primary_raw_item is not None else None,
        "publishedAt": published_at,
        "displayedAt": displayed_at,
        "timeBasis": "source_published" if published_at is not None else "system_seen",
        "lastSeenAt": last_seen_at,
        "seenAt": seen_at,
        "score": cluster.hot_score,
        "selected": _is_selected(cluster),
        "category": category,
        "categoryLabel": CATEGORY_LABELS.get(category, "行业"),
        "tags": tags,
        "reason": reason,
        "url": source_url,
        "avatarUrl": _first_avatar_url(raw_items),
        "mediaUrls": _media_urls(raw_items),
        "evidenceCount": len(evidence_rows),
        "confidence": cluster.confidence,
    }


def list_daily_archives(db: Session, *, take: int = 30) -> list[dict[str, Any]]:
    exports = _public_exports(db, scope_type="global", scope_key="all")
    daily_exports = exports or [export for export in list(db.scalars(select(BriefExport).order_by(BriefExport.generated_at.desc())).all()) if _is_daily_export(export)]
    if daily_exports:
        return [
            {
                "date": (export.report_date or _ensure_aware(export.generated_at).date()).isoformat(),
                "title": export.title,
                "storyCount": len(export.event_cluster_ids_json or []),
                "generatedAt": export.generated_at,
            }
            for export in daily_exports[:take]
        ]

    clusters = list(db.scalars(select(EventCluster).order_by(EventCluster.last_seen_at.desc())).all())
    seen_dates: list[date] = []
    for cluster in clusters:
        value = cluster.last_seen_at or cluster.first_seen_at or cluster.created_at
        day = _ensure_aware(value).date()
        if day not in seen_dates:
            seen_dates.append(day)
        if len(seen_dates) >= take:
            break
    return [
        {
            "date": day.isoformat(),
            "title": f"{day.isoformat()} AI HOT 日报",
            "storyCount": _cluster_count_for_day(clusters, day),
            "generatedAt": datetime.combine(day, datetime.min.time(), tzinfo=timezone.utc),
        }
        for day in seen_dates
    ]


def get_daily_digest(db: Session, *, target_date: date | None = None) -> dict[str, Any]:
    archive = list_daily_archives(db, take=1 if target_date is None else 60)
    if target_date is None and archive:
        target_date = date.fromisoformat(archive[0]["date"])
    if target_date is None:
        target_date = datetime.now(timezone.utc).date()

    export = _daily_export_for_date(db, target_date)
    if export is not None:
        items = [
            build_timeline_item(db, cluster)
            for cluster in db.scalars(
                select(EventCluster).where(EventCluster.id.in_(export.event_cluster_ids_json or []))
            ).all()
        ]
        return {
            "date": target_date.isoformat(),
            "title": export.title,
            "generatedAt": export.generated_at,
            "storyCount": len(items),
            "sections": _daily_sections(items),
            "markdown": export.markdown,
            "archive": list_daily_archives(db, take=30),
        }

    start = datetime.combine(target_date, datetime.min.time(), tzinfo=timezone.utc)
    end = start + timedelta(days=1)
    clusters = [
        cluster
        for cluster in db.scalars(select(EventCluster)).all()
        if _cluster_seen_between(cluster, start, end)
    ]
    clusters = sorted(clusters, key=lambda cluster: cluster.hot_score, reverse=True)[:30]
    items = [build_timeline_item(db, cluster) for cluster in clusters]
    return {
        "date": target_date.isoformat(),
        "title": f"AI HOT 日报",
        "generatedAt": start,
        "storyCount": len(items),
        "sections": _daily_sections(items),
        "markdown": "",
        "archive": list_daily_archives(db, take=30),
    }


def classify_cluster(cluster: EventCluster) -> str:
    haystack = " ".join(
        [
            cluster.editorial_category or "",
            cluster.title or "",
            cluster.summary or "",
            " ".join(cluster.editorial_tags_json or []),
            " ".join(cluster.impact_domains_json or []),
            " ".join(cluster.entities_json or []),
        ]
    ).lower()
    if any(term in haystack for term in ["paper", "arxiv", "论文", "research paper"]):
        return "paper"
    if any(term in haystack for term in ["tutorial", "guide", "技巧", "教程", "实践", "coding", "developer_platform"]):
        return "tip"
    if any(term in haystack for term in ["product", "产品", "commercial_value", "product_business"]):
        return "ai-products"
    if any(term in haystack for term in ["model", "模型", "openai", "anthropic", "qwen", "deepseek", "ai_tech"]):
        return "ai-models"
    return "industry"


def list_industry_reports(db: Session, *, take: int = 10) -> list[dict[str, Any]]:
    reports: list[dict[str, Any]] = []
    for domain, label in INDUSTRY_LABELS.items():
        exports = _public_exports(db, scope_type="industry", scope_key=domain)
        latest = exports[0] if exports else None
        story_count = len(latest.event_cluster_ids_json or []) if latest else _cluster_count_for_industry(db, domain)
        reports.append(
            {
                "domain": domain,
                "label": label,
                "englishLabel": INDUSTRY_ENGLISH_LABELS[domain],
                "description": INDUSTRY_DESCRIPTIONS[domain],
                "title": latest.title if latest else f"{label}日报",
                "storyCount": story_count,
                "latestDate": (latest.report_date.isoformat() if latest and latest.report_date else None),
                "generatedAt": latest.generated_at if latest else None,
                "archive": [
                    {
                        "date": (export.report_date or _ensure_aware(export.generated_at).date()).isoformat(),
                        "title": export.title,
                        "storyCount": len(export.event_cluster_ids_json or []),
                        "generatedAt": export.generated_at,
                    }
                    for export in exports[:take]
                ],
            }
        )
    return reports


def get_industry_digest(
    db: Session,
    *,
    domain: str,
    target_date: date | None = None,
) -> dict[str, Any]:
    domain = normalize_industry_key(domain) or domain
    if domain not in INDUSTRY_LABELS:
        domain = next(iter(INDUSTRY_LABELS))
    exports = _public_exports(db, scope_type="industry", scope_key=domain)
    if target_date is None and exports:
        target_date = exports[0].report_date or _ensure_aware(exports[0].generated_at).date()
    if target_date is None:
        target_date = datetime.now(timezone.utc).date()

    export = _public_export_for_date(db, scope_type="industry", scope_key=domain, target_date=target_date)
    if export is not None:
        items = _items_for_export(db, export)
        return {
            "domain": domain,
            "label": INDUSTRY_LABELS[domain],
            "englishLabel": INDUSTRY_ENGLISH_LABELS[domain],
            "description": INDUSTRY_DESCRIPTIONS[domain],
            "date": target_date.isoformat(),
            "title": export.title,
            "generatedAt": export.generated_at,
            "storyCount": len(items),
            "sections": _daily_sections(items),
            "markdown": export.markdown,
            "archive": _archive_for_exports(exports),
        }

    start = datetime.combine(target_date, datetime.min.time(), tzinfo=timezone.utc)
    end = start + timedelta(days=1)
    clusters = [
        cluster
        for cluster in db.scalars(select(EventCluster)).all()
        if _cluster_matches_industry(db, cluster, domain) and _cluster_seen_between(cluster, start, end)
    ]
    clusters = sorted(clusters, key=lambda cluster: cluster.hot_score, reverse=True)[:12]
    items = [build_timeline_item(db, cluster) for cluster in clusters]
    return {
        "domain": domain,
        "label": INDUSTRY_LABELS[domain],
        "englishLabel": INDUSTRY_ENGLISH_LABELS[domain],
        "description": INDUSTRY_DESCRIPTIONS[domain],
        "date": target_date.isoformat(),
        "title": f"{INDUSTRY_LABELS[domain]}日报",
        "generatedAt": start,
        "storyCount": len(items),
        "sections": _daily_sections(items),
        "markdown": "",
        "archive": _archive_for_exports(exports),
    }


def _daily_sections(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sections = []
    for index, key in enumerate(["ai-models", "ai-products", "industry", "paper", "tip"], start=1):
        section_items = sorted(
            [item for item in items if item["category"] == key],
            key=lambda item: (_timeline_timestamp(item), item["score"]),
            reverse=True,
        )
        if not section_items:
            continue
        sections.append(
            {
                "key": key,
                "index": f"{index:02d}",
                "label": CATEGORY_LABELS[key],
                "englishLabel": {
                    "ai-models": "MODEL RELEASES",
                    "ai-products": "PRODUCT UPDATES",
                    "industry": "INDUSTRY SIGNALS",
                    "paper": "PAPERS",
                    "tip": "TIPS",
                }[key],
                "items": section_items,
            }
        )
    return sections


def _items_for_export(db: Session, export: BriefExport) -> list[dict[str, Any]]:
    return [
        build_timeline_item(db, cluster)
        for cluster in db.scalars(
            select(EventCluster).where(EventCluster.id.in_(export.event_cluster_ids_json or []))
        ).all()
    ]


def _evidence_rows(db: Session, cluster_id: str) -> list[tuple[Source, RawItem, Evidence]]:
    return [
        (source, raw_item, evidence)
        for source, raw_item, evidence in db.execute(
            select(Source, RawItem, Evidence)
            .join(RawItem, RawItem.source_id == Source.id)
            .join(Evidence, Evidence.raw_item_id == RawItem.id)
            .where(Evidence.event_cluster_id == cluster_id)
        ).all()
    ]


def _primary_evidence_row(
    rows: list[tuple[Source, RawItem, Evidence]],
) -> tuple[Source, RawItem, Evidence] | None:
    if not rows:
        return None

    def sort_key(row: tuple[Source, RawItem, Evidence]) -> tuple[int, float, str]:
        source, raw_item, _ = row
        seen_at = raw_item.published_at or raw_item.fetched_at
        timestamp = _ensure_aware(seen_at).timestamp() if seen_at is not None else 0.0
        return (-(source.weight or 0), -timestamp, source.name)

    return sorted(rows, key=sort_key)[0]


def _timeline_datetime(item: dict[str, Any]) -> datetime | None:
    value = item.get("publishedAt") or item.get("displayedAt") or item.get("seenAt")
    return _aware_or_none(value) if value is not None else None


def _timeline_timestamp(item: dict[str, Any]) -> float:
    value = _timeline_datetime(item)
    return value.timestamp() if value is not None else 0.0


def _is_selected(cluster: EventCluster) -> bool:
    reasons = {
        str(reason.get("key")): int(reason.get("score") or 0)
        for reason in cluster.score_reason_json or []
        if isinstance(reason, dict)
    }
    noise_penalty = abs(reasons.get("noise_penalty", 0))
    off_topic_penalty = abs(reasons.get("off_topic_penalty", 0))
    duplicate_penalty = abs(reasons.get("duplicate_penalty", 0))
    has_quality_penalty = noise_penalty >= 15 or off_topic_penalty >= 15 or duplicate_penalty >= 20

    if cluster.hot_score >= 75:
        return off_topic_penalty < 30
    if cluster.hot_score >= 66:
        return not has_quality_penalty
    if cluster.hot_score >= 55:
        return not has_quality_penalty and (
            reasons.get("source_authority", 0) >= 8 or reasons.get("actionability", 0) >= 10
        )
    return False


def _matches_query(item: dict[str, Any], needle: str) -> bool:
    if not needle:
        return True
    haystack = " ".join(
        [
            item.get("displayTitle") or "",
            item.get("displaySummary") or "",
            item.get("sourceName") or "",
            " ".join(item.get("tags") or []),
            " ".join(item.get("industryLabels") or []),
        ]
    ).lower()
    return needle in haystack


def _matches_source_kind(source_types: list[str], source_kind: str) -> bool:
    if source_kind == "social":
        return any(source_type in SOCIAL_SOURCE_TYPES for source_type in source_types)
    if source_kind == "news":
        return any(source_type in NEWS_SOURCE_TYPES for source_type in source_types)
    if source_kind == "first_party":
        return any(source_type in FIRST_PARTY_SOURCE_TYPES for source_type in source_types)
    return True


def _timeline_tags(cluster: EventCluster, category: str) -> list[str]:
    tags = [
        *(cluster.editorial_tags_json or []),
        *(cluster.entities_json or []),
    ]
    unique: list[str] = []
    for tag in tags:
        value = str(tag).strip()
        if value and value not in unique:
            unique.append(value)
    return unique[:5]


def _primary_reason(cluster: EventCluster, *, source_names: list[str], industries: list[str]) -> str:
    if cluster.industry_reason and _is_usable_chinese_text(cluster.industry_reason):
        return cluster.industry_reason
    reasons = [*cluster.intelligence_reason_json, *cluster.score_reason_json]
    reasons = [reason for reason in reasons if isinstance(reason, dict)]
    reasons.sort(key=lambda reason: int(reason.get("score") or 0), reverse=True)
    for reason in reasons:
        detail = str(reason.get("detail") or "").strip()
        if detail and _is_usable_chinese_text(detail) and not _is_internal_taxonomy_detail(detail):
            return detail
    source_label = "、".join(source_names[:2]) or "可信信源"
    industry_label = "、".join(labels_for_industries(industries)[:2])
    if industry_label:
        return f"来自 {source_label} 的 {industry_label} 动态，按来源权重、热度和证据完整度进入当前情报流。"
    return "基于来源权重、热度和 Evidence 可信度进入当前情报流。"


def _is_usable_chinese_text(value: str) -> bool:
    if value.count("?") >= 3:
        return False
    return any("\u4e00" <= char <= "\u9fff" for char in value)


def _is_internal_taxonomy_detail(value: str) -> bool:
    lowered = value.lower()
    return "识别领域" in value or any(token in lowered for token in ["ai_tech", "social_signal", "product_business", "policy_risk"])


def _media_urls(raw_items: list[RawItem]) -> list[str]:
    urls: list[str] = []
    for raw_item in raw_items:
        for url in _collect_urls(raw_item.raw_payload_json, avatar=False):
            if url not in urls:
                urls.append(url)
            if len(urls) >= 4:
                return urls
    return urls


def _first_avatar_url(raw_items: list[RawItem]) -> str | None:
    for raw_item in raw_items:
        for url in _collect_urls(raw_item.raw_payload_json, avatar=True):
            return url
    return None


def _collect_urls(value: Any, *, avatar: bool) -> list[str]:
    urls: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            key_lower = str(key).lower()
            if isinstance(child, str):
                url = unescape(child)
                if avatar and key_lower in {"avatar", "avatarurl", "profileimageurl", "profile_image_url"} and _is_image_url(url):
                    urls.append(url)
                if not avatar and key_lower in {"mediaurl", "media_url", "thumbnailurl", "thumbnail_url", "fullsize"} and _is_image_url(url):
                    urls.append(url)
                if not avatar and key_lower in {"url", "src"} and _is_image_url(url):
                    urls.append(url)
            urls.extend(_collect_urls(child, avatar=avatar))
    elif isinstance(value, list):
        for child in value:
            urls.extend(_collect_urls(child, avatar=avatar))
    return _dedupe(urls)


def _is_image_url(value: str) -> bool:
    lowered = value.lower()
    return lowered.startswith("http") and (
        any(ext in lowered for ext in [".jpg", ".jpeg", ".png", ".webp", ".gif"])
        or "pbs.twimg.com/media/" in lowered
        or "twimg.com/profile_images/" in lowered
    )


def _dedupe(values: list[str]) -> list[str]:
    unique: list[str] = []
    for value in values:
        if value not in unique:
            unique.append(value)
    return unique


def _is_daily_export(export: BriefExport) -> bool:
    if export.scope_type == "global" and export.scope_key == "all" and export.is_public:
        return True
    value = f"{export.title} {export.brief_type or ''}".lower()
    return "日报" in value or "daily" in value


def _daily_export_for_date(db: Session, target_date: date) -> BriefExport | None:
    export = _public_export_for_date(db, scope_type="global", scope_key="all", target_date=target_date)
    if export is not None:
        return export
    exports = list(db.scalars(select(BriefExport).order_by(BriefExport.generated_at.desc())).all())
    for export in exports:
        export_date = export.report_date or _ensure_aware(export.generated_at).date()
        if _is_daily_export(export) and export_date == target_date:
            return export
    return None


def _public_exports(db: Session, *, scope_type: str, scope_key: str) -> list[BriefExport]:
    return list(
        db.scalars(
            select(BriefExport)
            .where(BriefExport.is_public.is_(True))
            .where(BriefExport.scope_type == scope_type)
            .where(BriefExport.scope_key == scope_key)
            .order_by(BriefExport.report_date.desc(), BriefExport.generated_at.desc())
        ).all()
    )


def _public_export_for_date(
    db: Session,
    *,
    scope_type: str,
    scope_key: str,
    target_date: date,
) -> BriefExport | None:
    return db.scalar(
        select(BriefExport)
        .where(BriefExport.is_public.is_(True))
        .where(BriefExport.scope_type == scope_type)
        .where(BriefExport.scope_key == scope_key)
        .where(BriefExport.report_date == target_date)
        .order_by(BriefExport.generated_at.desc())
    )


def _archive_for_exports(exports: list[BriefExport]) -> list[dict[str, Any]]:
    return [
        {
            "date": (export.report_date or _ensure_aware(export.generated_at).date()).isoformat(),
            "title": export.title,
            "storyCount": len(export.event_cluster_ids_json or []),
            "generatedAt": export.generated_at,
        }
        for export in exports[:30]
    ]


def _industry_keys_for_rows(rows: list[tuple[Source, RawItem, Evidence]], cluster: EventCluster) -> list[str]:
    primary = _primary_industry_key(cluster)
    if primary:
        return [primary]
    if industry_classification_blocks_source_fallback(cluster.intelligence_reason_json):
        return []

    keys: list[str] = []
    for source, _, _ in rows:
        for key in industry_values_from_config(source.config_json):
            if key not in keys:
                keys.append(key)
    return keys


def _primary_industry_key(cluster: EventCluster) -> str | None:
    if cluster.primary_industry in INDUSTRY_LABELS:
        return cluster.primary_industry
    primary_from_reason = classification_primary_industry(cluster.intelligence_reason_json)
    if primary_from_reason:
        return primary_from_reason
    if industry_classification_blocks_source_fallback(cluster.intelligence_reason_json):
        return None
    classified_keys = industry_values_from_domains(cluster.impact_domains_json)
    return classified_keys[0] if classified_keys else None


def _related_industry_keys(cluster: EventCluster) -> list[str]:
    primary = _primary_industry_key(cluster)
    values = cluster.related_industries_json or classification_related_industries(cluster.intelligence_reason_json)
    keys: list[str] = []
    for key in values:
        if key in INDUSTRY_LABELS and key != primary and key not in keys:
            keys.append(key)
    return keys


def _cluster_industry_keys(db: Session, cluster: EventCluster) -> list[str]:
    return _industry_keys_for_rows(_evidence_rows(db, cluster.id), cluster)


def _cluster_matches_industry(db: Session, cluster: EventCluster, industry: str) -> bool:
    return industry in _cluster_industry_keys(db, cluster)


def _cluster_count_for_industry(db: Session, industry: str) -> int:
    return sum(1 for cluster in db.scalars(select(EventCluster)).all() if _cluster_matches_industry(db, cluster, industry))


def _cluster_count_for_day(clusters: list[EventCluster], day: date) -> int:
    return sum(1 for cluster in clusters if _ensure_aware(cluster.last_seen_at or cluster.created_at).date() == day)


def _cluster_seen_between(cluster: EventCluster, start: datetime, end: datetime) -> bool:
    value = _ensure_aware(cluster.last_seen_at or cluster.first_seen_at or cluster.created_at)
    return start <= value < end


def _ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _aware_or_none(value: datetime | None) -> datetime | None:
    return _ensure_aware(value) if value is not None else None
