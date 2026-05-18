# ADR 0003：主流国际平台官方 Connector

## 状态

Accepted

## 背景

终局路线图的 Milestone 3 要覆盖国际主流公开讨论场，包括 X、YouTube、LinkedIn、TikTok、Telegram、Discord 和 Slack。

这些平台的访问能力与成本差异很大，且多数需要 API Key、OAuth Token、Bot Token、开发者审核或组织授权。直接做默认抓取会破坏当前系统的合规边界。

## 决策

新增一组凭证门控的官方 Connector：

- `x_recent_search`
- `youtube_channel`
- `linkedin_posts`
- `tiktok_research`
- `telegram_updates`
- `discord_channel`
- `slack_channel`

这些 Connector 只允许使用官方 API、Bot API 或工作区授权 API。缺少凭证时必须失败并写入 `FetchRun`，不得降级到 Cookie、登录态、网页私有抓取或验证码绕过。

## 边界

允许：

- 官方 API。
- 公开内容或用户/组织授权内容。
- Bot 被加入频道、服务器或工作区后的授权读取。
- API 配额、限流和权限错误写入 `FetchRun`。

不允许：

- Cookie 抓取。
- 登录态模拟。
- 私有页面抓取。
- 验证码处理。
- 反爬绕过。
- 全量评论舆情或情感分析。

## 影响

正面影响：

- 终局路线图可以进入国际平台自动化阶段。
- 信源市场能从“后续接入”升级为“凭证配置后可用”。
- 仍然保持 `RawItem`、`FetchRun`、`MetricSnapshot` 和 `Evidence` 的统一链路。

风险与约束：

- 没有凭证时 Connector 会稳定失败而不是尝试替代抓取。
- 平台权限、审核和计费由用户自行配置。
- TikTok Research API 和 LinkedIn Posts API 的可用性取决于官方审核和权限范围。
