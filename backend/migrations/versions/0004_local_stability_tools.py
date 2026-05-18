"""local stability tools

Revision ID: 0004_local_stability_tools
Revises: 0003_event_cluster_editorial
Create Date: 2026-04-30
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0004_local_stability_tools"
down_revision: Union[str, None] = "0003_event_cluster_editorial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "local_credentials",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("key", sa.String(length=128), nullable=False, unique=True),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("provider", sa.String(length=64)),
        sa.Column("environment_key", sa.String(length=128)),
        sa.Column("secret_hint", sa.String(length=64)),
        sa.Column("configured", sa.Boolean(), nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_local_credentials_key", "local_credentials", ["key"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_local_credentials_key", table_name="local_credentials")
    op.drop_table("local_credentials")
