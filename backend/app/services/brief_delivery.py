from __future__ import annotations

from app.db.models import BriefDelivery, BriefExport


EXTERNAL_TARGETS = {"email", "feishu", "notion", "slack"}
READY_TARGETS = {"local_archive", "site_public"}


def create_delivery(export: BriefExport, *, target_type: str, target_label: str) -> BriefDelivery:
    normalized_type = target_type.strip().lower()
    status = "ready" if normalized_type in READY_TARGETS else "requires_configuration"
    if normalized_type in EXTERNAL_TARGETS:
        status = "requires_configuration"
    return BriefDelivery(
        export_id=export.id,
        target_type=normalized_type or "local_archive",
        target_label=target_label.strip() or _default_label(normalized_type),
        status=status,
        payload_json={
            "title": export.title,
            "briefType": export.brief_type,
            "formats": export.export_formats_json,
            "eventClusterIds": export.event_cluster_ids_json,
            "markdownChars": len(export.markdown),
        },
        error_message=None if status == "ready" else "External delivery requires configured credentials and sender.",
    )


def _default_label(target_type: str) -> str:
    return {
        "email": "Email draft",
        "feishu": "Feishu delivery",
        "notion": "Notion delivery",
        "slack": "Slack delivery",
        "local_archive": "Local archive",
        "site_public": "AIHOT site",
    }.get(target_type, "Delivery target")
