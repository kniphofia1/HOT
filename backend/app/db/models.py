from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text
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
    event_cluster_ids_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    manual_notes_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    markdown: Mapped[str] = mapped_column(Text, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
