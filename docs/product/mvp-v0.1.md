# MVP v0.1：研究员情报雷达

## Summary

v0.1 聚焦本地单机闭环：

```text
RSS / 指定网页 / Hacker News / GitHub repo + release watch
-> 统一入库
-> AI 聚类与摘要
-> 来源引用
-> 人工选择
-> Markdown 简报导出
```

不实现：国内平台、X、PDF、Word、评论抽样、多租户、复杂权限、网页截图、登录态抓取。YouTube 只预留 `Connector` 接口，不做实际抓取。

## v0.1 数据模型

- `Source`：信源配置，包含 `type`, `name`, `url`, `enabled`, `weight`, `pollIntervalMinutes`, `configJson`, `lastFetchedAt`, `lastError`
- `RawItem`：连接器抓到的原始内容，包含 `sourceId`, `externalId`, `sourceUrl`, `title`, `contentText`, `author`, `publishedAt`, `fetchedAt`, `rawPayloadJson`, `contentHash`
- `FetchRun`：每次抓取记录，包含 `sourceId`, `status`, `itemsFound`, `itemsCreated`, `errorMessage`, `rateLimitRemaining`, `costEstimate`
- `WebMonitorTarget`：网页监控配置，包含 `url`, `cssSelector`, `extractionMode`, `lastContentHash`, `lastChangedAt`
- `WebpageSnapshot`：网页快照，包含 `targetId`, `textContent`, `contentHash`, `diffSummary`, `capturedAt`
- `EventCandidate`：聚类前候选，包含 `rawItemId`, `normalizedTitle`, `canonicalUrl`, `keywordsJson`, `candidateHash`
- `EventCluster`：聚类后事件，包含 `title`, `summary`, `translatedTitle`, `translatedSummary`, `translatedAt`, `hotScore`, `scoreReasonJson`, `confidence`, `firstSeenAt`, `lastSeenAt`
- `Evidence`：事件引用证据，包含 `eventClusterId`, `rawItemId`, `sourceName`, `sourceUrl`, `quote`, `confidence`
- `MetricSnapshot`：指标时间序列，覆盖 HN score/comments、GitHub stars/forks/open issues/release downloads
- `AiRunLog`：AI 聚类、摘要与事件翻译调用记录，包含 `taskType`, `inputHash`, `model`, `status`, `tokenEstimate`, `errorMessage`
- `BriefTemplate`：Markdown 简报模板，内置 `ai_tech` 与 `investment`
- `BriefExport`：简报导出记录，包含 `templateId`, `title`, `eventClusterIdsJson`, `manualNotesJson`, `markdown`, `generatedAt`

## 后端模块划分

- `connectors/core`：统一连接器接口、能力声明、限流元数据、错误分类；YouTube 只注册 placeholder
- `connectors/rss`：解析 RSS、Atom、JSON Feed
- `connectors/webpage`：公开网页拉取、CSS Selector 文本抽取、快照与 diff
- `connectors/hackerNews`：HN top/new/best/show/item 抓取与指标记录
- `connectors/github`：repo 指标与 release watch
- `scheduler`：按 `Source` 刷新频率调度，支持手动刷新，写入 `FetchRun`
- `ingestion`：`RawItem` 标准化、URL canonicalize、`contentHash` 去重、生成 `EventCandidate`
- `clustering`：候选分桶、AI 合并事件、AI 摘要、`Evidence` 绑定、`AiRunLog` 记录
- `translation`：将已聚类事件的标题和摘要翻译为简体中文，写入 `EventCluster` 翻译缓存；失败时保留原文并记录 `AiRunLog`
- `scoring`：计算可解释 `hotScore = recency + sourceWeight + mentionCount + velocity + aiImportance`
- `briefExporter`：基于 `EventCluster`、`Evidence`、人工点评和模板生成 Markdown
- `api`：`Source` CRUD、手动刷新、事件列表/详情、事件翻译、运行日志、简报创建/预览/下载

## 前端页面划分

- `Radar / 情报雷达`：`EventCluster` 流、筛选、分数、推荐理由、证据数量，优先展示中文翻译标题和摘要
- `Event Detail / 事件详情`：聚类内 `RawItem`、来源引用、指标变化、AI 摘要、中文翻译展示、人工备注
- `Sources / 信源管理`：按类型卡片配置 RSS、公开网页、HN、GitHub repo/release 和热榜规划入口，支持新增、启停、刷新、删除和错误查看
- `Web Watch / 网页监控`：URL、CSS Selector、刷新频率、快照历史、diff 摘要
- `GitHub Watch`：repo/release watch、latest release、指标趋势
- `Runs / 运行日志`：`FetchRun` 与 `AiRunLog` 查询
- `Briefs / 简报`：勾选事件、选择模板、编辑点评、预览/下载 Markdown
- `Settings / 设置`：AI provider、API Key、GitHub token、默认刷新频率、数据保留天数

## 实现里程碑

### Milestone 1：工程底座与数据层

实现 Docker Compose、前后端壳、数据库迁移、核心表结构、`Source` CRUD。

测试标准：

- Docker Compose 一条命令启动前端、后端、数据库
- 迁移可重复执行，空库可完整初始化
- `Source` 能创建、编辑、启停、删除
- 核心表有基础读写测试
- YouTube placeholder 只注册接口，不执行真实抓取

### Milestone 2：连接器与 RawItem 入库

实现 RSS、HN、GitHub、网页监控连接器，并统一写入 `RawItem`、`FetchRun`、`MetricSnapshot`。

测试标准：

- 3 个真实 RSS 源可解析并去重
- HN top/new/best 可抓取指定数量
- GitHub repo/release 可检测新增 release 和基础指标
- 网页内容不变时不生成重复 `RawItem`，变化时生成 snapshot 和 diff
- 任一 `Source` 失败不影响其他 `Source` 抓取

### Milestone 3：AI 聚类、摘要与 Evidence

实现 `EventCandidate`、候选分桶、AI 合并、摘要生成、`Evidence` 引用链路。

测试标准：

- 多个相似 `RawItem` 能聚合为一个 `EventCluster`
- 不相关 `RawItem` 不应被错误合并
- 每个 AI 摘要至少绑定 1 条 `Evidence`
- AI 调用失败时保留 `RawItem` / `EventCandidate`，并记录 `AiRunLog`
- 事件详情页能回溯原始来源链接和引用片段

### Milestone 4：热度评分与雷达 UI

只实现事件排序、可解释评分、雷达列表、事件详情和运行日志，不实现简报导出。

测试标准：

- 事件列表支持时间、来源、分数、类型筛选
- UI 空状态、加载中、错误状态完整

### Milestone 5：Markdown 简报导出

单独实现 `BriefTemplate`、`BriefExport`、事件勾选、人工点评、Markdown 预览与下载。

测试标准：

- 可从事件流选择多个 `EventCluster` 生成简报
- Markdown 包含标题、日期、事件摘要、推荐理由、来源引用、人工点评
- 内置 AI/科技 与 投资/产业 两个模板
- 重新编辑点评后可重新生成 Markdown
- 中文内容、长标题、失效链接、空 `Evidence` 都有稳定降级表现

## Assumptions

- v0.1 必须配置 AI provider 才启用聚类与摘要；未配置时显示明确错误
- 网页监控只支持公开网页，不处理登录、验证码、Cookie、截图和 JS 重渲染
- Markdown 是唯一交付格式，PDF/Word 放到后续版本
- 产品优先级固定为：可信来源链路 > 聚类质量 > 简报质量 > 热度评分 > 平台数量
