# 当前任务：Milestone 1 工程底座与数据层

## 执行限制

当前任务 **Milestone 1：工程底座与数据层** 已完成验收。

在 `docs/roadmap/milestones.md` 明确更新前，不得实现 Milestone 2-5 的任何业务能力。

## 开工前必须阅读

实现前必须阅读：

- `AGENTS.md`
- `docs/product/mvp-v0.1.md`
- `docs/roadmap/milestones.md`
- `docs/decisions/0001-mvp-scope.md`
- 本文件 `tasks/milestone-1.md`

## Milestone 1 允许做的事

- [x] 搭建 Docker Compose
- [x] 创建后端应用壳
- [x] 创建前端应用壳
- [x] 添加数据库迁移机制
- [x] 创建 v0.1 核心表结构
- [x] 实现 `Source` CRUD
- [x] 注册 YouTube placeholder `Connector`
- [x] 添加核心表基础读写测试
- [x] 添加 `Source` CRUD 测试
- [x] 验证空库可完整初始化

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

- [x] 可启动的本地开发环境
- [x] 后端与前端基础项目结构
- [x] 数据库迁移机制
- [x] 核心数据表
- [x] `Source` CRUD API
- [x] YouTube placeholder `Connector`，只注册接口，不抓取
- [x] 基础测试

## 测试标准

- [x] Docker Compose 一条命令能启动前端、后端、数据库。
- [x] 迁移可重复执行，空库可完整初始化。
- [x] `Source` 能创建、编辑、启停、删除。
- [x] 核心表有基础读写测试。
- [x] YouTube placeholder 只注册接口，不执行真实抓取。
- [x] 所有 Milestone 1 测试通过。
- [x] 没有实现 Milestone 2-5 的业务功能。

## 命名要求

代码命名、数据库表名、字段名、API 路由使用英文。

文档与说明使用中文为主，但保留关键概念英文名，例如：

- `Source`
- `RawItem`
- `Connector`
- `EventCluster`
- `Evidence`
- `Milestone`
