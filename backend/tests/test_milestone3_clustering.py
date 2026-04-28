from sqlalchemy import select

from app.connectors.types import RawItemPayload
from app.db.models import AiRunLog, EventCandidate, EventCluster, Evidence, RawItem, Source
from app.services.ai import AiCandidate, AiClusterSummary
from app.services.clustering import run_event_clustering
from app.services.ingestion import ingest_raw_item


class FakeAiProvider:
    model = "fake-cluster-model"

    def summarize_cluster(self, candidates: list[AiCandidate]) -> AiClusterSummary:
        return AiClusterSummary(
            title=candidates[0].title,
            summary=f"{len(candidates)} related items: {candidates[0].title}",
            confidence=86,
            candidate_ids=[candidate.id for candidate in candidates],
        )


class FailingAiProvider:
    model = "failing-model"

    def summarize_cluster(self, candidates: list[AiCandidate]) -> AiClusterSummary:
        raise RuntimeError("AI unavailable")


def test_similar_raw_items_are_clustered_with_evidence(db_session):
    official = _source(db_session, "Official Blog")
    hn = _source(db_session, "Hacker News")
    _raw_item(
        db_session,
        official,
        title="OpenAI releases GPT-5 model",
        source_url="https://openai.com/index/gpt-5",
        content_text="OpenAI announced GPT-5 with stronger coding ability.",
    )
    _raw_item(
        db_session,
        hn,
        title="GPT-5 released by OpenAI",
        source_url="https://news.ycombinator.com/item?id=123",
        content_text="HN discussion about GPT-5 launch details.",
    )

    result = run_event_clustering(db_session, ai_provider=FakeAiProvider())

    assert result.status == "success"
    assert result.candidates_created == 0
    assert result.clusters_created == 1
    cluster = db_session.scalar(select(EventCluster))
    assert cluster is not None
    assert cluster.summary is not None
    evidence = db_session.scalars(select(Evidence)).all()
    assert len(evidence) == 2
    assert {item.source_name for item in evidence} == {"Official Blog", "Hacker News"}


def test_unrelated_raw_items_are_not_merged(db_session):
    source = _source(db_session, "Tech Feed")
    _raw_item(
        db_session,
        source,
        title="OpenAI releases GPT-5 model",
        source_url="https://example.com/openai-gpt-5",
        content_text="OpenAI release details.",
    )
    _raw_item(
        db_session,
        source,
        title="Anthropic publishes Claude reliability report",
        source_url="https://example.com/anthropic-claude-report",
        content_text="Anthropic reliability research details.",
    )

    result = run_event_clustering(db_session, ai_provider=FakeAiProvider())

    assert result.status == "success"
    assert result.clusters_created == 2
    clusters = db_session.scalars(select(EventCluster)).all()
    assert len(clusters) == 2


def test_ai_failure_preserves_candidates_and_records_run_log(db_session):
    source = _source(db_session, "RSS")
    _raw_item(
        db_session,
        source,
        title="GitHub releases new repository insights",
        source_url="https://example.com/github-insights",
        content_text="Repository analytics update.",
    )

    result = run_event_clustering(db_session, ai_provider=FailingAiProvider())

    assert result.status == "failed"
    assert db_session.scalar(select(RawItem)) is not None
    assert db_session.scalar(select(EventCandidate)) is not None
    assert db_session.scalar(select(EventCluster)) is None
    run_log = db_session.scalar(select(AiRunLog))
    assert run_log is not None
    assert run_log.status == "failed"
    assert run_log.error_message == "AI unavailable"


def test_cluster_detail_api_returns_source_links_and_quotes(client, db_session):
    source = _source(db_session, "GitHub")
    _raw_item(
        db_session,
        source,
        title="Example repo publishes v1.0.0",
        source_url="https://github.com/example/repo/releases/tag/v1.0.0",
        content_text="Release notes include the first stable version.",
    )
    result = run_event_clustering(db_session, ai_provider=FakeAiProvider())
    assert result.status == "success"
    cluster = db_session.scalar(select(EventCluster))
    assert cluster is not None

    response = client.get(f"/api/clusters/{cluster.id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["evidenceCount"] == 1
    assert payload["evidence"][0]["sourceName"] == "GitHub"
    assert payload["evidence"][0]["sourceUrl"] == "https://github.com/example/repo/releases/tag/v1.0.0"
    assert payload["evidence"][0]["quote"] == "Release notes include the first stable version."
    assert payload["evidence"][0]["rawTitle"] == "Example repo publishes v1.0.0"


def test_cluster_run_api_reports_missing_ai_configuration(client, db_session):
    source = _source(db_session, "RSS")
    _raw_item(
        db_session,
        source,
        title="RSS item without configured AI",
        source_url="https://example.com/rss-item",
        content_text="This item should become an EventCandidate before failure.",
    )

    response = client.post("/api/clusters/run")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "failed"
    assert payload["aiRunsCreated"] == 1
    assert db_session.scalar(select(EventCandidate)) is not None
    assert db_session.scalar(select(AiRunLog)).status == "failed"


def _source(db_session, name: str) -> Source:
    source = Source(type="rss", name=name, url=f"https://example.com/{name}", config_json={})
    db_session.add(source)
    db_session.commit()
    db_session.refresh(source)
    return source


def _raw_item(
    db_session,
    source: Source,
    *,
    title: str,
    source_url: str,
    content_text: str,
) -> RawItem:
    raw_item, _ = ingest_raw_item(
        db_session,
        source,
        RawItemPayload(
            external_id=source_url,
            source_url=source_url,
            title=title,
            content_text=content_text,
            author=None,
            published_at=None,
            raw_payload_json={},
        ),
    )
    db_session.commit()
    db_session.refresh(raw_item)
    return raw_item
