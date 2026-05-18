# 生产部署：VPS Docker Compose

本文档用于把研究员情报雷达部署成完全私有的网站。第一版上线目标是自动抓取、自动生成 Markdown 日报和行业日报，并通过 Basic Auth 保护整站。

## 部署形态

- `caddy`：唯一公网入口，监听 80/443，自动签发 HTTPS 证书，并对整站启用 Basic Auth。
- `frontend`：Next.js 生产构建，提供情报流、日报、行业日报、简报和设置页面。
- `backend`：FastAPI，执行迁移、Connector 抓取、聚类、评分、自动化任务和 Markdown 下载。
- `db`：PostgreSQL 16，使用 Docker volume 持久化。

公网只暴露 Caddy。后端和数据库不发布宿主机端口，前端页面内的 `/api/*` 请求由 Caddy 反向代理到后端。

## 准备 VPS

1. 安装 Docker Engine 和 Docker Compose Plugin。
2. 将域名 A 记录指向 VPS 公网 IP。
3. 放行 80 和 443 端口。
4. 拉取或上传仓库代码到 VPS，例如 `/opt/hot-radar`。

## 配置环境变量

在 VPS 上创建生产环境文件：

```bash
cp .env.example .env.production
chmod 600 .env.production
```

至少填写：

```text
POSTGRES_PASSWORD=replace-with-a-strong-database-password
SITE_DOMAIN=radar.example.com
BASIC_AUTH_USER=admin
BASIC_AUTH_HASH=replace-with-caddy-hash
AI_PROVIDER=openai_compatible
AI_MODEL=deepseek-v4-flash
AI_API_KEY=replace-with-real-key
AI_BASE_URL=https://api.deepseek.com
```

生成 Basic Auth 密码哈希：

```bash
docker run --rm caddy:2-alpine caddy hash-password --plaintext "replace-with-a-strong-password"
```

把输出完整写入 `BASIC_AUTH_HASH`。真实 API Key、Token 和密码只放在 `.env.production`，不要提交到仓库。

`BASIC_AUTH_HASH` 必须用单引号包住，因为 Caddy 生成的 bcrypt 哈希包含 `$`，否则 Docker Compose 会把 `$...` 当成变量插值：

```text
BASIC_AUTH_HASH='$2a$14$example'
```

可选平台凭证：

```text
GITHUB_TOKEN=
REDDIT_CLIENT_ID=
REDDIT_CLIENT_SECRET=
X_BEARER_TOKEN=
YOUTUBE_API_KEY=
LINKEDIN_ACCESS_TOKEN=
TIKTOK_RESEARCH_ACCESS_TOKEN=
TELEGRAM_BOT_TOKEN=
DISCORD_BOT_TOKEN=
SLACK_BOT_TOKEN=
```

缺少凭证的平台信源会被自动任务跳过或记录失败，不会回退到 Cookie、登录态、验证码或私有页面抓取。

## 启动与升级

首次启动：

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml up -d --build
```

查看状态：

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml ps
docker compose --env-file .env.production -f docker-compose.prod.yml logs -f backend
```

升级代码后：

```bash
git pull
docker compose --env-file .env.production -f docker-compose.prod.yml up -d --build
```

后端容器启动时会执行：

```text
alembic upgrade head
```

## 验收

1. 打开 `https://你的域名`，确认未认证时无法访问。
2. 登录后进入 `/settings`，确认自动化运行已启用。
3. 点击“立即运行”，确认 `source_refresh` 和 `daily_reports` 有运行记录。
4. 打开 `/daily`，确认能看到最新日报。
5. 打开 `/industry`，确认有行业日报索引。
6. 在简报详情页下载 Markdown，确认接口走同域名 `/api/briefs/exports/{id}/download`。

## 自动化说明

默认任务：

- `source_refresh`：默认每 5 分钟检查到期信源，执行抓取、聚类、编辑和评分。
- `daily_reports`：默认每天 `08:30` 生成全局日报和行业日报。

可以在 `/settings` 修改：

- 是否启用定时抓取。
- 是否启用每日报告。
- 日报时间和时区。
- 全局事件上限。
- 行业事件上限。

第一版不自动生成自然周周报。

## 备份与恢复

数据库备份：

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml exec -T db \
  sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' > hot-radar-backup.sql
```

数据库恢复前建议先停止应用容器：

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml stop backend frontend caddy
cat hot-radar-backup.sql | docker compose --env-file .env.production -f docker-compose.prod.yml exec -T db \
  sh -c 'psql -U "$POSTGRES_USER" "$POSTGRES_DB"'
docker compose --env-file .env.production -f docker-compose.prod.yml up -d
```

也可以在 `/settings` 下载应用级 JSON 备份，用于小规模迁移和人工恢复。

## 排查

- HTTPS 不生效：检查 DNS 是否指向 VPS，80/443 是否放行，Caddy 日志是否有 ACME 错误。
- 日报为空：先确认信源已启用且抓取成功，再检查 AI provider 和 `AiRunLog`。
- 凭证平台无数据：检查对应环境变量是否存在，平台权限是否通过审核，`FetchRun` 是否记录 401、403 或 429。
- 下载链接不可用：确认 `SITE_DOMAIN` 正确，Caddy 的 `/api/*` 反代能到 `backend:8000`。
