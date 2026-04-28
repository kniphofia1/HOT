from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class MetricPayload:
    metric_type: str
    value: int


@dataclass(frozen=True)
class RawItemPayload:
    external_id: str | None
    source_url: str | None
    title: str
    content_text: str | None = None
    author: str | None = None
    published_at: datetime | None = None
    raw_payload_json: dict[str, Any] = field(default_factory=dict)
    content_hash: str | None = None
    metrics: list[MetricPayload] = field(default_factory=list)


@dataclass(frozen=True)
class WebpageSnapshotPayload:
    target_id: str
    text_content: str
    content_hash: str
    diff_summary: str | None


@dataclass(frozen=True)
class ConnectorFetchResult:
    items: list[RawItemPayload] = field(default_factory=list)
    snapshots: list[WebpageSnapshotPayload] = field(default_factory=list)


class ConnectorError(RuntimeError):
    pass
