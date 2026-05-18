"""event intelligence fields

Revision ID: 0005_event_intelligence
Revises: 0004_local_stability_tools
Create Date: 2026-04-30
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0005_event_intelligence"
down_revision: Union[str, None] = "0004_local_stability_tools"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("event_clusters", sa.Column("event_phase", sa.String(length=32)))
    op.add_column(
        "event_clusters",
        sa.Column("credibility_score", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "event_clusters",
        sa.Column("propagation_score", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "event_clusters",
        sa.Column("impact_domains_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
    )
    op.add_column(
        "event_clusters",
        sa.Column("entities_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
    )
    op.add_column(
        "event_clusters",
        sa.Column("historical_matches_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
    )
    op.add_column(
        "event_clusters",
        sa.Column("intelligence_reason_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
    )


def downgrade() -> None:
    op.drop_column("event_clusters", "intelligence_reason_json")
    op.drop_column("event_clusters", "historical_matches_json")
    op.drop_column("event_clusters", "entities_json")
    op.drop_column("event_clusters", "impact_domains_json")
    op.drop_column("event_clusters", "propagation_score")
    op.drop_column("event_clusters", "credibility_score")
    op.drop_column("event_clusters", "event_phase")
