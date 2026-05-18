from __future__ import annotations

import os

import httpx
from sqlalchemy.orm import Session

from app.connectors.core import BaseConnector, ConnectorMetadata
from app.connectors.types import ConnectorFetchResult, MetricPayload, RawItemPayload
from app.connectors.utils import parse_datetime, repo_from_url_or_config, stable_hash
from app.db.models import Source


GITHUB_API_BASE = "https://api.github.com"


class GithubRepoConnector(BaseConnector):
    metadata = ConnectorMetadata(
        type="github_repo",
        name="GitHub repo watch",
        capabilities=["content_fetch", "metric_refresh"],
        real_fetch_enabled=True,
    )

    def fetch(self, db: Session, source: Source) -> ConnectorFetchResult:
        owner, repo = repo_from_url_or_config(source.url, source.config_json)
        repo_payload = _github_get(f"/repos/{owner}/{repo}")
        full_name = repo_payload["full_name"]
        html_url = repo_payload["html_url"]
        description = repo_payload.get("description")
        items = [
            RawItemPayload(
                external_id=full_name,
                source_url=html_url,
                title=f"GitHub repo watch: {full_name}",
                content_text=description,
                author=owner,
                published_at=parse_datetime(
                    repo_payload.get("pushed_at") or repo_payload.get("updated_at") or repo_payload.get("created_at")
                ),
                raw_payload_json=repo_payload,
                content_hash=stable_hash("github_repo", full_name),
                metrics=[
                    MetricPayload("github_stars", int(repo_payload.get("stargazers_count") or 0)),
                    MetricPayload("github_forks", int(repo_payload.get("forks_count") or 0)),
                    MetricPayload("github_open_issues", int(repo_payload.get("open_issues_count") or 0)),
                ],
            )
        ]
        return ConnectorFetchResult(items=items)


class GithubReleaseConnector(BaseConnector):
    metadata = ConnectorMetadata(
        type="github_release",
        name="GitHub release watch",
        capabilities=["content_fetch", "metric_refresh"],
        real_fetch_enabled=True,
    )

    def fetch(self, db: Session, source: Source) -> ConnectorFetchResult:
        owner, repo = repo_from_url_or_config(source.url, source.config_json)
        limit = int(source.config_json.get("limit", 10))
        releases = _github_get(f"/repos/{owner}/{repo}/releases")
        items: list[RawItemPayload] = []
        for release in releases[:limit]:
            release_id = str(release["id"])
            tag_name = release.get("tag_name") or release_id
            html_url = release.get("html_url")
            author = release.get("author") or {}
            download_count = sum(int(asset.get("download_count") or 0) for asset in release.get("assets", []))
            items.append(
                RawItemPayload(
                    external_id=release_id,
                    source_url=html_url,
                    title=f"GitHub release: {owner}/{repo} {tag_name}",
                    content_text=release.get("body"),
                    author=author.get("login"),
                    published_at=parse_datetime(release.get("published_at") or release.get("created_at")),
                    raw_payload_json=release,
                    content_hash=stable_hash("github_release", owner, repo, release_id, tag_name),
                    metrics=[MetricPayload("github_release_downloads", download_count)],
                )
            )
        return ConnectorFetchResult(items=items)


def _github_get(path: str):
    headers = {"Accept": "application/vnd.github+json"}
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    response = httpx.get(f"{GITHUB_API_BASE}{path}", headers=headers, timeout=20.0)
    response.raise_for_status()
    return response.json()
