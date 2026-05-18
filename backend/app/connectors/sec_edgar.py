from __future__ import annotations

import os
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.connectors.core import BaseConnector, ConnectorMetadata
from app.connectors.types import ConnectorError, ConnectorFetchResult, RawItemPayload
from app.connectors.utils import parse_datetime, stable_hash
from app.db.models import Source


SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
SEC_ARCHIVE_URL = "https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{document}"
DEFAULT_FORMS = {"10-K", "10-Q", "8-K", "S-1", "S-3", "6-K", "20-F"}


class SecEdgarFilingsConnector(BaseConnector):
    metadata = ConnectorMetadata(
        type="sec_edgar_filings",
        name="SEC EDGAR filings",
        capabilities=["content_fetch"],
        real_fetch_enabled=True,
    )

    def fetch(self, db: Session, source: Source) -> ConnectorFetchResult:
        companies = source.config_json.get("companies")
        if not isinstance(companies, list) or not companies:
            raise ConnectorError("SEC EDGAR source requires companies config")

        forms = {str(form).upper() for form in source.config_json.get("forms", DEFAULT_FORMS)}
        limit = _bounded_int(source.config_json.get("limit", 30), 1, 100)
        headers = {
            "User-Agent": os.getenv("SEC_USER_AGENT", "AIHOT local research radar contact@example.com"),
            "Accept-Encoding": "gzip, deflate",
            "Accept": "application/json",
        }

        items: list[RawItemPayload] = []
        for company in companies:
            company_config = _company_config(company)
            response = httpx.get(
                SEC_SUBMISSIONS_URL.format(cik=company_config["cik_padded"]),
                headers=headers,
                timeout=20.0,
                follow_redirects=True,
            )
            response.raise_for_status()
            items.extend(_items_for_company(response.json(), company_config, forms=forms, limit=limit))

        return ConnectorFetchResult(items=items[:limit])


def _company_config(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        raise ConnectorError("SEC EDGAR companies entries must be objects")
    cik = str(value.get("cik") or "").strip()
    if not cik.isdigit():
        raise ConnectorError("SEC EDGAR company requires numeric cik")
    cik_padded = cik.zfill(10)
    cik_archive = str(int(cik_padded))
    ticker = str(value.get("ticker") or cik_archive).upper()
    name = str(value.get("name") or ticker)
    return {"cik_padded": cik_padded, "cik_archive": cik_archive, "ticker": ticker, "name": name}


def _items_for_company(
    payload: dict[str, Any],
    company: dict[str, str],
    *,
    forms: set[str],
    limit: int,
) -> list[RawItemPayload]:
    recent = (payload.get("filings") or {}).get("recent") or {}
    accession_numbers = _list_value(recent, "accessionNumber")
    form_values = _list_value(recent, "form")
    filing_dates = _list_value(recent, "filingDate")
    report_dates = _list_value(recent, "reportDate")
    acceptance_times = _list_value(recent, "acceptanceDateTime")
    primary_documents = _list_value(recent, "primaryDocument")
    items_descriptions = _list_value(recent, "items")

    items: list[RawItemPayload] = []
    for index, accession in enumerate(accession_numbers):
        form_type = _at(form_values, index).upper()
        if forms and form_type not in forms:
            continue
        primary_document = _at(primary_documents, index) or f"{accession}-index.htm"
        filing_date = _at(filing_dates, index)
        report_date = _at(report_dates, index)
        accepted_at = _at(acceptance_times, index)
        accession_compact = accession.replace("-", "")
        source_url = SEC_ARCHIVE_URL.format(
            cik=company["cik_archive"],
            accession=accession_compact,
            document=primary_document,
        )
        title = f"{company['ticker']} {form_type} filing"
        if filing_date:
            title = f"{title} - {filing_date}"
        content = (
            f"{company['name']} ({company['ticker']}) filed Form {form_type} with SEC EDGAR."
            f" Filing date: {filing_date or 'unknown'}."
            f" Report date: {report_date or 'unknown'}."
        )
        items_value = _at(items_descriptions, index)
        if items_value:
            content = f"{content} Items: {items_value}."
        items.append(
            RawItemPayload(
                external_id=f"{company['cik_padded']}:{accession}:{primary_document}",
                source_url=source_url,
                title=title,
                content_text=content,
                author=company["ticker"],
                published_at=parse_datetime(accepted_at or filing_date),
                raw_payload_json={
                    "company": company,
                    "form": form_type,
                    "accessionNumber": accession,
                    "filingDate": filing_date,
                    "reportDate": report_date,
                    "acceptanceDateTime": accepted_at,
                    "primaryDocument": primary_document,
                    "items": items_value,
                },
                content_hash=stable_hash(company["cik_padded"], accession, primary_document, form_type),
            )
        )
        if len(items) >= limit:
            break
    return items


def _list_value(payload: dict[str, Any], key: str) -> list[str]:
    value = payload.get(key)
    if not isinstance(value, list):
        return []
    return [str(item or "") for item in value]


def _at(values: list[str], index: int) -> str:
    if index >= len(values):
        return ""
    return values[index].strip()


def _bounded_int(value: Any, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = minimum
    return max(minimum, min(maximum, parsed))
