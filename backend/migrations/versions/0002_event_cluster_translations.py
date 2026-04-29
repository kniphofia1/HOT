"""event cluster translation cache

Revision ID: 0002_event_cluster_translations
Revises: 0001_initial_schema
Create Date: 2026-04-28
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002_event_cluster_translations"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("event_clusters", sa.Column("translated_title", sa.Text()))
    op.add_column("event_clusters", sa.Column("translated_summary", sa.Text()))
    op.add_column("event_clusters", sa.Column("translated_at", sa.DateTime(timezone=True)))


def downgrade() -> None:
    op.drop_column("event_clusters", "translated_at")
    op.drop_column("event_clusters", "translated_summary")
    op.drop_column("event_clusters", "translated_title")
