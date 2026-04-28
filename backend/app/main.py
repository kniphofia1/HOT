from fastapi import FastAPI

from app.api.routes import clusters, connectors, health, items, runs, sources


def create_app() -> FastAPI:
    app = FastAPI(title="Researcher Intelligence Radar")
    app.include_router(health.router)
    app.include_router(clusters.router)
    app.include_router(connectors.router)
    app.include_router(items.router)
    app.include_router(runs.router)
    app.include_router(sources.router)
    return app


app = create_app()
