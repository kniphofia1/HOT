from app.connectors.github import GithubReleaseConnector, GithubRepoConnector
from app.connectors.hacker_news import HackerNewsConnector
from app.connectors.international import (
    DiscordChannelConnector,
    LinkedInPostsConnector,
    SlackChannelConnector,
    TelegramUpdatesConnector,
    TikTokResearchConnector,
    XRecentSearchConnector,
    YouTubeChannelConnector,
)
from app.connectors.rss import RssConnector
from app.connectors.sec_edgar import SecEdgarFilingsConnector
from app.connectors.social import (
    BlueskyActorFeedConnector,
    BlueskySearchConnector,
    MastodonTimelineConnector,
    RedditSubredditConnector,
)
from app.connectors.webpage import WebpageConnector
from app.connectors.youtube_placeholder import youtube_placeholder

connector_instances = [
    RssConnector(),
    HackerNewsConnector(),
    GithubRepoConnector(),
    GithubReleaseConnector(),
    SecEdgarFilingsConnector(),
    WebpageConnector(),
    RedditSubredditConnector(),
    BlueskySearchConnector(),
    BlueskyActorFeedConnector(),
    MastodonTimelineConnector(),
    XRecentSearchConnector(),
    YouTubeChannelConnector(),
    LinkedInPostsConnector(),
    TikTokResearchConnector(),
    TelegramUpdatesConnector(),
    DiscordChannelConnector(),
    SlackChannelConnector(),
]
registered_connectors = [connector.metadata for connector in connector_instances] + [youtube_placeholder]
connectors_by_type = {connector.metadata.type: connector for connector in connector_instances}
