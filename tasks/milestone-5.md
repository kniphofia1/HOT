# 当前任务：Milestone 5 Markdown 简报导出

## 执行限制

当前任务 **Milestone 5：Markdown 简报导出** 已完成验收。

Milestone 1-4 已完成。Milestone 5 只实现 Markdown 简报闭环，不得扩展到 PDF、Word 或任何新增平台。

## 开工前必须阅读

实现前必须阅读：

- `AGENTS.md`
- `docs/product/mvp-v0.1.md`
- `docs/roadmap/milestones.md`
- `docs/decisions/0001-mvp-scope.md`
- 本文件 `tasks/milestone-5.md`

## Milestone 5 允许做的事

- [x] 实现 `BriefTemplate`
- [x] 实现 `BriefExport`
- [x] 实现事件勾选
- [x] 实现人工点评
- [x] 实现 Markdown 预览
- [x] 实现 Markdown 下载
- [x] 内置 AI/科技 与 投资/产业 两个模板

## Milestone 5 禁止做的事

不得实现以下内容：

- PDF 导出
- Word / DOCX 导出
- 邮件发送
- 客户门户
- 多租户
- 团队权限
- 国内平台 `Connector`
- X / Twitter `Connector`
- YouTube 真实 API 请求
- 评论抽样
- 登录态抓取

## Milestone 5 交付物

- [x] `briefExporter` 后端模块
- [x] `BriefTemplate` 初始化与查询 API
- [x] `BriefExport` 创建、预览、下载 API
- [x] 简报页面
- [x] 事件勾选控件
- [x] 人工点评输入
- [x] Markdown 预览与下载
- [x] Milestone 5 测试

## 测试标准

- [x] 可从事件流选择多个 `EventCluster` 生成简报。
- [x] Markdown 包含标题、日期、事件摘要、推荐理由、来源引用、人工点评。
- [x] 内置 AI/科技 与 投资/产业 两个模板。
- [x] 重新编辑点评后可重新生成 Markdown。
- [x] 中文内容、长标题、失效链接、空 `Evidence` 都有稳定降级表现。
- [x] 没有实现 PDF、Word 或其他 v0.1 禁止项。

## 验收后体验补丁：中文翻译展示

Milestone 5 完成后，允许收口一个不扩大产品范围的体验补丁：为已有 `EventCluster` 增加简体中文展示缓存，并让雷达 UI 与 Markdown 简报优先展示中文。

- [x] 新增 `EventCluster` 翻译缓存字段。
- [x] 新增批量和单事件翻译 API。
- [x] 翻译调用写入 `AiRunLog`。
- [x] 翻译失败时保留原始标题和摘要。
- [x] 雷达列表、事件详情、简报选择页和 Markdown 简报优先使用中文展示字段。
- [x] 没有实现 PDF、Word、新平台、多租户、团队权限或登录态抓取。

## 验收后 UI 补丁：信源管理配置台

将 `Sources / 信源管理` 从静态说明页升级为按类型配置的本地信源管理界面，不改变 v0.1 抓取范围。

- [x] 每类 Source 单独展示配置卡片。
- [x] 支持 RSS、公开网页、Hacker News、GitHub repo、GitHub release 的新增表单。
- [x] 支持已有 Source 的启停、立即刷新和确认删除。
- [x] 展示最近抓取时间、最后错误、刷新频率和权重。
- [x] 热榜信源只作为规划入口，不在 connector 落地前创建真实 Source。
- [x] YouTube placeholder 只展示占位说明，不提供真实抓取入口。

## 命名要求

代码命名、数据库表名、字段名、API 路由使用英文。

文档与说明使用中文为主，但保留关键概念英文名，例如：

- `BriefTemplate`
- `BriefExport`
- `EventCluster`
- `Evidence`
- `Markdown`
- `Milestone`
