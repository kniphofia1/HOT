from dataclasses import dataclass


@dataclass(frozen=True)
class ConnectorMetadata:
    type: str
    name: str
    capabilities: list[str]
    real_fetch_enabled: bool


class PlaceholderFetchError(RuntimeError):
    pass
