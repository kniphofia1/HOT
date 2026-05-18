# ADR 0009：价值密度优先的 hotScore

## Status

Accepted

## Context

旧评分模型主要由 `recency`、`sourceWeight`、`mentionCount`、`velocity` 和 `aiImportance` 线性叠加。它能找到“新”和“多次出现”的内容，但容易把泛泛讨论、单条社交噪声和短文本误判为高价值信息。

研究员情报雷达的目标不是普通 RSS 阅读器，而是把可信来源转化为可追溯、可解释、可交付的情报事件。因此 `hotScore` 应该优先回答：这条信息是否具体、是否可跟进、是否对产业/产品/技术判断有价值、是否有可靠证据链。

## Decision

`hotScore` 改为价值密度模型：

```text
hotScore =
  signalQuality
  + actionability
  + strategicImpact
  + sourceCredibility
  + propagationMomentum
  + freshness
  - qualityPenalty
```

各维度职责：

- `signalQuality`：标题、正文、实体、数字、版本、价格、API、仓库等具体事实。
- `actionability`：发布、开源、定价、API、SDK、论文、融资、监管、教程等可直接跟进的信息。
- `strategicImpact`：重点公司、产业链、平台、算力、资本、政策风险等判断价值。
- `sourceCredibility`：高权重来源、多来源交叉验证、事件可信度。
- `propagationMomentum`：短时间内多证据或跨来源扩散。
- `freshness`：新近程度，保留但降低主导性。
- `qualityPenalty`：短文本、泛泛讨论、个人学习徽章/成就类社交动态、单一社交信号、缺少实体/领域/行动线索、过旧非长尾内容。

公开精选流不再因为 `editorialPriority > 0` 直接入选；需要 `hotScore >= 60`，或 `hotScore >= 50` 且 `editorialPriority >= 70`。

## Consequences

- 具体的产品发布、模型能力变化、开发者工具、论文、融资、监管和安全事件会更容易上榜。
- 单条新鲜但信息密度低的社交讨论会被压低。
- 评分理由仍写入 `scoreReasonJson`，前端和 Markdown 简报可以继续解释推荐依据。
- 新模型依赖 `EventIntelligence` 的实体、领域、可信度和传播特征，因此重算评分前必须先刷新事件智能字段。
