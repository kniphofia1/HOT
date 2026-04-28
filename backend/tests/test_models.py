from sqlalchemy import inspect

from app.db.models import Source


def test_core_tables_are_created(db_session):
    table_names = set(inspect(db_session.bind).get_table_names())

    assert {
        "sources",
        "raw_items",
        "fetch_runs",
        "web_monitor_targets",
        "webpage_snapshots",
        "event_candidates",
        "event_clusters",
        "evidence",
        "metric_snapshots",
        "ai_run_logs",
        "brief_templates",
        "brief_exports",
    }.issubset(table_names)


def test_source_table_basic_write_and_read(db_session):
    source = Source(
        type="rss",
        name="Example RSS",
        url="https://example.com/feed.xml",
        config_json={},
    )

    db_session.add(source)
    db_session.commit()
    db_session.refresh(source)

    loaded = db_session.get(Source, source.id)
    assert loaded is not None
    assert loaded.name == "Example RSS"
