from datetime import timezone

from sqlalchemy import select

from app.db.models import RawItem, Source
from app.services.connector_runner import run_source_fetch


class FakeResponse:
    def json(self):
        return {
            "filings": {
                "recent": {
                    "accessionNumber": ["0001045810-26-000001", "0001045810-26-000002"],
                    "form": ["10-Q", "4"],
                    "filingDate": ["2026-05-10", "2026-05-11"],
                    "reportDate": ["2026-04-30", "2026-05-10"],
                    "acceptanceDateTime": ["2026-05-10T12:30:00.000Z", "2026-05-11T12:30:00.000Z"],
                    "primaryDocument": ["nvda-20260430.htm", "ownership.htm"],
                    "items": ["", ""],
                }
            }
        }

    def raise_for_status(self):
        return None


def test_sec_edgar_connector_writes_filtered_filings(monkeypatch, db_session):
    def fake_get(url, **kwargs):
        assert url == "https://data.sec.gov/submissions/CIK0001045810.json"
        assert "User-Agent" in kwargs["headers"]
        return FakeResponse()

    monkeypatch.setattr("app.connectors.sec_edgar.httpx.get", fake_get)
    source = Source(
        type="sec_edgar_filings",
        name="SEC NVIDIA",
        url="https://www.sec.gov/search-filings",
        config_json={
            "companies": [{"ticker": "NVDA", "name": "NVIDIA", "cik": "1045810"}],
            "forms": ["10-Q"],
            "limit": 5,
        },
    )
    db_session.add(source)
    db_session.commit()

    run = run_source_fetch(db_session, source)

    assert run.status == "success"
    assert run.items_created == 1
    item = db_session.scalar(select(RawItem))
    assert item is not None
    assert item.title == "NVDA 10-Q filing - 2026-05-10"
    assert item.author == "NVDA"
    assert item.source_url == "https://www.sec.gov/Archives/edgar/data/1045810/000104581026000001/nvda-20260430.htm"
    assert item.published_at is not None
    assert item.published_at.replace(tzinfo=timezone.utc).isoformat().startswith("2026-05-10T12:30:00")
