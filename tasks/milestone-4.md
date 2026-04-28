# 当前任务：Milestone 4 热度评分与雷达 UI

## 执行限制

当前任务 **Milestone 4：热度评分与雷达 UI** 已完成验收。

Milestone 1-4 已完成。Milestone 5 仍然 blocked，不得提前实现 Markdown 简报导出。

## 开工前必须阅读

实现前必须阅读：

- `AGENTS.md`
- `docs/product/mvp-v0.1.md`
- `docs/roadmap/milestones.md`
- `docs/decisions/0001-mvp-scope.md`
- 本文件 `tasks/milestone-4.md`

## Milestone 4 允许做的事

- [x] 实现事件排序
- [x] 实现可解释 `hotScore`
- [x] 构建雷达列表 UI
- [x] 构建事件详情 UI
- [x] 构建运行日志 UI
- [x] 为事件列表提供时间、来源、分数、类型筛选
- [x] 为 UI 提供空状态、加载中、错误状态

## Milestone 4 禁止做的事

不得实现以下内容：

- Markdown 简报导出
- `BriefTemplate` 真实模板工作流
- `BriefExport` 真实导出工作流
- PDF 导出
- Word / DOCX 导出
- YouTube 真实 API 请求
- 国内平台 `Connector`
- X / Twitter `Connector`
- 评论抽样
- 多租户
- 登录态抓取

## Milestone 4 交付物

- [x] `scoring` 后端模块
- [x] 可解释 `hotScore` 写回 `EventCluster`
- [x] 事件列表筛选与排序 API
- [x] 雷达列表页面
- [x] 事件详情页面
- [x] 运行日志页面
- [x] UI 空状态、加载中、错误状态
- [x] Milestone 4 测试

## 测试标准

- [x] 事件列表支持时间、来源、分数、类型筛选。
- [x] 事件默认可按 `hotScore` 和时间排序。
- [x] 每个非空 `hotScore` 都有 `scoreReasonJson`。
- [x] UI 空状态、加载中、错误状态完整。
- [x] 没有实现 Milestone 5 的 Markdown 简报导出。

## 命名要求

代码命名、数据库表名、字段名、API 路由使用英文。

文档与说明使用中文为主，但保留关键概念英文名，例如：

- `EventCluster`
- `Evidence`
- `RawItem`
- `MetricSnapshot`
- `FetchRun`
- `AiRunLog`
- `hotScore`
- `Milestone`
