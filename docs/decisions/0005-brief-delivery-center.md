# ADR 0005：商业简报与交付中心

## 状态

Accepted

## 背景

终局 Milestone 6 要把事件流转化为可交付成果，包括 AI 技术日报、投资观察、竞争情报、行业周报、风险预警和项目尽调材料。
交付格式会从 Markdown 扩展到 Word/PDF，以及邮件、飞书、Notion、Slack 等渠道。

## 决策

当前实现以本地可验证交付为核心：

- Markdown 仍是主格式。
- 新增 Word `.docx` 下载和打印友好 HTML 下载。
- PDF 暂不直接生成二进制文件，先通过打印 HTML 作为稳定过渡路径。
- 邮件、飞书、Notion、Slack 不在无凭证时主动发送，只创建 `BriefDelivery` outbox 记录并标记为 `requires_configuration`。
- 每条简报判断必须保留事件智能理由、评分理由和 Evidence 来源引用。

## 边界

允许：

- 本地下载 Markdown、DOCX、打印 HTML。
- 创建外部交付计划和 payload。
- 后续在凭证、权限、限流和审计完成后接入真实发送器。

禁止：

- 无凭证发送外部消息。
- 在日志或数据库中保存明文 token。
- 生成无法追溯来源引用的商业判断。
