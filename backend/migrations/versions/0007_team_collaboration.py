"""team collaboration

Revision ID: 0007_team_collaboration
Revises: 0006_brief_delivery_center
Create Date: 2026-04-30
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0007_team_collaboration"
down_revision: Union[str, None] = "0006_brief_delivery_center"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "team_users",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255)),
        sa.Column("role", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_team_users_email", "team_users", ["email"])
    op.create_table(
        "team_spaces",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "team_memberships",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("space_id", sa.String(length=36), sa.ForeignKey("team_spaces.id"), nullable=False),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("team_users.id"), nullable=False),
        sa.Column("role", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_team_memberships_space_id", "team_memberships", ["space_id"])
    op.create_index("ix_team_memberships_user_id", "team_memberships", ["user_id"])
    op.create_table(
        "source_space_links",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("space_id", sa.String(length=36), sa.ForeignKey("team_spaces.id"), nullable=False),
        sa.Column("source_id", sa.String(length=36), sa.ForeignKey("sources.id"), nullable=False),
        sa.Column("created_by_user_id", sa.String(length=36), sa.ForeignKey("team_users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_source_space_links_space_id", "source_space_links", ["space_id"])
    op.create_index("ix_source_space_links_source_id", "source_space_links", ["source_id"])
    op.create_table(
        "event_bookmarks",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("space_id", sa.String(length=36), sa.ForeignKey("team_spaces.id"), nullable=False),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("team_users.id"), nullable=False),
        sa.Column("event_cluster_id", sa.String(length=36), sa.ForeignKey("event_clusters.id"), nullable=False),
        sa.Column("note", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_event_bookmarks_space_id", "event_bookmarks", ["space_id"])
    op.create_index("ix_event_bookmarks_event_cluster_id", "event_bookmarks", ["event_cluster_id"])
    op.create_table(
        "event_annotations",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("space_id", sa.String(length=36), sa.ForeignKey("team_spaces.id"), nullable=False),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("team_users.id"), nullable=False),
        sa.Column("event_cluster_id", sa.String(length=36), sa.ForeignKey("event_clusters.id"), nullable=False),
        sa.Column("label", sa.String(length=128), nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_event_annotations_space_id", "event_annotations", ["space_id"])
    op.create_index("ix_event_annotations_event_cluster_id", "event_annotations", ["event_cluster_id"])
    op.create_table(
        "brief_reviews",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("space_id", sa.String(length=36), sa.ForeignKey("team_spaces.id"), nullable=False),
        sa.Column("brief_export_id", sa.String(length=36), sa.ForeignKey("brief_exports.id"), nullable=False),
        sa.Column("requested_by_user_id", sa.String(length=36), sa.ForeignKey("team_users.id"), nullable=False),
        sa.Column("reviewer_user_id", sa.String(length=36), sa.ForeignKey("team_users.id")),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_brief_reviews_space_id", "brief_reviews", ["space_id"])
    op.create_index("ix_brief_reviews_brief_export_id", "brief_reviews", ["brief_export_id"])
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("actor_user_id", sa.String(length=36), sa.ForeignKey("team_users.id")),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.String(length=36), nullable=False),
        sa.Column("detail_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_logs_actor_user_id", "audit_logs", ["actor_user_id"])
    op.create_index("ix_audit_logs_entity_type", "audit_logs", ["entity_type"])


def downgrade() -> None:
    op.drop_index("ix_audit_logs_entity_type", table_name="audit_logs")
    op.drop_index("ix_audit_logs_actor_user_id", table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_index("ix_brief_reviews_brief_export_id", table_name="brief_reviews")
    op.drop_index("ix_brief_reviews_space_id", table_name="brief_reviews")
    op.drop_table("brief_reviews")
    op.drop_index("ix_event_annotations_event_cluster_id", table_name="event_annotations")
    op.drop_index("ix_event_annotations_space_id", table_name="event_annotations")
    op.drop_table("event_annotations")
    op.drop_index("ix_event_bookmarks_event_cluster_id", table_name="event_bookmarks")
    op.drop_index("ix_event_bookmarks_space_id", table_name="event_bookmarks")
    op.drop_table("event_bookmarks")
    op.drop_index("ix_source_space_links_source_id", table_name="source_space_links")
    op.drop_index("ix_source_space_links_space_id", table_name="source_space_links")
    op.drop_table("source_space_links")
    op.drop_index("ix_team_memberships_user_id", table_name="team_memberships")
    op.drop_index("ix_team_memberships_space_id", table_name="team_memberships")
    op.drop_table("team_memberships")
    op.drop_table("team_spaces")
    op.drop_index("ix_team_users_email", table_name="team_users")
    op.drop_table("team_users")
