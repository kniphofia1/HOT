# 当前任务：Milestone 3 AI 聚类、摘要与 Evidence

## 执行限制

当前任务 **Milestone 3：AI 聚类、摘要与 Evidence** 已完成验收。

Milestone 1-3 已完成。Milestone 4-5 仍然 blocked，不得提前实现热度评分 UI、雷达事件流 UI 或 Markdown 简报导出。

## 开工前必须阅读

实现前必须阅读：

- `AGENTS.md`
- `docs/product/mvp-v0.1.md`
- `docs/roadmap/milestones.md`
- `docs/decisions/0001-mvp-scope.md`
- 本文件 `tasks/milestone-3.md`

## Milestone 3 允许做的事

- [x] 实现 `EventCandidate` 生成逻辑
- [x] 实现候选分桶
- [x] 实现 AI 合并事件
- [x] 实现 AI 摘要生成
- [x] 实现 `Evidence` 引用链路
- [x] 实现 `AiRunLog` 记录
- [x] 实现 AI 调用失败降级
- [x] 提供事件列表与事件详情 API，用于验证 `EventCluster`、`Evidence` 和原始来源回溯

## Milestone 3 禁止做的事

不得实现以下内容：

- `hotScore` 实际评分逻辑
- Radar 真实事件流 UI
- 前端事件详情页完整交互
- Markdown 简报导出
- PDF 导出
- Word / DOCX 导出
- YouTube 真实 API 请求
- 国内平台 `Connector`
- X / Twitter `Connector`
- 评论抽样
- 多租户
- 登录态抓取

## Milestone 3 交付物

- [x] `RawItem` 到 `EventCandidate` 的标准化链路
- [x] 候选分桶与去重策略
- [x] AI provider 抽象与本地测试替身
- [x] `EventCluster` 生成与更新逻辑
- [x] `Evidence` 来源引用生成逻辑
- [x] `AiRunLog` 成功/失败记录
- [x] 聚类运行 API
- [x] 事件列表和详情 API
- [x] Milestone 3 测试

## 测试标准

- [x] 多个相似 `RawItem` 能聚合为一个 `EventCluster`。
- [x] 不相关 `RawItem` 不应被错误合并。
- [x] 每个 AI 摘要至少绑定 1 条 `Evidence`。
- [x] AI 调用失败时保留 `RawItem` / `EventCandidate`，并记录 `AiRunLog`。
- [x] 事件详情 API 能回溯原始来源链接和引用片段。
- [x] 没有实现 Milestone 4-5 的业务功能。

## 命名要求

代码命名、数据库表名、字段名、API 路由使用英文。

文档与说明使用中文为主，但保留关键概念英文名，例如：

- `RawItem`
- `EventCandidate`
- `EventCluster`
- `Evidence`
- `AiRunLog`
- `Connector`
- `Milestone`
