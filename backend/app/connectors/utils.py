from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from hashlib import sha256
from typing import Any
from urllib.parse import urlparse


def stable_hash(*parts: object) -> str:
    digest = sha256()
    for part in parts:
        if part is None:
            continue
        digest.update(str(part).strip().encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()


def parse_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = parsedate_to_datetime(value)
        except (TypeError, ValueError):
            return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def repo_from_url_or_config(url: str | None, config: dict[str, Any]) -> tuple[str, str]:
    owner = config.get("owner")
    repo = config.get("repo")
    if owner and repo:
        return str(owner), str(repo)

    if not url:
        raise ValueError("GitHub source requires owner/repo config or repository URL")

    parsed = urlparse(url)
    path_parts = [part for part in parsed.path.strip("/").split("/") if part]
    if len(path_parts) < 2:
        raise ValueError("GitHub repository URL must include owner and repo")
    return path_parts[0], path_parts[1].removesuffix(".git")
