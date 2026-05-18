from fastapi import FastAPI

from app.api.routes import (
    automation,
    agents,
    briefs,
    clusters,
    connectors,
    domestic_platforms,
    feedback,
    health,
    items,
    maintenance,
    public,
    reports,
    runs,
    saas,
    source_market,
    sources,
    team,
)
from app.services.automation_scheduler import start_automation_scheduler, stop_automation_scheduler


def create_app() -> FastAPI:
    app = FastAPI(title="Researcher Intelligence Radar")

    async def _startup() -> None:
        start_automation_scheduler(app)

    async def _shutdown() -> None:
        await stop_automation_scheduler(app)

    app.router.on_startup.append(_startup)
    app.router.on_shutdown.append(_shutdown)
    app.include_router(agents.router)
    app.include_router(automation.router)
    app.include_router(briefs.router)
    app.include_router(health.router)
    app.include_router(clusters.router)
    app.include_router(connectors.router)
    app.include_router(domestic_platforms.router)
    app.include_router(feedback.router)
    app.include_router(items.router)
    app.include_router(maintenance.router)
    app.include_router(public.router)
    app.include_router(reports.router)
    app.include_router(runs.router)
    app.include_router(saas.router)
    app.include_router(source_market.router)
    app.include_router(sources.router)
    app.include_router(team.router)
    return app


app = create_app()
