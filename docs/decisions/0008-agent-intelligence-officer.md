# ADR 0008：自动 Agent 情报官

## 状态

Accepted

## 背景

Milestone 9 要从用户手动查情报升级为系统主动发现异常、生成预警并建议跟进问题。
当前系统已经具备 EventCluster、事件智能字段、团队/SaaS 控制平面和简报交付能力，可以在此基础上增加本地 Agent。

## 决策

新增本地 Agent 情报官：

- `IntelligenceAgent`：主题、公司、竞品、投资赛道、风险等代理配置。
- `AgentAlert`：由 Agent 生成的系统内预警。
- `AgentRunLog`：每次扫描记录。

Agent 只扫描本地 `EventCluster` 和 Evidence，不额外抓取平台，不绕过任何访问控制。
外部通知留给交付/通知渠道具备凭证后接入。

## 影响

- 用户可以少做手动刷新后的逐条筛选。
- 系统能解释为什么某个事件值得关注，并给出跟进问题。
- Agent 逻辑可测试、可审计、可回溯到 EventCluster 和 Evidence。
