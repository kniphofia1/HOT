from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.connectors.utils import stable_hash
from app.db.models import AiRunLog, BriefExport, BriefTemplate, EventCluster, Evidence, RawItem, Source
from app.services.ai import MissingAiConfigurationError, build_ai_provider
from app.services.brief_exporter import ensure_default_templates
from app.services.industry_taxonomy import (
    INDUSTRY_DESCRIPTIONS,
    INDUSTRY_KEYS,
    INDUSTRY_LABELS,
    INDUSTRY_SHORT_LABELS,
    classification_primary_industry,
    industry_classification_blocks_source_fallback,
    industry_values_from_config,
    industry_values_from_domains,
    normalize_industry_key,
)


TIMEZONE = ZoneInfo("Asia/Shanghai")

REPORT_INDUSTRIES = {
    key: {"label": INDUSTRY_LABELS[key], "description": INDUSTRY_DESCRIPTIONS[key]}
    for key in INDUSTRY_KEYS
}

REPORT_TYPE_CONFIG = {
    "daily": {"label": "日报", "top_n": 12},
    "weekly": {"label": "周报", "top_n": 25},
    "competitive_brief": {"label": "竞品简报", "top_n": 15},
    "investment_opportunity": {"label": "投资机会", "top_n": 15},
    "risk_alert": {"label": "风险预警", "top_n": 15},
}

CONTENT_MODULES = {
    "core_conclusions": "核心结论",
    "important_events": "重要事件",
    "company_updates": "公司动态",
    "technology_progress": "技术进展",
    "policy_regulation": "政策监管",
    "risk_signals": "风险信号",
}

OUTPUT_FORMATS = {"markdown"}
REPORT_STYLES = {
    "concise": "简洁版",
    "consulting": "咨询报告版",
    "executive": "老板汇报版",
}


@dataclass(frozen=True)
class ReportGenerationResult:
    export: BriefExport
    markdown: str
    event_cluster_ids: list[str]
    generated_at: datetime
    ai_status: str
    ai_error: str | None


@dataclass(frozen=True)
class ReportRequest:
    industry: str
    time_range: str
    start_date: date | None
    end_date: date | None
    report_type: str
    modules: list[str]
    output_format: str
    style: str


def generate_report_export(db: Session, request: ReportRequest, *, now: datetime | None = None) -> ReportGenerationResult:
    request = _normalize_request(request)
    _validate_request(request)
    current = _ensure_aware(now or datetime.now(timezone.utc))
    start, end = _time_window(request, now=current)
    selected_modules = _normalize_modules(request.modules)
    clusters = _select_clusters(db, industry=request.industry, start=start, end=end)
    if not clusters:
        raise ValueError("No events found for the selected industry and time range")
    top_n = REPORT_TYPE_CONFIG[request.report_type]["top_n"]
    ranked = sorted(clusters, key=lambda cluster: (cluster.hot_score, cluster.last_seen_at or cluster.created_at), reverse=True)[
        :top_n
    ]
    events = [_event_payload(db, cluster) for cluster in ranked]
    title = _report_title(request)
    generated_at = datetime.now(timezone.utc)
    ai_status = "success"
    ai_error: str | None = None

    ai_payload = {
        "title": title,
        "industry": REPORT_INDUSTRIES[request.industry],
        "timeRange": {
            "key": request.time_range,
            "start": start.isoformat(),
            "end": end.isoformat(),
        },
        "reportType": REPORT_TYPE_CONFIG[request.report_type]["label"],
        "modules": [CONTENT_MODULES[module] for module in selected_modules],
        "style": REPORT_STYLES[request.style],
        "selectionPolicy": {
            "75_plus": "必选，头条级",
            "66_to_74": "强候选，结合去重和栏目配额",
            "55_to_65": "普通候选，只选一手源或强实用内容",
            "below_55": "默认不选",
        },
        "fixedTemplate": [
            "一、今日核心结论",
            "二、重要事件概览",
            "三、模型与产品动态",
            "四、公司与商业化动态",
            "五、技术与开源生态",
            "六、政策与风险信号",
            "七、建议继续跟踪",
        ],
        "events": events,
    }
    input_hash = stable_hash("report_generation", ai_payload)
    token_estimate = _estimate_tokens(ai_payload)

    try:
        provider = build_ai_provider()
        markdown = provider.generate_report(ai_payload)
        _record_ai_run(
            db,
            input_hash=input_hash,
            model=provider.model,
            status="success",
            token_estimate=token_estimate,
            error_message=None,
        )
    except MissingAiConfigurationError as exc:
        ai_error = str(exc)
        _record_ai_run(
            db,
            input_hash=input_hash,
            model=None,
            status="failed",
            token_estimate=token_estimate,
            error_message=ai_error,
        )
        db.commit()
        raise ValueError(
            "AI provider is not configured; report generation requires AI_API_KEY and AI_MODEL or AI_HIGH_MODEL"
        ) from exc
    except Exception as exc:  # noqa: BLE001 - provider failures must be visible to the caller.
        ai_error = str(exc)
        _record_ai_run(
            db,
            input_hash=input_hash,
            model=None,
            status="failed",
            token_estimate=token_estimate,
            error_message=ai_error,
        )
        db.commit()
        raise ValueError(f"AI report generation failed: {ai_error}") from exc

    template = _template_for_report(db)
    cluster_ids = [event["id"] for event in events]
    export = BriefExport(
        template_id=template.id,
        title=title,
        brief_type=request.report_type,
        scope_type="industry",
        scope_key=request.industry,
        report_date=end.astimezone(TIMEZONE).date(),
        is_public=False,
        event_cluster_ids_json=cluster_ids,
        manual_notes_json={
            "reportConfig": {
                "industry": request.industry,
                "timeRange": request.time_range,
                "reportType": request.report_type,
                "modules": selected_modules,
                "style": request.style,
            },
            "aiStatus": ai_status,
            "aiError": ai_error,
        },
        export_formats_json=["markdown"],
        delivery_targets_json=[],
        markdown=markdown,
        generated_at=generated_at,
    )
    db.add(export)
    db.commit()
    db.refresh(export)
    return ReportGenerationResult(
        export=export,
        markdown=markdown,
        event_cluster_ids=cluster_ids,
        generated_at=generated_at,
        ai_status=ai_status,
        ai_error=ai_error,
    )


def _normalize_request(request: ReportRequest) -> ReportRequest:
    industry = normalize_industry_key(request.industry) or request.industry
    return ReportRequest(
        industry=industry,
        time_range=request.time_range,
        start_date=request.start_date,
        end_date=request.end_date,
        report_type=request.report_type,
        modules=request.modules,
        output_format=request.output_format,
        style=request.style,
    )


def _validate_request(request: ReportRequest) -> None:
    if request.industry not in REPORT_INDUSTRIES:
        raise ValueError("Unsupported industry")
    if request.time_range not in {"today", "this_week", "custom"}:
        raise ValueError("Unsupported time range")
    if request.report_type not in REPORT_TYPE_CONFIG:
        raise ValueError("Unsupported report type")
    if request.output_format not in OUTPUT_FORMATS:
        raise ValueError("Only Markdown output is supported in this version")
    if request.style not in REPORT_STYLES:
        raise ValueError("Unsupported report style")
    invalid_modules = [module for module in request.modules if module not in CONTENT_MODULES]
    if invalid_modules:
        raise ValueError(f"Unsupported content modules: {', '.join(invalid_modules)}")
    if request.time_range == "custom":
        if request.start_date is None or request.end_date is None:
            raise ValueError("Custom time range requires startDate and endDate")
        if request.start_date > request.end_date:
            raise ValueError("startDate must be earlier than or equal to endDate")


def _normalize_modules(modules: list[str]) -> list[str]:
    if not modules:
        modules = [
            "core_conclusions",
            "important_events",
            "company_updates",
            "technology_progress",
            "risk_signals",
        ]
    unique: list[str] = []
    for module in modules:
        if module in CONTENT_MODULES and module not in unique:
            unique.append(module)
    return unique


def _time_window(request: ReportRequest, *, now: datetime) -> tuple[datetime, datetime]:
    local_now = now.astimezone(TIMEZONE)
    if request.time_range == "today":
        local_start = datetime.combine(local_now.date(), time.min, tzinfo=TIMEZONE)
        return local_start.astimezone(timezone.utc), now
    if request.time_range == "this_week":
        return now - timedelta(hours=168), now

    assert request.start_date is not None
    assert request.end_date is not None
    local_start = datetime.combine(request.start_date, time.min, tzinfo=TIMEZONE)
    local_end = datetime.combine(request.end_date, time.max, tzinfo=TIMEZONE)
    return local_start.astimezone(timezone.utc), local_end.astimezone(timezone.utc)


def _select_clusters(db: Session, *, industry: str, start: datetime, end: datetime) -> list[EventCluster]:
    clusters = [
        cluster
        for cluster in db.scalars(select(EventCluster)).all()
        if _cluster_seen_between(cluster, start, end)
    ]
    return [cluster for cluster in clusters if industry in _cluster_industry_keys(db, cluster)]


def _event_payload(db: Session, cluster: EventCluster) -> dict[str, Any]:
    evidence = list(db.scalars(select(Evidence).where(Evidence.event_cluster_id == cluster.id)).all())
    rows = _source_rows_for_cluster(db, cluster.id)
    source_names = sorted({source.name for source, _, _ in rows}) or sorted({item.source_name for item in evidence})
    source_groups = sorted(
        {
            str(source.config_json.get("sourceGroup"))
            for source, _, _ in rows
            if isinstance(source.config_json, dict) and source.config_json.get("sourceGroup")
        }
    )
    event_type = _event_type(cluster, source_groups)
    return {
        "id": cluster.id,
        "title": _display_title(cluster),
        "summary": _display_summary(cluster),
        "finalScore": cluster.hot_score,
        "importanceScore": cluster.hot_score,
        "confidence": cluster.confidence,
        "eventType": event_type,
        "eventTypeLabel": _event_type_label(event_type),
        "primaryIndustry": cluster.primary_industry,
        "relatedIndustries": cluster.related_industries_json or [],
        "sourceNames": source_names,
        "sourceGroups": source_groups,
        "publishedAt": _format_datetime(cluster.last_seen_at or cluster.first_seen_at or cluster.created_at),
        "scoreReasons": cluster.score_reason_json or [],
        "intelligenceReasons": cluster.intelligence_reason_json or [],
        "impactDomains": cluster.impact_domains_json or [],
        "entities": cluster.entities_json or [],
        "evidence": [
            {
                "sourceName": item.source_name,
                "sourceUrl": item.source_url,
                "quote": item.quote,
                "confidence": item.confidence,
            }
            for item in evidence[:3]
        ],
    }


def _event_type(cluster: EventCluster, source_groups: list[str]) -> str:
    text = " ".join(
        [
            cluster.editorial_category or "",
            cluster.title or "",
            cluster.summary or "",
            cluster.translated_title or "",
            cluster.translated_summary or "",
            " ".join(cluster.editorial_tags_json or []),
            " ".join(cluster.impact_domains_json or []),
            " ".join(cluster.entities_json or []),
            " ".join(source_groups),
        ]
    ).lower()
    if any(term in text for term in ["policy", "regulation", "监管", "政策", "sec", "filing", "edgar"]):
        return "policy_regulation"
    if any(term in text for term in ["risk", "lawsuit", "ban", "delay", "shortage", "风险", "告警", "停产", "短缺"]):
        return "risk_signal"
    if any(term in text for term in ["market data", "price", "sales", "shipment", "trendforce", "infolink", "eia", "市场数据", "价格", "出货", "装机"]):
        return "market_data"
    if any(term in text for term in ["funding", "investment", "ipo", "valuation", "acquisition", "融资", "投资", "上市", "估值", "并购"]):
        return "funding_investment"
    if any(term in text for term in ["benchmark", "mlperf", "eval", "score", "基准", "评测", "跑分"]):
        return "benchmark_metric"
    if any(term in text for term in ["capex", "datacenter", "data center", "hbm", "gpu", "power demand", "capital expenditure", "资本开支", "数据中心", "算力", "hbm"]):
        return "infrastructure_capex"
    if any(term in text for term in ["order", "deployment", "customer", "ship", "交付", "订单", "部署", "客户"]):
        return "deployment_order"
    if any(term in text for term in ["paper", "arxiv", "github", "open source", "benchmark", "mlperf", "论文", "开源", "基准"]):
        return "technology_open_source"
    if any(term in text for term in ["company", "official", "newsroom", "investor", "earnings", "order", "funding", "公司", "融资", "订单"]):
        return "company_business"
    if any(term in text for term in ["model", "product", "launch", "agent", "模型", "产品", "发布"]):
        return "model_product"
    return "company_business"


def _event_type_label(event_type: str) -> str:
    return {
        "model_product": "模型与产品动态",
        "company_business": "公司与商业化动态",
        "technology_open_source": "技术与开源生态",
        "policy_regulation": "政策监管",
        "risk_signal": "风险信号",
        "market_data": "市场与数据",
        "funding_investment": "融资与投资",
        "benchmark_metric": "基准与指标",
        "infrastructure_capex": "基础设施与资本开支",
        "deployment_order": "部署与订单",
    }.get(event_type, "重要事件")


def _source_rows_for_cluster(db: Session, cluster_id: str) -> list[tuple[Source, RawItem, Evidence]]:
    return [
        (source, raw_item, evidence)
        for source, raw_item, evidence in db.execute(
            select(Source, RawItem, Evidence)
            .join(RawItem, RawItem.source_id == Source.id)
            .join(Evidence, Evidence.raw_item_id == RawItem.id)
            .where(Evidence.event_cluster_id == cluster_id)
        ).all()
    ]


def _cluster_industry_keys(db: Session, cluster: EventCluster) -> list[str]:
    primary = _primary_industry_key(cluster)
    if primary:
        return [primary]
    if industry_classification_blocks_source_fallback(cluster.intelligence_reason_json):
        return []

    keys: list[str] = []
    for source, _, _ in _source_rows_for_cluster(db, cluster.id):
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


def _cluster_seen_between(cluster: EventCluster, start: datetime, end: datetime) -> bool:
    value = _ensure_aware(cluster.last_seen_at or cluster.first_seen_at or cluster.created_at)
    return start <= value <= end


def _report_title(request: ReportRequest) -> str:
    industry_label = REPORT_INDUSTRIES[request.industry]["label"]
    report_type_label = REPORT_TYPE_CONFIG[request.report_type]["label"]
    if request.industry in INDUSTRY_SHORT_LABELS:
        return f"{REPORT_INDUSTRIES[request.industry]['label']}行业{report_type_label}"
    return f"{industry_label}行业{report_type_label}"


def _template_for_report(db: Session) -> BriefTemplate:
    templates = ensure_default_templates(db)
    return next((template for template in templates if template.mode == "industry_weekly"), templates[0])


def _display_title(cluster: EventCluster) -> str:
    return cluster.editorial_title or cluster.translated_title or cluster.title


def _display_summary(cluster: EventCluster) -> str:
    return cluster.editorial_summary or cluster.translated_summary or cluster.summary or "暂无摘要。"


def _format_datetime(value: datetime) -> str:
    return _ensure_aware(value).astimezone(TIMEZONE).strftime("%Y-%m-%d %H:%M")


def _ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _estimate_tokens(payload: dict[str, Any]) -> int:
    return max(1, len(str(payload)) // 4)


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
            task_type="report_generation",
            input_hash=input_hash,
            model=model,
            status=status,
            token_estimate=token_estimate,
            error_message=error_message,
        )
    )
