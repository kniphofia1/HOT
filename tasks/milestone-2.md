# 当前任务：Milestone 2 连接器与 RawItem 入库

## 执行限制

当前任务 **Milestone 2：连接器与 RawItem 入库** 已完成验收。

Milestone 1 已完成。Milestone 3-5 仍然 blocked，不得提前实现 AI 聚类、热度评分、雷达事件流 UI 或 Markdown 简报导出。

## 开工前必须阅读

实现前必须阅读：

- `AGENTS.md`
- `docs/product/mvp-v0.1.md`
- `docs/roadmap/milestones.md`
- `docs/decisions/0001-mvp-scope.md`
- 本文件 `tasks/milestone-2.md`

## Milestone 2 允许做的事

- [x] 实现 RSS `Connector`
- [x] 实现 HN `Connector`
- [x] 实现 GitHub repo watch
- [x] 实现 GitHub release watch
- [x] 实现网页监控 `Connector`
- [x] 统一写入 `RawItem`
- [x] 统一写入 `FetchRun`
- [x] 统一写入 `MetricSnapshot`
- [x] 实现单个 `Source` 失败不影响其他 `Source`

## Milestone 2 禁止做的事

不得实现以下内容：

- AI 聚类
- AI 摘要
- `EventCluster` 生成逻辑
- `Evidence` 绑定逻辑
- `hotScore` 实际评分逻辑
- Radar 真实事件流 UI
- Markdown 简报导出
- PDF 导出
- Word / DOCX 导出
- YouTube 真实 API 请求
- 国内平台 `Connector`
- X / Twitter `Connector`
- 评论抽样
- 多租户
- 登录态抓取

## Milestone 2 交付物

- [x] RSS / HN / GitHub / 网页监控连接器
- [x] 统一连接器执行服务
- [x] `RawItem`、`FetchRun`、`MetricSnapshot` 写入逻辑
- [x] 手动刷新 API
- [x] 连接器失败隔离
- [x] Milestone 2 测试

## 测试标准

- [x] 3 个真实 RSS 源可解析并去重。
- [x] HN top/new/best 可抓取指定数量。
- [x] GitHub repo/release 可检测新增 release 和基础指标。
- [x] 网页内容不变时不生成重复 `RawItem`，变化时生成 snapshot 和 diff。
- [x] 任一 `Source` 失败不影响其他 `Source` 抓取。
- [x] 没有实现 Milestone 3-5 的业务功能。
