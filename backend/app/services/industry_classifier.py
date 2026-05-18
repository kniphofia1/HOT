from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.connectors.utils import stable_hash
from app.db.models import AiRunLog, EventCluster, Evidence, RawItem, Source, utc_now
from app.services.ai import AiProvider, MissingAiConfigurationError, build_ai_provider
from app.services.industry_taxonomy import (
    INDUSTRY_LABELS,
    INDUSTRY_CLASSIFICATION_REASON_KEY,
    classification_primary_industry,
    industry_values_from_config,
    normalize_industry_key,
)


@dataclass
class IndustryClassificationRunResult:
    clusters_classified: int = 0
    clusters_skipped: int = 0
    ai_runs_created: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def status(self) -> str:
        if self.errors and self.clusters_classified:
            return "partial"
        if self.errors:
            return "failed"
        return "success"


def classify_event_clusters(
    db: Session,
    *,
    ai_provider: AiProvider | None = None,
    force: bool = False,
    limit: int = 100,
) -> IndustryClassificationRunResult:
    result = IndustryClassificationRunResult()
    clusters = _load_targets(db, force=force, limit=limit)
    if not clusters:
        return result

    provider_error: Exception | None = None
    if ai_provider is None:
        try:
            ai_provider = build_ai_provider()
        except MissingAiConfigurationError as exc:
            provider_error = exc

    for cluster in clusters:
        if _has_classification(cluster) and not force:
            result.clusters_skipped += 1
            continue

        context = _classification_context(db, cluster)
        input_hash = _classification_input_hash(cluster, context)
        token_estimate = _estimate_tokens(cluster, context)
        if provider_error is not None:
            _record_ai_run(
                db,
                input_hash=input_hash,
                model=None,
                status="failed",
                token_estimate=token_estimate,
                error_message=str(provider_error),
            )
            result.ai_runs_created += 1
            result.errors.append(str(provider_error))
            continue

        if ai_provider is None or not hasattr(ai_provider, "classify_event"):
            result.clusters_skipped += 1
            continue

        try:
            classification = ai_provider.classify_event(
                title=cluster.title,
                summary=cluster.summary,
                source_names=context["sourceNames"],
                source_industries=context["sourceIndustries"],
                evidence=context["evidence"],
            )
            primary_industry, related_industries, guard_reason = _normalize_classification(
                classification,
                context=context,
            )
            off_topic = classification.off_topic or bool(guard_reason)
            _apply_classification(
                cluster,
                primary_industry=primary_industry,
                related_industries=related_industries,
                confidence=classification.confidence,
                reason=_merge_reason(classification.reason, guard_reason),
                noise=classification.noise,
                off_topic=off_topic,
            )
            db.add(cluster)
            _record_ai_run(
                db,
                input_hash=input_hash,
                model=ai_provider.model,
                status="success",
                token_estimate=token_estimate,
                error_message=None,
            )
            result.clusters_classified += 1
            result.ai_runs_created += 1
        except Exception as exc:  # noqa: BLE001 - classification is best-effort per event.
            _record_ai_run(
                db,
                input_hash=input_hash,
                model=getattr(ai_provider, "model", None),
                status="failed",
                token_estimate=token_estimate,
                error_message=str(exc),
            )
            result.ai_runs_created += 1
            result.errors.append(str(exc))

    db.commit()
    return result


def classify_event_cluster(
    db: Session,
    cluster: EventCluster,
    *,
    ai_provider: AiProvider | None = None,
    force: bool = False,
) -> IndustryClassificationRunResult:
    if _has_classification(cluster) and not force:
        return IndustryClassificationRunResult(clusters_skipped=1)
    provider = ai_provider
    result = IndustryClassificationRunResult()
    provider_error: Exception | None = None
    if provider is None:
        try:
            provider = build_ai_provider()
        except MissingAiConfigurationError as exc:
            provider_error = exc

    context = _classification_context(db, cluster)
    input_hash = _classification_input_hash(cluster, context)
    token_estimate = _estimate_tokens(cluster, context)
    if provider_error is not None:
        _record_ai_run(
            db,
            input_hash=input_hash,
            model=None,
            status="failed",
            token_estimate=token_estimate,
            error_message=str(provider_error),
        )
        result.ai_runs_created = 1
        result.errors.append(str(provider_error))
        db.commit()
        return result

    if provider is None or not hasattr(provider, "classify_event"):
        return IndustryClassificationRunResult(clusters_skipped=1)

    try:
        classification = provider.classify_event(
            title=cluster.title,
            summary=cluster.summary,
            source_names=context["sourceNames"],
            source_industries=context["sourceIndustries"],
            evidence=context["evidence"],
        )
        primary_industry, related_industries, guard_reason = _normalize_classification(
            classification,
            context=context,
        )
        off_topic = classification.off_topic or bool(guard_reason)
        _apply_classification(
            cluster,
            primary_industry=primary_industry,
            related_industries=related_industries,
            confidence=classification.confidence,
            reason=_merge_reason(classification.reason, guard_reason),
            noise=classification.noise,
            off_topic=off_topic,
        )
        db.add(cluster)
        _record_ai_run(
            db,
            input_hash=input_hash,
            model=provider.model,
            status="success",
            token_estimate=token_estimate,
            error_message=None,
        )
        result.clusters_classified = 1
        result.ai_runs_created = 1
    except Exception as exc:  # noqa: BLE001 - preserve existing classification and log the failure.
        _record_ai_run(
            db,
            input_hash=input_hash,
            model=getattr(provider, "model", None),
            status="failed",
            token_estimate=token_estimate,
            error_message=str(exc),
        )
        result.ai_runs_created = 1
        result.errors.append(str(exc))
    db.commit()
    return result


def _load_targets(db: Session, *, force: bool, limit: int) -> list[EventCluster]:
    clusters = list(db.scalars(select(EventCluster)).all())
    if not force:
        clusters = [cluster for cluster in clusters if not _has_classification(cluster)]
    clusters.sort(key=lambda cluster: (cluster.last_seen_at or cluster.created_at, cluster.hot_score), reverse=True)
    return clusters[:limit]


def _has_classification(cluster: EventCluster) -> bool:
    if cluster.primary_industry or cluster.industry_classified_at:
        return True
    primary_from_reason = classification_primary_industry(cluster.intelligence_reason_json)
    if primary_from_reason:
        return True
    return any(
        isinstance(reason, dict)
        and reason.get("key") == INDUSTRY_CLASSIFICATION_REASON_KEY
        and (reason.get("offTopic") or reason.get("noise"))
        for reason in cluster.intelligence_reason_json or []
    )


def _classification_context(db: Session, cluster: EventCluster) -> dict[str, Any]:
    rows = db.execute(
        select(Source, RawItem, Evidence)
        .join(RawItem, RawItem.source_id == Source.id)
        .join(Evidence, Evidence.raw_item_id == RawItem.id)
        .where(Evidence.event_cluster_id == cluster.id)
    ).all()
    source_names = sorted({source.name for source, _, _ in rows})
    source_industries: list[str] = []
    evidence: list[dict[str, str | None]] = []
    for source, raw_item, evidence_item in rows:
        for industry in industry_values_from_config(source.config_json):
            if industry not in source_industries:
                source_industries.append(industry)
        evidence.append(
            {
                "sourceName": source.name,
                "title": raw_item.title,
                "content": (raw_item.content_text or evidence_item.quote or "")[:800],
                "url": raw_item.source_url or evidence_item.source_url,
            }
        )
    return {
        "sourceNames": source_names,
        "sourceIndustries": source_industries,
        "evidence": evidence,
    }


def _apply_classification(
    cluster: EventCluster,
    *,
    primary_industry: str | None,
    related_industries: list[str],
    confidence: int,
    reason: str,
    noise: bool,
    off_topic: bool,
) -> None:
    if noise or off_topic:
        primary_industry = None
        related_industries = []
    non_industry_domains = [
        domain
        for domain in cluster.impact_domains_json or []
        if not _looks_like_industry_domain(domain)
    ]
    cluster.impact_domains_json = non_industry_domains
    cluster.primary_industry = primary_industry
    cluster.related_industries_json = related_industries
    cluster.industry_confidence = confidence
    cluster.industry_reason = reason
    cluster.industry_classified_at = utc_now().astimezone(timezone.utc)
    existing_reasons = [
        item
        for item in cluster.intelligence_reason_json or []
        if not (isinstance(item, dict) and item.get("key") == INDUSTRY_CLASSIFICATION_REASON_KEY)
    ]
    existing_reasons.append(
        {
            "key": INDUSTRY_CLASSIFICATION_REASON_KEY,
            "label": "行业分类",
            "score": confidence,
            "detail": reason,
            "primaryIndustry": primary_industry,
            "relatedIndustries": related_industries,
            "industries": [industry for industry in [primary_industry, *related_industries] if industry],
            "noise": noise,
            "offTopic": off_topic,
        }
    )
    cluster.intelligence_reason_json = existing_reasons


def _normalize_classification(
    classification: Any,
    *,
    context: dict[str, Any],
) -> tuple[str | None, list[str], str | None]:
    primary = normalize_industry_key(str(getattr(classification, "primary_industry", "") or "")) or None
    related = []
    raw_related = getattr(classification, "related_industries", None)
    if isinstance(raw_related, list):
        related = [key for key in (normalize_industry_key(str(value)) for value in raw_related) if key]
    if primary is None:
        raw_industries = getattr(classification, "industries", [])
        if isinstance(raw_industries, list) and raw_industries:
            primary = normalize_industry_key(str(raw_industries[0])) or None
            related.extend(
                key
                for key in (normalize_industry_key(str(value)) for value in raw_industries[1:])
                if key
            )
    unique_related: list[str] = []
    for key in related:
        if key != primary and key not in unique_related:
            unique_related.append(key)
        if len(unique_related) >= 2:
            break
    guard_reason = _classification_guard(primary, _classification_text(context))
    if guard_reason:
        return None, [], guard_reason
    return primary, unique_related, None


def _looks_like_industry_domain(value: Any) -> bool:
    raw = str(value).strip()
    return raw in INDUSTRY_LABELS or normalize_industry_key(raw) is not None


def _classification_text(context: dict[str, Any]) -> str:
    parts: list[str] = []
    for item in context.get("evidence") or []:
        if isinstance(item, dict):
            parts.extend([str(item.get("title") or ""), str(item.get("content") or "")])
    return " ".join(parts).lower()


def _classification_guard(primary: str | None, text: str) -> str | None:
    automotive_terms = {
        "cars",
        "electric vehicle",
        "suv",
        "sedan",
        "vehicle",
        "vehicles",
        "automotive",
        "robotaxi",
        "tesla fsd",
        "汽车",
        "车型",
        "车企",
        "新能源车",
        "自动驾驶出租车",
    }
    embodied_allowed_terms = {
        "humanoid",
        "robotics",
        "industrial robot",
        "warehouse robot",
        "manipulation",
        "dexterous",
        "optimus",
        "atlas",
        "digit",
        "人形机器人",
        "工业机器人",
        "仓储机器人",
        "灵巧手",
        "具身智能",
    }
    if primary == "products" and _contains_any(text, automotive_terms):
        return "普通汽车或出行新闻不属于产品行业定义，已按跑题处理"
    if primary == "embodied_ai" and _contains_any(text, automotive_terms) and not _contains_any(text, embodied_allowed_terms):
        return "自动驾驶/汽车新闻不等同于具身智能，已按跑题处理"
    return None


def _contains_any(text: str, terms: set[str]) -> bool:
    lowered = text.lower()
    padded = f" {lowered} "
    for term in terms:
        needle = term.lower()
        if needle.isascii() and len(needle) <= 3:
            if f" {needle} " in padded:
                return True
            continue
        if needle in lowered:
            return True
    return False


def _merge_reason(reason: str, guard_reason: str | None) -> str:
    reason = reason.strip()
    if guard_reason and reason:
        return f"{reason}；{guard_reason}"
    return guard_reason or reason


def _classification_input_hash(cluster: EventCluster, context: dict[str, Any]) -> str:
    return stable_hash(
        "event_industry_classification",
        cluster.id,
        cluster.title,
        cluster.summary,
        *context["sourceNames"],
        *context["sourceIndustries"],
    )


def _estimate_tokens(cluster: EventCluster, context: dict[str, Any]) -> int:
    total_chars = len(cluster.title) + len(cluster.summary or "")
    total_chars += sum(len(item.get("title") or "") + len(item.get("content") or "") for item in context["evidence"])
    return max(1, total_chars // 4)


def _record_ai_run(
    db: Session,
    *,
    input_hash: str,
    model: str | None,
    status: str,
    token_estimate: int,
    error_message: str | None,
) -> None:
    db.add(
        AiRunLog(
            task_type="event_industry_classification",
            input_hash=input_hash,
            model=model,
            status=status,
            token_estimate=token_estimate,
            error_message=error_message,
        )
    )
