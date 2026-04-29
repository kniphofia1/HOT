# 本地开发运行说明

## 默认数据库

本地手动开发默认使用 SQLite 文件：

```text
backend/dev-preview.db
```

后端在没有显式 `DATABASE_URL` 环境变量时，会自动连接这个文件。普通重启后端不会清空数据。

## 推荐启动方式

Windows 本地开发使用：

```powershell
.\scripts\dev-sqlite.ps1
```

脚本会执行：

1. 读取 `.env` 中的 AI、GitHub、Reddit 等运行配置
2. 强制设置 `DATABASE_URL=sqlite:///.../backend/dev-preview.db`
3. 执行 `alembic upgrade head`
4. 启动后端 `http://127.0.0.1:8000`
5. 启动前端 `http://127.0.0.1:3000`

## 数据不会保留的常见原因

- 换用了另一个 `DATABASE_URL`，例如连到了本机 PostgreSQL 或 Docker PostgreSQL。
- 删除了 `backend/dev-preview.db`。
- 使用 Docker Compose 时执行了 `docker compose down -v`，这会删除 PostgreSQL volume。

## 刷新链路

首页“刷新情报”和信源页“立即刷新”都会执行完整链路：

```text
Source fetch -> RawItem -> EventCandidate -> EventCluster -> Evidence -> editorial -> scoring
```

如果 AI provider 未配置或调用失败，`RawItem` 和 `EventCandidate` 会保留，失败信息会写入 `AiRunLog`。
