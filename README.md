# HOT

HOT is a private intelligence radar for tracking high-value AI, technology, investment, and industry signals from public sources. It ingests source items, clusters them into events, scores their importance, and exports Markdown briefs with traceable evidence.

## What It Does

- Collects content from RSS feeds, public webpages, Hacker News, GitHub repositories, releases, and supported public social sources.
- Normalizes raw content into event candidates and clusters related items into event groups.
- Uses an OpenAI-compatible model provider for clustering, summarization, translation, scoring, and brief generation.
- Preserves source evidence so every event and brief can be traced back to original links.
- Provides a Next.js dashboard for feeds, sources, runs, briefs, reports, industry views, agents, team workflows, and settings.
- Supports local SQLite development and Docker Compose deployments with PostgreSQL.

## Repository Structure

```text
backend/    FastAPI application, SQLAlchemy models, Alembic migrations, connectors, services, tests
frontend/   Next.js application, dashboard pages, UI components, API helpers
docs/       Product scope, deployment notes, roadmap, and architecture decisions
scripts/    Local development helpers
tasks/      Milestone planning documents
```

## Tech Stack

- Backend: Python 3.12, FastAPI, SQLAlchemy, Alembic, Pydantic, Uvicorn
- Frontend: Next.js 15, React 19, TypeScript, lucide-react
- Database: SQLite for local preview, PostgreSQL 16 for Docker and production
- Deployment: Docker Compose, optional Caddy production reverse proxy

## Local Development

Copy the environment template first:

```powershell
Copy-Item ".env.example" ".env"
```

For Windows local development with SQLite:

```powershell
.\scripts\dev-sqlite.ps1
```

The script:

- loads local environment values from `.env`
- forces `DATABASE_URL` to `backend/dev-preview.db`
- runs Alembic migrations
- starts the backend at `http://127.0.0.1:8000`
- starts the frontend at `http://127.0.0.1:3000`

## Docker Development

```powershell
Copy-Item ".env.example" ".env"
docker compose up --build
```

Default local services:

- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000`
- PostgreSQL: `localhost:5432`

## Configuration

Important environment variables are defined in `.env.example`.

Required for AI-assisted clustering and summaries:

```text
AI_PROVIDER=openai_compatible
AI_MODEL=deepseek-v4-flash
AI_API_KEY=
AI_BASE_URL=https://api.deepseek.com
```

Optional credentials can improve source reliability or unlock authorized platform integrations:

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

Do not commit real secrets.

## Common Commands

Backend tests:

```powershell
cd backend
pytest
```

Frontend type check:

```powershell
cd frontend
npm run typecheck
```

Frontend production build:

```powershell
cd frontend
npm run build
```

## Production Deployment

Production deployment notes are in `docs/deployment-production.md`. The production Compose setup uses:

- Caddy as the public HTTPS entrypoint with Basic Auth
- Next.js frontend
- FastAPI backend
- PostgreSQL 16 with a persistent Docker volume

Start production services with:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml up -d --build
```

## Documentation

- `docs/development.md`: local development workflow
- `docs/deployment-production.md`: VPS deployment workflow
- `docs/roadmap/`: milestone and future roadmap notes
- `docs/decisions/`: architecture decision records

