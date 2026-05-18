"""brief delivery center

Revision ID: 0006_brief_delivery_center
Revises: 0005_event_intelligence
Create Date: 2026-04-30
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0006_brief_delivery_center"
down_revision: Union[str, None] = "0005_event_intelligence"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("brief_exports", sa.Column("brief_type", sa.String(length=64), server_default="intelligence_brief"))
    op.add_column(
        "brief_exports",
        sa.Column("export_formats_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
    )
    op.add_column(
        "brief_exports",
        sa.Column("delivery_targets_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
    )
    op.create_table(
        "brief_deliveries",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("export_id", sa.String(length=36), sa.ForeignKey("brief_exports.id"), nullable=False),
        sa.Column("target_type", sa.String(length=64), nullable=False),
        sa.Column("target_label", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("error_message", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_brief_deliveries_export_id", "brief_deliveries", ["export_id"])
    op.create_index("ix_brief_deliveries_target_type", "brief_deliveries", ["target_type"])


def downgrade() -> None:
    op.drop_index("ix_brief_deliveries_target_type", table_name="brief_deliveries")
    op.drop_index("ix_brief_deliveries_export_id", table_name="brief_deliveries")
    op.drop_table("brief_deliveries")
    op.drop_column("brief_exports", "delivery_targets_json")
    op.drop_column("brief_exports", "export_formats_json")
    op.drop_column("brief_exports", "brief_type")
