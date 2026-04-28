from app.connectors.core import ConnectorMetadata, PlaceholderFetchError


youtube_placeholder = ConnectorMetadata(
    type="youtube_placeholder",
    name="YouTube placeholder",
    capabilities=[],
    real_fetch_enabled=False,
)


def fetch_youtube_placeholder() -> None:
    raise PlaceholderFetchError("YouTube real fetching is out of scope for Milestone 1.")
