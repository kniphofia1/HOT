# 当前任务：终局 Milestone 后续路线

## 执行限制

v0.1 已完成并归档。当前实现工作进入 `docs/roadmap/final-milestones.md` 描述的后续路线。

后续路线允许实现：

- 主流国际平台官方 Connector：X、YouTube、LinkedIn、TikTok、Telegram、Discord、Slack。
- 国内平台合规矩阵与人工链接补录。
- 事件智能层 2.0。
- 商业简报与本地交付中心。
- 本地团队协作对象。
- SaaS 控制平面数据对象。
- Agent 情报官。

## 开工前必须阅读

实现前必须阅读：

- `AGENTS.md`
- `docs/product/mvp-v0.1.md`
- `docs/roadmap/milestones.md`
- `docs/roadmap/final-milestones.md`
- `docs/decisions/0001-mvp-scope.md`
- `docs/decisions/0002-public-social-sources.md`
- `docs/decisions/0003-international-platform-connectors.md`
- `docs/decisions/0004-domestic-platform-compliance.md`
- `docs/decisions/0005-brief-delivery-center.md`
- `docs/decisions/0006-local-team-collaboration.md`
- `docs/decisions/0007-saas-control-plane.md`
- `docs/decisions/0008-agent-intelligence-officer.md`
- `docs/decisions/0010-private-vps-deployment.md`
- 本文件 `tasks/final-milestones.md`

## 合规边界

允许：

- 官方 API、公开 API、公开网页、公开协议、用户授权、Bot/Webhook 和人工链接补录。
- 缺少凭证时记录失败或标记 `requires_configuration`。
- 本地可验证的数据模型、API、UI 和测试。
- Word `.docx` 下载与打印友好 HTML。

禁止：

- Cookie 抓取。
- 登录态模拟。
- 验证码处理。
- 私有页面抓取。
- 反爬绕过。
- 未配置凭证时主动发送外部消息。
- 保存明文 API Key、Token 或支付凭证。
- 无 Evidence 的商业判断。

## 当前完成状态

- [x] Milestone 0：v0.1 本地情报雷达。
- [x] Milestone 1：本地稳定版。
- [x] Milestone 2：信源市场与平台能力矩阵。
- [x] Milestone 3：主流国际平台自动化。
- [x] Milestone 4：国内平台合规接入。
- [x] Milestone 5：事件智能层 2.0。
- [x] Milestone 6：商业简报与交付中心。
- [x] Milestone 7：团队协作版。
- [x] Milestone 8：SaaS 商业化版。
- [x] Milestone 9：自动 Agent 情报官。

## 当前收口任务

- [x] 将 v0.1 路线文档标记为归档范围，避免与后续路线冲突。
- [x] 修复国际平台 Connector 的 Unix 时间戳转换，确保 Telegram 和 TikTok 入库时保留 `publishedAt`。
- [x] 为 Telegram 和 TikTok Connector 增加发布时间断言。
- [x] 新增私有 VPS 生产部署方案，使用 Caddy、Basic Auth 和 Docker Compose。
- [x] 将自动报告第一版收口为全局日报与行业日报，不扩展自然周周报。
- [x] 补齐生产环境变量样例和部署/备份/恢复文档。

## 验收标准

- 后续路线文档、ADR 和当前任务文档能够解释为什么可以继续实现终局能力。
- 新增平台能力仍然走 `Connector -> RawItem -> FetchRun -> MetricSnapshot -> EventCluster -> Evidence` 链路。
- 缺少凭证、限流、权限错误都有明确失败记录。
- 国内平台不做 Cookie、登录态、验证码或私有页面抓取。
- Agent 只扫描本地 `EventCluster` 和 Evidence，不额外抓取平台。
- 后端测试和前端类型检查通过。
