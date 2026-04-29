from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import BriefExport, BriefTemplate, EventCluster, Evidence


DEFAULT_TEMPLATES = [
    {
        "name": "AI/科技简报",
        "mode": "ai_tech",
        "sections_json": ["重点摘要", "事件详情", "来源引用"],
        "style_rules": "面向 AI/科技研究，强调产品发布、模型能力、开源动态和技术影响。",
    },
    {
        "name": "投资/产业简报",
        "mode": "investment",
        "sections_json": ["核心判断", "产业事件", "风险与观察"],
        "style_rules": "面向投研和产业跟踪，强调商业影响、竞争格局、趋势信号和风险。",
    },
]


def ensure_default_templates(db: Session) -> list[BriefTemplate]:
    for template in DEFAULT_TEMPLATES:
        existing = db.scalar(select(BriefTemplate).where(BriefTemplate.mode == template["mode"]))
        if existing is None:
            db.add(BriefTemplate(**template))
    db.commit()
    return list(db.scalars(select(BriefTemplate).order_by(BriefTemplate.mode.asc())).all())


def preview_markdown(
    db: Session,
    *,
    template_id: str,
    title: str,
    event_cluster_ids: list[str],
    manual_notes: dict[str, str],
) -> str:
    template = _get_template(db, template_id)
    clusters = _load_clusters(db, event_cluster_ids)
    return generate_markdown(template, title, clusters, manual_notes)


def create_brief_export(
    db: Session,
    *,
    template_id: str,
    title: str,
    event_cluster_ids: list[str],
    manual_notes: dict[str, str],
) -> BriefExport:
    markdown = preview_markdown(
        db,
        template_id=template_id,
        title=title,
        event_cluster_ids=event_cluster_ids,
        manual_notes=manual_notes,
    )
    export = BriefExport(
        template_id=template_id,
        title=title,
        event_cluster_ids_json=event_cluster_ids,
        manual_notes_json=manual_notes,
        markdown=markdown,
    )
    db.add(export)
    db.commit()
    db.refresh(export)
    return export


def generate_markdown(
    template: BriefTemplate,
    title: str,
    clusters: list[EventCluster],
    manual_notes: dict[str, str],
) -> str:
    generated_at = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M")
    lines = [
        f"# {_clean_line(title) or '研究员情报简报'}",
        "",
        f"- 生成时间：{generated_at}",
        f"- 模板：{template.name} (`{template.mode}`)",
        f"- 事件数量：{len(clusters)}",
        "",
        "## 重点摘要",
        "",
    ]
    if clusters:
        for index, cluster in enumerate(clusters, start=1):
            lines.append(
                f"{index}. {_cluster_title(cluster)}（热度 {cluster.hot_score}，置信度 {cluster.confidence}）"
            )
    else:
        lines.append("暂无选中的事件。")

    lines.extend(["", "## 事件详情", ""])
    for index, cluster in enumerate(clusters, start=1):
        lines.extend(_event_markdown(index, cluster, manual_notes.get(cluster.id, "")))

    lines.extend(["", "## 附录：模板说明", "", template.style_rules or "无额外样式要求。", ""])
    return "\n".join(lines).strip() + "\n"


def _event_markdown(index: int, cluster: EventCluster, manual_note: str) -> list[str]:
    reasons = cluster.score_reason_json or []
    evidence_items = getattr(cluster, "_brief_evidence", [])
    lines = [
        f"### {index}. {_clean_line(_cluster_title(cluster))}",
        "",
        f"- 热度：{cluster.hot_score}",
        f"- 置信度：{cluster.confidence}",
        f"- 首次发现：{_format_datetime(cluster.first_seen_at)}",
        f"- 最近更新：{_format_datetime(cluster.last_seen_at)}",
        "",
        "**事件摘要**",
        "",
        _cluster_summary(cluster) or "暂无摘要。",
        "",
        "**推荐理由**",
        "",
    ]
    if reasons:
        for reason in reasons:
            label = _clean_line(str(reason.get("label", reason.get("key", "评分项"))))
            score = reason.get("score", 0)
            detail = _clean_line(str(reason.get("detail", "")))
            lines.append(f"- {label}：{score}。{detail}")
    else:
        lines.append("- 暂无评分理由。")

    lines.extend(["", "**人工点评**", "", manual_note.strip() or "暂无人工点评。", "", "**来源引用**", ""])
    if evidence_items:
        for evidence in evidence_items:
            source = _clean_line(evidence.source_name)
            quote = _clean_line(evidence.quote or "暂无引用片段。")
            if _is_http_url(evidence.source_url):
                lines.append(f"- [{source}]({evidence.source_url})：{quote}")
            else:
                lines.append(f"- {source}：{quote}")
    else:
        lines.append("- 暂无可用 Evidence。")

    lines.append("")
    return lines


def _get_template(db: Session, template_id: str) -> BriefTemplate:
    ensure_default_templates(db)
    template = db.get(BriefTemplate, template_id)
    if template is None:
        raise ValueError("BriefTemplate not found")
    return template


def _load_clusters(db: Session, event_cluster_ids: list[str]) -> list[EventCluster]:
    clusters: list[EventCluster] = []
    for cluster_id in event_cluster_ids:
        cluster = db.get(EventCluster, cluster_id)
        if cluster is None:
            continue
        evidence_items = list(
            db.scalars(select(Evidence).where(Evidence.event_cluster_id == cluster.id)).all()
        )
        setattr(cluster, "_brief_evidence", evidence_items)
        clusters.append(cluster)
    return clusters


def _format_datetime(value: datetime | None) -> str:
    if value is None:
        return "未记录"
    return value.astimezone().strftime("%Y-%m-%d %H:%M")


def _clean_line(value: str) -> str:
    return " ".join(value.replace("\r", " ").replace("\n", " ").split())


def _cluster_title(cluster: EventCluster) -> str:
    return cluster.translated_title or cluster.title


def _cluster_summary(cluster: EventCluster) -> str | None:
    return cluster.translated_summary or cluster.summary


def _is_http_url(value: str | None) -> bool:
    if not value:
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
