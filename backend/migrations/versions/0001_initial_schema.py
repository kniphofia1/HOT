"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-04-28
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sources",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("type", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("url", sa.Text()),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("weight", sa.Integer(), nullable=False),
        sa.Column("poll_interval_minutes", sa.Integer(), nullable=False),
        sa.Column("config_json", sa.JSON(), nullable=False),
        sa.Column("last_fetched_at", sa.DateTime(timezone=True)),
        sa.Column("last_error", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_sources_type", "sources", ["type"])

    op.create_table(
        "raw_items",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("source_id", sa.String(length=36), sa.ForeignKey("sources.id"), nullable=False),
        sa.Column("external_id", sa.String(length=255)),
        sa.Column("source_url", sa.Text()),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("content_text", sa.Text()),
        sa.Column("author", sa.String(length=255)),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("raw_payload_json", sa.JSON(), nullable=False),
        sa.Column("content_hash", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_raw_items_source_id", "raw_items", ["source_id"])
    op.create_index("ix_raw_items_content_hash", "raw_items", ["content_hash"])

    op.create_table(
        "fetch_runs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("source_id", sa.String(length=36), sa.ForeignKey("sources.id"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("items_found", sa.Integer(), nullable=False),
        sa.Column("items_created", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.Text()),
        sa.Column("rate_limit_remaining", sa.Integer()),
        sa.Column("cost_estimate", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_fetch_runs_source_id", "fetch_runs", ["source_id"])

    op.create_table(
        "web_monitor_targets",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("source_id", sa.String(length=36), sa.ForeignKey("sources.id"), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("css_selector", sa.Text()),
        sa.Column("extraction_mode", sa.String(length=64), nullable=False),
        sa.Column("last_content_hash", sa.String(length=128)),
        sa.Column("last_changed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_web_monitor_targets_source_id", "web_monitor_targets", ["source_id"])

    op.create_table(
        "webpage_snapshots",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("target_id", sa.String(length=36), sa.ForeignKey("web_monitor_targets.id"), nullable=False),
        sa.Column("text_content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=128), nullable=False),
        sa.Column("diff_summary", sa.Text()),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_webpage_snapshots_target_id", "webpage_snapshots", ["target_id"])
    op.create_index("ix_webpage_snapshots_content_hash", "webpage_snapshots", ["content_hash"])

    op.create_table(
        "event_candidates",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("raw_item_id", sa.String(length=36), sa.ForeignKey("raw_items.id"), nullable=False),
        sa.Column("normalized_title", sa.Text(), nullable=False),
        sa.Column("canonical_url", sa.Text()),
        sa.Column("keywords_json", sa.JSON(), nullable=False),
        sa.Column("candidate_hash", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_event_candidates_raw_item_id", "event_candidates", ["raw_item_id"])
    op.create_index("ix_event_candidates_candidate_hash", "event_candidates", ["candidate_hash"])

    op.create_table(
        "event_clusters",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text()),
        sa.Column("hot_score", sa.Integer(), nullable=False),
        sa.Column("score_reason_json", sa.JSON(), nullable=False),
        sa.Column("confidence", sa.Integer(), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True)),
        sa.Column("last_seen_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "evidence",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("event_cluster_id", sa.String(length=36), sa.ForeignKey("event_clusters.id"), nullable=False),
        sa.Column("raw_item_id", sa.String(length=36), sa.ForeignKey("raw_items.id"), nullable=False),
        sa.Column("source_name", sa.String(length=255), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("quote", sa.Text()),
        sa.Column("confidence", sa.Integer(), nullable=False),
    )
    op.create_index("ix_evidence_event_cluster_id", "evidence", ["event_cluster_id"])
    op.create_index("ix_evidence_raw_item_id", "evidence", ["raw_item_id"])

    op.create_table(
        "metric_snapshots",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("raw_item_id", sa.String(length=36), sa.ForeignKey("raw_items.id"), nullable=False),
        sa.Column("metric_type", sa.String(length=64), nullable=False),
        sa.Column("value", sa.Integer(), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_metric_snapshots_raw_item_id", "metric_snapshots", ["raw_item_id"])
    op.create_index("ix_metric_snapshots_metric_type", "metric_snapshots", ["metric_type"])

    op.create_table(
        "ai_run_logs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("task_type", sa.String(length=64), nullable=False),
        sa.Column("input_hash", sa.String(length=128), nullable=False),
        sa.Column("model", sa.String(length=255)),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("token_estimate", sa.Integer()),
        sa.Column("error_message", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_ai_run_logs_task_type", "ai_run_logs", ["task_type"])

    op.create_table(
        "brief_templates",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("mode", sa.String(length=64), nullable=False),
        sa.Column("sections_json", sa.JSON(), nullable=False),
        sa.Column("style_rules", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "brief_exports",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("template_id", sa.String(length=36), sa.ForeignKey("brief_templates.id"), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("event_cluster_ids_json", sa.JSON(), nullable=False),
        sa.Column("manual_notes_json", sa.JSON(), nullable=False),
        sa.Column("markdown", sa.Text(), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_brief_exports_template_id", "brief_exports", ["template_id"])


def downgrade() -> None:
    op.drop_index("ix_brief_exports_template_id", table_name="brief_exports")
    op.drop_table("brief_exports")
    op.drop_table("brief_templates")
    op.drop_index("ix_ai_run_logs_task_type", table_name="ai_run_logs")
    op.drop_table("ai_run_logs")
    op.drop_index("ix_metric_snapshots_metric_type", table_name="metric_snapshots")
    op.drop_index("ix_metric_snapshots_raw_item_id", table_name="metric_snapshots")
    op.drop_table("metric_snapshots")
    op.drop_index("ix_evidence_raw_item_id", table_name="evidence")
    op.drop_index("ix_evidence_event_cluster_id", table_name="evidence")
    op.drop_table("evidence")
    op.drop_table("event_clusters")
    op.drop_index("ix_event_candidates_candidate_hash", table_name="event_candidates")
    op.drop_index("ix_event_candidates_raw_item_id", table_name="event_candidates")
    op.drop_table("event_candidates")
    op.drop_index("ix_webpage_snapshots_content_hash", table_name="webpage_snapshots")
    op.drop_index("ix_webpage_snapshots_target_id", table_name="webpage_snapshots")
    op.drop_table("webpage_snapshots")
    op.drop_index("ix_web_monitor_targets_source_id", table_name="web_monitor_targets")
    op.drop_table("web_monitor_targets")
    op.drop_index("ix_fetch_runs_source_id", table_name="fetch_runs")
    op.drop_table("fetch_runs")
    op.drop_index("ix_raw_items_content_hash", table_name="raw_items")
    op.drop_index("ix_raw_items_source_id", table_name="raw_items")
    op.drop_table("raw_items")
    op.drop_index("ix_sources_type", table_name="sources")
    op.drop_table("sources")
