# 项目协作规则

## 产品定位

本仓库的长期产品是 **研究员情报雷达**。

它不是普通 RSS 阅读器，而是一个本地优先的研究工具，用来把可信来源转化为可追溯、可聚类、可解释、可导出的情报事件和 Markdown 简报。

核心价值按优先级排序：

1. 可信来源链路
2. 可回溯的原始证据
3. AI 辅助聚类与摘要
4. 可解释的事件评分
5. 可交付的 Markdown 简报

## 每次开工前必须阅读

任何实现工作开始前，必须先阅读这些文档：

- `docs/product/mvp-v0.1.md`
- `docs/roadmap/milestones.md`
- `docs/decisions/0001-mvp-scope.md`
- 当前任务文档，例如 `tasks/milestone-1.md`

不得只依赖聊天记录或记忆开工。仓库文档是当前范围与协作规则的唯一事实来源。

## v0.1 当前范围

v0.1 只做本地单机闭环：

```text
RSS / 公开网页监控 / Hacker News / GitHub repo + release watch
-> RawItem 入库
-> AI 聚类与摘要
-> Evidence 来源引用
-> 可解释 hotScore
-> 人工选择事件
-> Markdown 简报导出
```

v0.1 只面向本地单用户使用，不做 SaaS、多用户、团队协作或客户登录。

## v0.1 明确禁止提前实现

在项目范围被正式更新前，不得实现以下内容：

- 国内平台 Connector，包括微博、B站、知乎、微信公众号、小红书、抖音、快手等
- X / Twitter 真实数据 Connector
- PDF 导出
- Word / DOCX 导出
- 评论抽样
- 全量评论舆情或情感分析
- 多租户
- 团队账号、角色、权限、客户登录
- 登录态抓取
- Cookie 抓取
- 验证码处理
- 私有页面抓取
- YouTube 真实抓取
- 浏览器插件
- 移动端 App
- 复杂通知渠道

YouTube 在 v0.1 中只能作为 `youtube_placeholder` 或 `Connector` 接口占位存在，不得发起真实 API 请求，不得做真实网页抓取。

## 命名规则

文档可以使用中文说明，但代码命名、数据库表名、字段名、API 路由仍然使用英文。

必须保留并统一使用以下核心概念名：

- `Connector`
- `Source`
- `RawItem`
- `FetchRun`
- `EventCandidate`
- `EventCluster`
- `Evidence`
- `MetricSnapshot`
- `AiRunLog`
- `BriefTemplate`
- `BriefExport`
- `Milestone`

## 实现原则

- `Connector` 逻辑必须隔离在统一接口后面。
- 所有抓取结果必须先进入 `RawItem`，再做标准化、聚类、摘要。
- 每次抓取必须记录 `FetchRun`。
- 每条 AI 摘要必须能通过 `Evidence` 回溯到来源。
- `hotScore` 必须可解释，不允许只有黑箱分数。
- v0.1 只允许 Markdown 导出。
- 不为了未来平台提前堆抽象，除非当前 `Milestone` 明确需要。
- 不得混做 `Milestone`。只能执行 `docs/roadmap/milestones.md` 中标记为 allowed 的 `Milestone`。

## 安全与合规

- 只使用官方 API、RSS、公开 API 或公开网页。
- 不绕过平台访问控制。
- 不保存用户 Cookie 用于抓取。
- 不实现需要登录、反爬绕过、验证码破解的抓取行为。
- API Key、Token 等凭证必须视为密钥，不得提交到仓库。

## 文档维护规则

- 如果范围变化，先更新 `docs/product/mvp-v0.1.md`、`docs/roadmap/milestones.md` 和对应 ADR，再实现代码。
- 如果完成某个 `Milestone` 的任务，必须更新 `docs/roadmap/milestones.md` 的 checklist。
- 如果做出新的重大产品或架构决策，必须在 `docs/decisions/` 下新增 ADR。
