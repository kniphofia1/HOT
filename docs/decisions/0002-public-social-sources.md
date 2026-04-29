# ADR 0002：公开社交媒体信源扩展

## 状态

Accepted

## 背景

Milestone 1-5 已完成，系统已经具备 `Source`、`RawItem`、`FetchRun`、`Evidence`、`EventCluster` 和 Markdown 简报闭环。

只接入 RSS、公开网页、HN 和 GitHub 后，系统对研究员关心的公共讨论场覆盖不足。用户明确需要“很多个主流社交媒体的信息”，但不能破坏本项目的本地优先、可信来源链路和合规边界。

## 决策

在 v0.1 验收后增加第一批公开社交媒体 Connector：

- `reddit_subreddit`：抓取公开 subreddit 列表或 subreddit 内搜索结果。
- `bluesky_search`：通过 Bluesky 公开 API 抓取关键词搜索结果。
- `bluesky_actor_feed`：通过 Bluesky 公开 API 抓取指定账号公开时间线。
- `mastodon_timeline`：抓取 Mastodon 实例公开时间线或公开标签时间线。

这些 Connector 的结果仍然必须先进入 `RawItem`，再进入现有标准化、聚类、证据和简报链路。UI 必须按每一种信源提供独立配置卡片，而不是把它们混成一个泛化“热榜”入口。

## 边界

允许：

- 官方 API、公开 API、公开网页端点。
- 用户自行配置的公开实例、公开关键词、公开 subreddit。
- 可选 API 凭证，例如 Reddit app credentials，用于提高稳定性和限流额度。
- 公开内容元数据指标，例如分数、评论数、回复数、转发数、点赞数。

不允许：

- X / Twitter 真实数据 Connector。
- 国内平台 Connector，包括微博、B站、知乎、微信公众号、小红书、抖音、快手等。
- YouTube 真实 API 请求或真实网页抓取。
- 登录态抓取、Cookie 抓取、验证码处理、私有页面抓取、反爬绕过。
- 评论抽样、全量评论舆情或情感分析。
- 保存用户社交账号凭证用于模拟登录。

## 理由

Reddit、Bluesky 和 Mastodon 都能通过公开或官方链路获取信息，适合验证“社交讨论场作为信源”的产品价值，且不会迫使系统进入登录态、Cookie 和反爬绕过问题。Bluesky 关键词搜索在部分环境下可能被平台要求鉴权，因此同时提供公开作者 feed 作为稳定可抓取入口。

这组三个 Connector 能覆盖社区论坛、公开短文本网络和联邦实例时间线三种不同形态，同时仍然保持 `Connector` 隔离、`RawItem` 入库和 `Evidence` 可追溯的既有设计。

## 影响

正面影响：

- 研究员可以把主流公开讨论场纳入事件聚类。
- 同一事件可以显示来自 RSS、GitHub、HN、Reddit、Bluesky、Mastodon 等多源报道。
- 信源管理 UI 从“规划入口”变为可配置的多类型信源控制台。

风险与约束：

- Reddit 公共 JSON 端点可能限流，建议配置 Reddit API credentials。
- Bluesky 搜索 API 的排序、覆盖和限流由平台控制。
- Mastodon 需要用户选择具体公开实例，不同实例内容覆盖差异较大。
- 后续接入 X、国内平台或视频平台必须另行新增 ADR，并明确 API、成本、限流和合规方案。
