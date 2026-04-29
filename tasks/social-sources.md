# 当前任务：公开社交媒体信源扩展

## 执行限制

Milestone 1-5 已完成，本任务是在 v0.1 验收后的公开社交信源扩展。

本任务只允许实现不需要登录态、不保存 Cookie、不绕过访问控制的公开或官方链路。

## 开工前必须阅读

实现前必须阅读：

- `AGENTS.md`
- `docs/product/mvp-v0.1.md`
- `docs/roadmap/milestones.md`
- `docs/decisions/0001-mvp-scope.md`
- `docs/decisions/0002-public-social-sources.md`
- 本文件 `tasks/social-sources.md`

## 允许做的事

- [x] 实现 `reddit_subreddit` Connector。
- [x] 实现 `bluesky_search` Connector。
- [x] 实现 `bluesky_actor_feed` Connector。
- [x] 实现 `mastodon_timeline` Connector。
- [x] 所有抓取结果统一进入 `RawItem` 和 `FetchRun`。
- [x] 为社交指标写入 `MetricSnapshot`。
- [x] 在信源管理页面为每类社交信源提供独立配置卡片。
- [x] 文档明确受限平台仍然不可抓取。
- [x] 增加后端 Connector 测试和前端类型检查。

## 禁止做的事

不得实现以下内容：

- X / Twitter 真实数据 Connector。
- 国内平台 Connector。
- YouTube 真实 API 请求或真实网页抓取。
- 登录态抓取。
- Cookie 抓取。
- 验证码处理。
- 私有页面抓取。
- 反爬绕过。
- 评论抽样、全量评论舆情或情感分析。

## 验收标准

- `GET /api/connectors` 能看到 Reddit、Bluesky、Mastodon 真实 Connector。
- 三个 Connector 均能被 `run_source_fetch` 调用并生成 `RawItem`。
- 社交指标能作为 `MetricSnapshot` 记录。
- 信源管理页每种社交信源都是独立配置卡片。
- 受限平台只显示说明，不提供真实抓取入口。
