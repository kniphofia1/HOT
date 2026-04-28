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

## 命名要求

代码命名、数据库表名、字段名、API 路由使用英文。

文档与说明使用中文为主，但保留关键概念英文名，例如：

- `BriefTemplate`
- `BriefExport`
- `EventCluster`
- `Evidence`
- `Markdown`
- `Milestone`
