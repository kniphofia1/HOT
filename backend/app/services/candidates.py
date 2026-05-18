import re
import unicodedata
from urllib.parse import urlsplit, urlunsplit

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.connectors.utils import stable_hash
from app.db.models import EventCandidate, RawItem, Source
from app.services.industry_taxonomy import industry_values_from_config


STOPWORDS = {
    "a",
    "about",
    "after",
    "and",
    "announce",
    "announced",
    "announces",
    "at",
    "by",
    "for",
    "from",
    "in",
    "into",
    "is",
    "launch",
    "launched",
    "launches",
    "live",
    "model",
    "new",
    "now",
    "of",
    "official",
    "on",
    "release",
    "released",
    "releases",
    "the",
    "to",
    "with",
}


def ensure_event_candidate(db: Session, raw_item: RawItem, source: Source | None = None) -> tuple[EventCandidate, bool]:
    normalized_title = normalize_title(raw_item.title)
    canonical_url = canonicalize_url(raw_item.source_url)
    keywords = extract_keywords(normalized_title)
    industries = _raw_item_industries(db, raw_item, source)
    candidate_hash = make_candidate_hash(normalized_title, canonical_url, keywords, industries)
    existing = db.scalar(select(EventCandidate).where(EventCandidate.raw_item_id == raw_item.id))
    if existing is not None:
        existing.normalized_title = normalized_title
        existing.canonical_url = canonical_url
        existing.keywords_json = keywords
        existing.candidate_hash = candidate_hash
        db.add(existing)
        db.flush()
        return existing, False

    candidate = EventCandidate(
        raw_item_id=raw_item.id,
        normalized_title=normalized_title,
        canonical_url=canonical_url,
        keywords_json=keywords,
        candidate_hash=candidate_hash,
    )
    db.add(candidate)
    db.flush()
    return candidate, True


def ensure_missing_event_candidates(db: Session) -> int:
    raw_items = db.scalars(
        select(RawItem)
        .outerjoin(EventCandidate, EventCandidate.raw_item_id == RawItem.id)
        .where(EventCandidate.id.is_(None))
        .order_by(RawItem.fetched_at.asc())
    ).all()
    created_count = 0
    for raw_item in raw_items:
        _, created = ensure_event_candidate(db, raw_item)
        if created:
            created_count += 1
    return created_count


def normalize_title(title: str) -> str:
    normalized = unicodedata.normalize("NFKC", title).lower()
    normalized = re.sub(r"[^\w\u4e00-\u9fff]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def canonicalize_url(url: str | None) -> str | None:
    if not url:
        return None
    parsed = urlsplit(url.strip())
    if not parsed.scheme or not parsed.netloc:
        return url.strip()
    host = parsed.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    path = parsed.path.rstrip("/") or "/"
    return urlunsplit((parsed.scheme.lower(), host, path, "", ""))


def extract_keywords(normalized_title: str) -> list[str]:
    tokens = re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]{2,}", normalized_title)
    keywords: list[str] = []
    for token in tokens:
        normalized = _normalize_token(token)
        if not normalized or normalized in STOPWORDS:
            continue
        if normalized not in keywords:
            keywords.append(normalized)
        if len(keywords) >= 8:
            break
    return keywords


def make_candidate_hash(
    normalized_title: str,
    canonical_url: str | None,
    keywords: list[str],
    industries: list[str] | None = None,
) -> str:
    industry_part = "+".join(sorted(industries or [])) or "general"
    if len(keywords) >= 2:
        return stable_hash("candidate-keywords", industry_part, *sorted(keywords[:6]))
    if canonical_url:
        return stable_hash("candidate-url", industry_part, canonical_url)
    return stable_hash("candidate-title", industry_part, normalized_title)


def _raw_item_industries(db: Session, raw_item: RawItem, source: Source | None) -> list[str]:
    source = source or db.get(Source, raw_item.source_id)
    if source is None:
        return []
    return industry_values_from_config(source.config_json)


def _normalize_token(token: str) -> str:
    if not token.isascii() or len(token) <= 4:
        return token
    for suffix in ("ingly", "edly", "ing", "ed", "es", "s"):
        if token.endswith(suffix) and len(token) - len(suffix) >= 3:
            return token[: -len(suffix)]
    return token
