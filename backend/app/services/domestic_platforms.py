from __future__ import annotations

from dataclasses import dataclass


PROHIBITED_PATHS = [
    "cookie_capture",
    "login_session_scraping",
    "captcha_bypass",
    "private_page_scraping",
    "anti_bot_bypass",
    "bulk_comment_sentiment",
]


@dataclass(frozen=True)
class DomesticPlatformPolicy:
    platform: str
    source_type: str
    status: str
    automation_level: str
    requires_credential: bool
    requires_approval: bool
    allowed_paths: list[str]
    prohibited_paths: list[str]
    manual_source_name: str
    notes: str


DOMESTIC_PLATFORM_POLICIES = [
    DomesticPlatformPolicy(
        platform="微博",
        source_type="weibo_official",
        status="official_auth_required",
        automation_level="manual_or_official",
        requires_credential=True,
        requires_approval=True,
        allowed_paths=["official_open_platform", "owned_account_authorization", "manual_link"],
        prohibited_paths=PROHIBITED_PATHS,
        manual_source_name="Manual Weibo",
        notes="当前不抓取微博页面；可人工补录公开链接，后续只考虑官方或自有授权能力。",
    ),
    DomesticPlatformPolicy(
        platform="B站",
        source_type="bilibili_official",
        status="official_auth_required",
        automation_level="manual_or_official",
        requires_credential=True,
        requires_approval=True,
        allowed_paths=["official_open_platform", "owned_account_authorization", "manual_link"],
        prohibited_paths=PROHIBITED_PATHS,
        manual_source_name="Manual Bilibili",
        notes="当前不抓取视频页或评论；可补录公开视频链接和人工摘要。",
    ),
    DomesticPlatformPolicy(
        platform="知乎",
        source_type="zhihu_manual",
        status="manual_only",
        automation_level="manual",
        requires_credential=False,
        requires_approval=False,
        allowed_paths=["manual_link"],
        prohibited_paths=PROHIBITED_PATHS,
        manual_source_name="Manual Zhihu",
        notes="当前只允许人工补录公开问题、回答或文章链接。",
    ),
    DomesticPlatformPolicy(
        platform="微信公众号",
        source_type="wechat_official_or_manual",
        status="official_auth_required",
        automation_level="manual_or_official",
        requires_credential=True,
        requires_approval=True,
        allowed_paths=["owned_account_official_api", "manual_link"],
        prohibited_paths=PROHIBITED_PATHS,
        manual_source_name="Manual WeChat",
        notes="第三方公众号文章只做人工补录；自有账号能力必须走官方授权。",
    ),
    DomesticPlatformPolicy(
        platform="小红书",
        source_type="xiaohongshu_manual",
        status="manual_only",
        automation_level="manual",
        requires_credential=False,
        requires_approval=False,
        allowed_paths=["manual_link"],
        prohibited_paths=PROHIBITED_PATHS,
        manual_source_name="Manual Xiaohongshu",
        notes="当前只允许人工补录公开链接和人工摘要，不做页面抓取。",
    ),
    DomesticPlatformPolicy(
        platform="抖音",
        source_type="douyin_official",
        status="official_auth_required",
        automation_level="manual_or_official",
        requires_credential=True,
        requires_approval=True,
        allowed_paths=["official_open_platform", "owned_account_authorization", "manual_link"],
        prohibited_paths=PROHIBITED_PATHS,
        manual_source_name="Manual Douyin",
        notes="当前不抓取视频页或评论；后续只考虑开放平台或自有授权能力。",
    ),
    DomesticPlatformPolicy(
        platform="快手",
        source_type="kuaishou_official",
        status="official_auth_required",
        automation_level="manual_or_official",
        requires_credential=True,
        requires_approval=True,
        allowed_paths=["official_open_platform", "owned_account_authorization", "manual_link"],
        prohibited_paths=PROHIBITED_PATHS,
        manual_source_name="Manual Kuaishou",
        notes="当前不抓取视频页或评论；后续只考虑官方能力或人工补录。",
    ),
]


def list_domestic_platform_policies() -> list[DomesticPlatformPolicy]:
    return DOMESTIC_PLATFORM_POLICIES
