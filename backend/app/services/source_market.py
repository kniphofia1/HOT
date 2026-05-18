from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SourcePlatformCapability:
    platform: str
    source_type: str
    category: str
    access_mode: str
    automation_level: str
    status: str
    requires_credential: bool
    requires_approval: bool
    supports_metrics: bool
    cost_level: str
    notes: str


SOURCE_PLATFORM_CAPABILITIES = [
    SourcePlatformCapability("RSS", "rss", "feed", "official_or_public_feed", "full", "available", False, False, False, "free", "公开 Feed，适合作为高可信基础信源。"),
    SourcePlatformCapability("Public Webpage", "webpage", "web", "public_webpage", "full", "available", False, False, False, "free", "仅公开网页和 CSS 文本抽取，不处理登录、验证码或私有页面。"),
    SourcePlatformCapability("Hacker News", "hacker_news", "developer_community", "official_public_api", "full", "available", False, False, True, "free", "官方 Firebase API，适合技术社区早期信号。"),
    SourcePlatformCapability("GitHub Repo", "github_repo", "developer_platform", "official_public_api", "full", "available", False, False, True, "free_or_token", "公开仓库可直接读取，配置 token 可提高限流额度。"),
    SourcePlatformCapability("GitHub Release", "github_release", "developer_platform", "official_public_api", "full", "available", False, False, True, "free_or_token", "跟踪 release 与下载量指标。"),
    SourcePlatformCapability("SEC EDGAR", "sec_edgar_filings", "company_filings", "official_public_api", "full", "available", False, False, False, "free", "SEC 官方公开 JSON submissions API，用于跟踪公司 10-K、10-Q、8-K 等公告。"),
    SourcePlatformCapability("Reddit", "reddit_subreddit", "social_forum", "public_endpoint_or_api", "full", "available", False, False, True, "free_or_token", "公开 subreddit 与搜索结果，后续可补充 API credentials 提高稳定性。"),
    SourcePlatformCapability("Bluesky Search", "bluesky_search", "social_network", "public_api", "full", "available", False, False, True, "free", "公开搜索可能受平台限流影响。"),
    SourcePlatformCapability("Bluesky Author Feed", "bluesky_actor_feed", "social_network", "public_api", "full", "available", False, False, True, "free", "适合跟踪官方账号、研究员和机构账号。"),
    SourcePlatformCapability("Mastodon", "mastodon_timeline", "federated_social", "public_instance_api", "full", "available", False, False, True, "free", "由用户选择公开实例，不同实例覆盖不同。"),
    SourcePlatformCapability("Manual Link", "manual_link", "manual_evidence", "manual_input", "manual", "available", False, False, False, "free", "用于补录无法自动抓取但可公开访问的链接。"),
    SourcePlatformCapability("X", "x_recent_search", "social_network", "official_paid_api", "credentialed", "available", True, True, True, "paid", "仅走官方 recent search API；缺少 bearer token 时只记录失败，不回退抓取。"),
    SourcePlatformCapability("YouTube", "youtube_channel", "video", "official_data_api", "credentialed", "available", True, True, True, "quota", "仅走 YouTube Data API；需要 API key 与配额管理。"),
    SourcePlatformCapability("LinkedIn", "linkedin_posts", "professional_network", "official_reviewed_api", "credentialed", "available", True, True, True, "reviewed", "官方 API 审核和权限边界较强，适合企业或自有组织授权。"),
    SourcePlatformCapability("TikTok", "tiktok_research", "short_video", "research_or_authorized_api", "credentialed", "available", True, True, True, "reviewed", "Research API 或官方授权能力，不做非官方抓取。"),
    SourcePlatformCapability("Telegram", "telegram_updates", "messaging", "bot_member_updates", "credentialed", "available", True, False, True, "free", "仅读取 bot 被授权加入的频道或群更新。"),
    SourcePlatformCapability("Discord", "discord_channel", "messaging", "bot_channel_api", "credentialed", "available", True, False, True, "free", "仅读取 bot 被授权加入服务器后的指定频道消息。"),
    SourcePlatformCapability("Slack", "slack_channel", "team_messaging", "workspace_authorized_api", "credentialed", "available", True, False, True, "free_or_paid", "仅读取 workspace 授权范围内的 conversation history。"),
    SourcePlatformCapability("微博", "weibo_official", "domestic_social", "official_or_manual", "manual_or_planned", "deferred", True, True, True, "reviewed", "后续只走官方能力或人工补录。"),
    SourcePlatformCapability("B站", "bilibili_official", "domestic_video", "official_or_manual", "manual_or_planned", "deferred", True, True, True, "reviewed", "后续只走开放平台、自有授权或人工补录。"),
    SourcePlatformCapability("知乎", "zhihu_manual", "domestic_content", "manual_input", "manual", "manual_only", False, False, False, "free", "当前只允许人工链接补录。"),
    SourcePlatformCapability("微信公众号", "wechat_official_or_manual", "domestic_content", "official_or_manual", "manual_or_planned", "deferred", True, True, True, "reviewed", "非自有文章优先人工补录；自有账号需官方授权。"),
    SourcePlatformCapability("小红书", "xiaohongshu_manual", "domestic_social", "manual_input", "manual", "manual_only", False, False, False, "free", "当前只允许人工链接补录。"),
    SourcePlatformCapability("抖音", "douyin_official", "domestic_short_video", "official_or_manual", "manual_or_planned", "deferred", True, True, True, "reviewed", "后续只走开放平台、自有授权或人工补录。"),
    SourcePlatformCapability("快手", "kuaishou_official", "domestic_short_video", "official_or_manual", "manual_or_planned", "deferred", True, True, True, "reviewed", "后续只走官方能力或人工补录。"),
]


def list_source_platform_capabilities() -> list[SourcePlatformCapability]:
    return SOURCE_PLATFORM_CAPABILITIES
