"""Entry point dell'applicazione FastAPI."""

from fastapi import FastAPI

from price_service.api.health import router as health_router
from price_service.api.v1.router import router as v1_router


def create_app() -> FastAPI:
    app = FastAPI(title="Price Service", version="0.1.0")
    app.include_router(health_router)
    app.include_router(v1_router)
    return app


app = create_app()
