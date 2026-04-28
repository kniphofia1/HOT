# 当前任务：Milestone 1 工程底座与数据层

## 执行限制

当前只允许实现 **Milestone 1：工程底座与数据层**。

在 `docs/roadmap/milestones.md` 明确更新前，不得实现 Milestone 2-5 的任何业务能力。

## 开工前必须阅读

实现前必须阅读：

- `AGENTS.md`
- `docs/product/mvp-v0.1.md`
- `docs/roadmap/milestones.md`
- `docs/decisions/0001-mvp-scope.md`
- 本文件 `tasks/milestone-1.md`

## Milestone 1 允许做的事

- 搭建 Docker Compose
- 创建后端应用壳
- 创建前端应用壳
- 添加数据库迁移机制
- 创建 v0.1 核心表结构
- 实现 `Source` CRUD
- 注册 YouTube placeholder `Connector`
- 添加核心表基础读写测试
- 添加 `Source` CRUD 测试
- 验证空库可完整初始化

## Milestone 1 禁止做的事

不得实现以下内容：

- RSS 真实抓取
- Hacker News 真实抓取
- GitHub 真实抓取
- 公开网页真实抓取
- `RawItem` 真实入库流程
- AI 聚类
- AI 摘要
- `EventCluster` 生成逻辑
- `Evidence` 绑定逻辑
- `hotScore` 实际评分逻辑
- Radar 事件流 UI
- Markdown 简报导出
- PDF 导出
- Word / DOCX 导出
- YouTube 真实 API 请求
- 国内平台 `Connector`
- X / Twitter `Connector`
- 评论抽样
- 多租户
- 登录态抓取

## Milestone 1 交付物

- 可启动的本地开发环境
- 后端与前端基础项目结构
- 数据库迁移机制
- 核心数据表
- `Source` CRUD API
- YouTube placeholder `Connector`，只注册接口，不抓取
- 基础测试

## 测试标准

- Docker Compose 一条命令能启动前端、后端、数据库。
- 迁移可重复执行，空库可完整初始化。
- `Source` 能创建、编辑、启停、删除。
- 核心表有基础读写测试。
- YouTube placeholder 只注册接口，不执行真实抓取。
- 所有 Milestone 1 测试通过。
- 没有实现 Milestone 2-5 的业务功能。

## 命名要求

代码命名、数据库表名、字段名、API 路由使用英文。

文档与说明使用中文为主，但保留关键概念英文名，例如：

- `Source`
- `RawItem`
- `Connector`
- `EventCluster`
- `Evidence`
- `Milestone`
