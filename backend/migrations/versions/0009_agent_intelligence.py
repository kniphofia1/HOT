"""agent intelligence

Revision ID: 0009_agent_intelligence
Revises: 0008_saas_control_plane
Create Date: 2026-04-30
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0009_agent_intelligence"
down_revision: Union[str, None] = "0008_saas_control_plane"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "intelligence_agents",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("organization_id", sa.String(length=36), sa.ForeignKey("organizations.id")),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("agent_type", sa.String(length=64), nullable=False),
        sa.Column("scope_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("cadence_minutes", sa.Integer(), nullable=False),
        sa.Column("last_run_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_intelligence_agents_organization_id", "intelligence_agents", ["organization_id"])
    op.create_index("ix_intelligence_agents_agent_type", "intelligence_agents", ["agent_type"])
    op.create_table(
        "agent_alerts",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("agent_id", sa.String(length=36), sa.ForeignKey("intelligence_agents.id"), nullable=False),
        sa.Column("event_cluster_id", sa.String(length=36), sa.ForeignKey("event_clusters.id"), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("follow_up_questions_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_agent_alerts_agent_id", "agent_alerts", ["agent_id"])
    op.create_index("ix_agent_alerts_event_cluster_id", "agent_alerts", ["event_cluster_id"])
    op.create_table(
        "agent_run_logs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("agent_id", sa.String(length=36), sa.ForeignKey("intelligence_agents.id"), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("clusters_scanned", sa.Integer(), nullable=False),
        sa.Column("alerts_created", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_agent_run_logs_agent_id", "agent_run_logs", ["agent_id"])


def downgrade() -> None:
    op.drop_index("ix_agent_run_logs_agent_id", table_name="agent_run_logs")
    op.drop_table("agent_run_logs")
    op.drop_index("ix_agent_alerts_event_cluster_id", table_name="agent_alerts")
    op.drop_index("ix_agent_alerts_agent_id", table_name="agent_alerts")
    op.drop_table("agent_alerts")
    op.drop_index("ix_intelligence_agents_agent_type", table_name="intelligence_agents")
    op.drop_index("ix_intelligence_agents_organization_id", table_name="intelligence_agents")
    op.drop_table("intelligence_agents")
