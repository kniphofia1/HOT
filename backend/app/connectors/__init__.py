from app.connectors.github import GithubReleaseConnector, GithubRepoConnector
from app.connectors.hacker_news import HackerNewsConnector
from app.connectors.rss import RssConnector
from app.connectors.webpage import WebpageConnector
from app.connectors.youtube_placeholder import youtube_placeholder

connector_instances = [
    RssConnector(),
    HackerNewsConnector(),
    GithubRepoConnector(),
    GithubReleaseConnector(),
    WebpageConnector(),
]
registered_connectors = [connector.metadata for connector in connector_instances] + [youtube_placeholder]
connectors_by_type = {connector.metadata.type: connector for connector in connector_instances}
