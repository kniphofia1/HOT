"""Add explicit primary industry classification fields.

Revision ID: 0012_event_cluster_primary_industry
Revises: 0011_automation_reports
Create Date: 2026-05-17
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0012_event_cluster_primary_industry"
down_revision: Union[str, None] = "0011_automation_reports"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("event_clusters", sa.Column("primary_industry", sa.String(length=64), nullable=True))
    op.add_column(
        "event_clusters",
        sa.Column("related_industries_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
    )
    op.add_column(
        "event_clusters",
        sa.Column("industry_confidence", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("event_clusters", sa.Column("industry_reason", sa.Text(), nullable=True))
    op.add_column("event_clusters", sa.Column("industry_classified_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_event_clusters_primary_industry", "event_clusters", ["primary_industry"])


def downgrade() -> None:
    op.drop_index("ix_event_clusters_primary_industry", table_name="event_clusters")
    op.drop_column("event_clusters", "industry_classified_at")
    op.drop_column("event_clusters", "industry_reason")
    op.drop_column("event_clusters", "industry_confidence")
    op.drop_column("event_clusters", "related_industries_json")
    op.drop_column("event_clusters", "primary_industry")
