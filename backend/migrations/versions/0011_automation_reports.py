"""automation reports

Revision ID: 0011_automation_reports
Revises: 0010_aihot_public_surface
Create Date: 2026-05-10
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0011_automation_reports"
down_revision: Union[str, None] = "0010_aihot_public_surface"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("brief_exports", sa.Column("scope_type", sa.String(length=64), nullable=False, server_default="manual"))
    op.add_column("brief_exports", sa.Column("scope_key", sa.String(length=128), nullable=False, server_default="manual"))
    op.add_column("brief_exports", sa.Column("report_date", sa.Date()))
    op.add_column("brief_exports", sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_index("ix_brief_exports_scope_type", "brief_exports", ["scope_type"])
    op.create_index("ix_brief_exports_scope_key", "brief_exports", ["scope_key"])
    op.create_index("ix_brief_exports_report_date", "brief_exports", ["report_date"])
    op.create_index("ix_brief_exports_is_public", "brief_exports", ["is_public"])

    op.create_table(
        "automation_schedules",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("task_type", sa.String(length=64), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("run_time", sa.String(length=16)),
        sa.Column("cadence_minutes", sa.Integer(), nullable=False),
        sa.Column("config_json", sa.JSON(), nullable=False),
        sa.Column("last_run_at", sa.DateTime(timezone=True)),
        sa.Column("next_run_at", sa.DateTime(timezone=True)),
        sa.Column("last_error", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_automation_schedules_task_type", "automation_schedules", ["task_type"], unique=True)
    op.create_index("ix_automation_schedules_next_run_at", "automation_schedules", ["next_run_at"])

    op.create_table(
        "automation_run_logs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("task_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("error_message", sa.Text()),
    )
    op.create_index("ix_automation_run_logs_task_type", "automation_run_logs", ["task_type"])
    op.create_index("ix_automation_run_logs_status", "automation_run_logs", ["status"])
    op.create_index("ix_automation_run_logs_started_at", "automation_run_logs", ["started_at"])


def downgrade() -> None:
    op.drop_index("ix_automation_run_logs_started_at", table_name="automation_run_logs")
    op.drop_index("ix_automation_run_logs_status", table_name="automation_run_logs")
    op.drop_index("ix_automation_run_logs_task_type", table_name="automation_run_logs")
    op.drop_table("automation_run_logs")

    op.drop_index("ix_automation_schedules_next_run_at", table_name="automation_schedules")
    op.drop_index("ix_automation_schedules_task_type", table_name="automation_schedules")
    op.drop_table("automation_schedules")

    op.drop_index("ix_brief_exports_is_public", table_name="brief_exports")
    op.drop_index("ix_brief_exports_report_date", table_name="brief_exports")
    op.drop_index("ix_brief_exports_scope_key", table_name="brief_exports")
    op.drop_index("ix_brief_exports_scope_type", table_name="brief_exports")
    op.drop_column("brief_exports", "is_public")
    op.drop_column("brief_exports", "report_date")
    op.drop_column("brief_exports", "scope_key")
    op.drop_column("brief_exports", "scope_type")
