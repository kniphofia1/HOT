"""event cluster editorial cache

Revision ID: 0003_event_cluster_editorial
Revises: 0002_event_cluster_translations
Create Date: 2026-04-29
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0003_event_cluster_editorial"
down_revision: Union[str, None] = "0002_event_cluster_translations"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("event_clusters", sa.Column("editorial_title", sa.Text()))
    op.add_column("event_clusters", sa.Column("editorial_summary", sa.Text()))
    op.add_column("event_clusters", sa.Column("editorial_category", sa.String(length=64)))
    op.add_column(
        "event_clusters",
        sa.Column("editorial_tags_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
    )
    op.add_column(
        "event_clusters",
        sa.Column("editorial_priority", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("event_clusters", sa.Column("editorial_at", sa.DateTime(timezone=True)))


def downgrade() -> None:
    op.drop_column("event_clusters", "editorial_at")
    op.drop_column("event_clusters", "editorial_priority")
    op.drop_column("event_clusters", "editorial_tags_json")
    op.drop_column("event_clusters", "editorial_category")
    op.drop_column("event_clusters", "editorial_summary")
    op.drop_column("event_clusters", "editorial_title")
