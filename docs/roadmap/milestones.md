# Milestone 路线图

## 执行规则

当前任务 **Milestone 5：Markdown 简报导出** 已完成验收。

不得实现 v0.1 之外的 PDF、Word、国内平台、X、YouTube 真实抓取、评论抽样、多租户或登录态抓取。

## Milestone 1：工程底座与数据层

状态：completed

- [x] 搭建 Docker Compose，支持一条命令启动前端、后端、数据库
- [x] 创建后端应用壳
- [x] 创建前端应用壳
- [x] 添加数据库迁移机制
- [x] 创建 v0.1 核心表结构
- [x] 实现 `Source` CRUD
- [x] 注册 YouTube placeholder `Connector`，只注册接口，不执行真实抓取
- [x] 为核心表添加基础读写测试
- [x] 为 `Source` CRUD 添加测试
- [x] 验证空库可完整初始化

测试标准：

- [x] Docker Compose 一条命令启动前端、后端、数据库
- [x] 迁移可重复执行，空库可完整初始化
- [x] `Source` 能创建、编辑、启停、删除
- [x] 核心表有基础读写测试
- [x] YouTube placeholder 只注册接口，不执行真实抓取

## Milestone 2：连接器与 RawItem 入库

状态：completed

- [x] 实现 RSS `Connector`
- [x] 实现 HN `Connector`
- [x] 实现 GitHub repo watch
- [x] 实现 GitHub release watch
- [x] 实现网页监控 `Connector`
- [x] 统一写入 `RawItem`
- [x] 统一写入 `FetchRun`
- [x] 统一写入 `MetricSnapshot`
- [x] 实现单个 `Source` 失败不影响其他 `Source`

测试标准：

- [x] 3 个真实 RSS 源可解析并去重
- [x] HN top/new/best 可抓取指定数量
- [x] GitHub repo/release 可检测新增 release 和基础指标
- [x] 网页内容不变时不生成重复 `RawItem`，变化时生成 snapshot 和 diff
- [x] 任一 `Source` 失败不影响其他 `Source` 抓取

## Milestone 3：AI 聚类、摘要与 Evidence

状态：completed

- [x] 实现 `EventCandidate`
- [x] 实现候选分桶
- [x] 实现 AI 合并事件
- [x] 实现 AI 摘要生成
- [x] 实现 `Evidence` 引用链路
- [x] 实现 `AiRunLog` 记录
- [x] 实现 AI 调用失败降级

测试标准：

- [x] 多个相似 `RawItem` 能聚合为一个 `EventCluster`
- [x] 不相关 `RawItem` 不应被错误合并
- [x] 每个 AI 摘要至少绑定 1 条 `Evidence`
- [x] AI 调用失败时保留 `RawItem` / `EventCandidate`，并记录 `AiRunLog`
- [x] 事件详情 API 能回溯原始来源链接和引用片段

## Milestone 4：热度评分与雷达 UI

状态：completed

- [x] 实现事件排序
- [x] 实现可解释评分
- [x] 构建雷达列表
- [x] 构建事件详情
- [x] 构建运行日志
- [x] 明确不实现简报导出

测试标准：

- [x] 事件列表支持时间、来源、分数、类型筛选
- [x] UI 空状态、加载中、错误状态完整

## Milestone 5：Markdown 简报导出

状态：completed

- [x] 实现 `BriefTemplate`
- [x] 实现 `BriefExport`
- [x] 实现事件勾选
- [x] 实现人工点评
- [x] 实现 Markdown 预览
- [x] 实现 Markdown 下载
- [x] 内置 AI/科技 与 投资/产业 两个模板

测试标准：

- [x] 可从事件流选择多个 `EventCluster` 生成简报
- [x] Markdown 包含标题、日期、事件摘要、推荐理由、来源引用、人工点评
- [x] 内置 AI/科技 与 投资/产业 两个模板
- [x] 重新编辑点评后可重新生成 Markdown
- [x] 中文内容、长标题、失效链接、空 `Evidence` 都有稳定降级表现
