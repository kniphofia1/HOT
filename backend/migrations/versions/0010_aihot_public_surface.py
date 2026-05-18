"""aihot public surface

Revision ID: 0010_aihot_public_surface
Revises: 0009_agent_intelligence
Create Date: 2026-05-08
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0010_aihot_public_surface"
down_revision: Union[str, None] = "0009_agent_intelligence"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "feedback_entries",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("contact", sa.String(length=200)),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_feedback_entries_status", "feedback_entries", ["status"])
    op.create_index("ix_feedback_entries_created_at", "feedback_entries", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_feedback_entries_created_at", table_name="feedback_entries")
    op.drop_index("ix_feedback_entries_status", table_name="feedback_entries")
    op.drop_table("feedback_entries")
