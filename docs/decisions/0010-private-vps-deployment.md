# ADR 0010：私有 VPS 上线收口

## 状态

Accepted

## 背景

当前系统已经具备自动信源刷新、事件聚类、Evidence、可解释评分、Markdown 简报、日报和行业日报页面。下一步目标不是继续扩大平台范围，而是把现有能力部署成可长期运行的私有网站。

用户选择的上线形态是“完全私有”，部署方式是 VPS Docker Compose，自动报告第一版只覆盖日报和行业日报。

## 决策

- 使用独立 `docker-compose.prod.yml` 启动生产服务。
- 使用 Caddy 作为唯一公网入口，负责 HTTPS、gzip/zstd 压缩、Basic Auth 和 `/api/*` 反向代理。
- 后端、前端和数据库只在 Docker 网络内通信，不发布后端和数据库宿主机端口。
- 使用 Basic Auth 保护整站，不在本阶段实现多用户账号、角色权限或 SaaS 租户系统。
- 自动化任务保留 `source_refresh` 和 `daily_reports`；第一版不自动生成自然周周报。
- 生产密钥只放在 VPS 环境文件中，仓库只维护示例变量和部署文档。

## 边界

允许：

- 私有站点 Basic Auth。
- VPS 上的 Postgres volume 持久化。
- Markdown 日报、行业日报和手动简报下载。
- 官方 API、公开 API、Bot/Webhook 和用户授权凭证。

不允许：

- Cookie 抓取。
- 登录态模拟。
- 验证码处理。
- 私有页面抓取。
- 反爬绕过。
- 在仓库中提交真实 API Key、Token、数据库密码或 Basic Auth 密码。
- 将本阶段扩展为多租户 SaaS 或团队权限系统。

## 影响

- 当前产品可以作为个人或小范围私有情报站长期运行。
- 部署复杂度集中在 Docker Compose、Caddy 和环境变量，应用层保持简单。
- 后续如果要开放给多人或客户，需要新增认证、权限、审计和租户隔离方案，不能复用 Basic Auth 当作商业账号体系。
