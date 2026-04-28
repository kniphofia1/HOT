from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.connectors.types import ConnectorFetchResult
from app.db.models import Source


@dataclass(frozen=True)
class ConnectorMetadata:
    type: str
    name: str
    capabilities: list[str]
    real_fetch_enabled: bool


class PlaceholderFetchError(RuntimeError):
    pass


class BaseConnector:
    metadata: ConnectorMetadata

    def fetch(self, db: Session, source: Source) -> ConnectorFetchResult:
        raise NotImplementedError
