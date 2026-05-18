from datetime import date, datetime, timezone
from uuid import uuid4

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return str(uuid4())


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )


class Source(Base, TimestampMixin):
    __tablename__ = "sources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str | None] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    weight: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    poll_interval_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    config_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    last_fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)

    raw_items: Mapped[list["RawItem"]] = relationship(back_populates="source")
    fetch_runs: Mapped[list["FetchRun"]] = relationship(back_populates="source")


class RawItem(Base, TimestampMixin):
    __tablename__ = "raw_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"), nullable=False, index=True)
    external_id: Mapped[str | None] = mapped_column(String(255))
    source_url: Mapped[str | None] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    content_text: Mapped[str | None] = mapped_column(Text)
    author: Mapped[str | None] = mapped_column(String(255))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    raw_payload_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)

    source: Mapped[Source] = relationship(back_populates="raw_items")


class FetchRun(Base, TimestampMixin):
    __tablename__ = "fetch_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"), nullable=False, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    items_found: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    items_created: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text)
    rate_limit_remaining: Mapped[int | None] = mapped_column(Integer)
    cost_estimate: Mapped[int | None] = mapped_column(Integer)

    source: Mapped[Source] = relationship(back_populates="fetch_runs")


class WebMonitorTarget(Base, TimestampMixin):
    __tablename__ = "web_monitor_targets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"), nullable=False, index=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    css_selector: Mapped[str | None] = mapped_column(Text)
    extraction_mode: Mapped[str] = mapped_column(String(64), nullable=False, default="css_selector")
    last_content_hash: Mapped[str | None] = mapped_column(String(128))
    last_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class WebpageSnapshot(Base):
    __tablename__ = "webpage_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    target_id: Mapped[str] = mapped_column(ForeignKey("web_monitor_targets.id"), nullable=False, index=True)
    text_content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    diff_summary: Mapped[str | None] = mapped_column(Text)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class EventCandidate(Base):
    __tablename__ = "event_candidates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    raw_item_id: Mapped[str] = mapped_column(ForeignKey("raw_items.id"), nullable=False, index=True)
    normalized_title: Mapped[str] = mapped_column(Text, nullable=False)
    canonical_url: Mapped[str | None] = mapped_column(Text)
    keywords_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    candidate_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class EventCluster(Base, TimestampMixin):
    __tablename__ = "event_clusters"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    translated_title: Mapped[str | None] = mapped_column(Text)
    translated_summary: Mapped[str | None] = mapped_column(Text)
    translated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    editorial_title: Mapped[str | None] = mapped_column(Text)
    editorial_summary: Mapped[str | None] = mapped_column(Text)
    editorial_category: Mapped[str | None] = mapped_column(String(64))
    editorial_tags_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    editorial_priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    editorial_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    hot_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    score_reason_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    confidence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    first_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    event_phase: Mapped[str | None] = mapped_column(String(32))
    credibility_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    propagation_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    primary_industry: Mapped[str | None] = mapped_column(String(64), index=True)
    related_industries_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    industry_confidence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    industry_reason: Mapped[str | None] = mapped_column(Text)
    industry_classified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    impact_domains_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    entities_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    historical_matches_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    intelligence_reason_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)


class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    event_cluster_id: Mapped[str] = mapped_column(ForeignKey("event_clusters.id"), nullable=False, index=True)
    raw_item_id: Mapped[str] = mapped_column(ForeignKey("raw_items.id"), nullable=False, index=True)
    source_name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    quote: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class MetricSnapshot(Base):
    __tablename__ = "metric_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    raw_item_id: Mapped[str] = mapped_column(ForeignKey("raw_items.id"), nullable=False, index=True)
    metric_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    value: Mapped[int] = mapped_column(Integer, nullable=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class AiRunLog(Base):
    __tablename__ = "ai_run_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    task_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    input_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    model: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    token_estimate: Mapped[int | None] = mapped_column(Integer)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class BriefTemplate(Base, TimestampMixin):
    __tablename__ = "brief_templates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    mode: Mapped[str] = mapped_column(String(64), nullable=False)
    sections_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    style_rules: Mapped[str | None] = mapped_column(Text)


class BriefExport(Base):
    __tablename__ = "brief_exports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    template_id: Mapped[str] = mapped_column(ForeignKey("brief_templates.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    brief_type: Mapped[str | None] = mapped_column(String(64), default="intelligence_brief")
    scope_type: Mapped[str] = mapped_column(String(64), nullable=False, default="manual", index=True)
    scope_key: Mapped[str] = mapped_column(String(128), nullable=False, default="manual", index=True)
    report_date: Mapped[date | None] = mapped_column(Date, index=True)
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    event_cluster_ids_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    manual_notes_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    export_formats_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    delivery_targets_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    markdown: Mapped[str] = mapped_column(Text, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class BriefDelivery(Base):
    __tablename__ = "brief_deliveries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    export_id: Mapped[str] = mapped_column(ForeignKey("brief_exports.id"), nullable=False, index=True)
    target_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    target_label: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    payload_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class AutomationSchedule(Base, TimestampMixin):
    __tablename__ = "automation_schedules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    task_type: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="Asia/Shanghai")
    run_time: Mapped[str | None] = mapped_column(String(16))
    cadence_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    config_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    last_error: Mapped[str | None] = mapped_column(Text)


class AutomationRunLog(Base):
    __tablename__ = "automation_run_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    task_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    payload_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    error_message: Mapped[str | None] = mapped_column(Text)


class FeedbackEntry(Base):
    __tablename__ = "feedback_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    contact: Mapped[str | None] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="new", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)


class TeamUser(Base, TimestampMixin):
    __tablename__ = "team_users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), index=True)
    role: Mapped[str] = mapped_column(String(64), nullable=False, default="analyst")


class TeamSpace(Base, TimestampMixin):
    __tablename__ = "team_spaces"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)


class TeamMembership(Base):
    __tablename__ = "team_memberships"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    space_id: Mapped[str] = mapped_column(ForeignKey("team_spaces.id"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("team_users.id"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(64), nullable=False, default="member")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class SourceSpaceLink(Base):
    __tablename__ = "source_space_links"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    space_id: Mapped[str] = mapped_column(ForeignKey("team_spaces.id"), nullable=False, index=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"), nullable=False, index=True)
    created_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("team_users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class EventBookmark(Base):
    __tablename__ = "event_bookmarks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    space_id: Mapped[str] = mapped_column(ForeignKey("team_spaces.id"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("team_users.id"), nullable=False)
    event_cluster_id: Mapped[str] = mapped_column(ForeignKey("event_clusters.id"), nullable=False, index=True)
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class EventAnnotation(Base, TimestampMixin):
    __tablename__ = "event_annotations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    space_id: Mapped[str] = mapped_column(ForeignKey("team_spaces.id"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("team_users.id"), nullable=False)
    event_cluster_id: Mapped[str] = mapped_column(ForeignKey("event_clusters.id"), nullable=False, index=True)
    label: Mapped[str] = mapped_column(String(128), nullable=False)
    note: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open")


class BriefReview(Base, TimestampMixin):
    __tablename__ = "brief_reviews"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    space_id: Mapped[str] = mapped_column(ForeignKey("team_spaces.id"), nullable=False, index=True)
    brief_export_id: Mapped[str] = mapped_column(ForeignKey("brief_exports.id"), nullable=False, index=True)
    requested_by_user_id: Mapped[str] = mapped_column(ForeignKey("team_users.id"), nullable=False)
    reviewer_user_id: Mapped[str | None] = mapped_column(ForeignKey("team_users.id"))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    notes: Mapped[str | None] = mapped_column(Text)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    actor_user_id: Mapped[str | None] = mapped_column(ForeignKey("team_users.id"), index=True)
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False)
    detail_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class Organization(Base, TimestampMixin):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")


class OrganizationMembership(Base):
    __tablename__ = "organization_memberships"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("team_users.id"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(64), nullable=False)
    permissions_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class SubscriptionPlan(Base, TimestampMixin):
    __tablename__ = "subscription_plans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    price_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    quota_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class OrganizationSubscription(Base, TimestampMixin):
    __tablename__ = "organization_subscriptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    plan_id: Mapped[str] = mapped_column(ForeignKey("subscription_plans.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    current_period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class QuotaUsage(Base, TimestampMixin):
    __tablename__ = "quota_usage"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    metric: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    limit: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class TaskQueueEntry(Base, TimestampMixin):
    __tablename__ = "task_queue_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str | None] = mapped_column(ForeignKey("organizations.id"), index=True)
    task_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued", index=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    payload_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    last_error: Mapped[str | None] = mapped_column(Text)


class MonitoringAlertRule(Base, TimestampMixin):
    __tablename__ = "monitoring_alert_rules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    metric: Mapped[str] = mapped_column(String(64), nullable=False)
    threshold: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")


class TenantDataScope(Base):
    __tablename__ = "tenant_data_scopes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False)
    access_level: Mapped[str] = mapped_column(String(32), nullable=False, default="owned")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class SaasAuditLog(Base):
    __tablename__ = "saas_audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str | None] = mapped_column(ForeignKey("organizations.id"), index=True)
    actor_user_id: Mapped[str | None] = mapped_column(ForeignKey("team_users.id"))
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False)
    detail_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class IntelligenceAgent(Base, TimestampMixin):
    __tablename__ = "intelligence_agents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str | None] = mapped_column(ForeignKey("organizations.id"), index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    agent_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    scope_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    cadence_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AgentAlert(Base, TimestampMixin):
    __tablename__ = "agent_alerts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    agent_id: Mapped[str] = mapped_column(ForeignKey("intelligence_agents.id"), nullable=False, index=True)
    event_cluster_id: Mapped[str] = mapped_column(ForeignKey("event_clusters.id"), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    follow_up_questions_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open")


class AgentRunLog(Base):
    __tablename__ = "agent_run_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    agent_id: Mapped[str] = mapped_column(ForeignKey("intelligence_agents.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    clusters_scanned: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    alerts_created: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class LocalCredential(Base, TimestampMixin):
    __tablename__ = "local_credentials"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    key: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    provider: Mapped[str | None] = mapped_column(String(64))
    environment_key: Mapped[str | None] = mapped_column(String(128))
    secret_hint: Mapped[str | None] = mapped_column(String(64))
    configured: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notes: Mapped[str | None] = mapped_column(Text)
