from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from server.config import Settings
from server.routers import control, pages, sessions, system, websockets
from server.services.container import AppServices


STATIC_DIR = Path(__file__).resolve().parent / "static"


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or Settings.from_env()
    services = AppServices.build(resolved_settings)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        resolved_settings.validate()
        try:
            yield
        finally:
            await services.hub.shutdown()

    application = FastAPI(
        title="Raspberry Pi Robot Control",
        version="2.0.0",
        lifespan=lifespan,
    )
    application.state.services = services
    application.mount("/assets", StaticFiles(directory=STATIC_DIR), name="assets")

    @application.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        return response

    @application.exception_handler(RuntimeError)
    async def runtime_error_handler(request: Request, exc: RuntimeError) -> JSONResponse:
        return JSONResponse(status_code=500, content={"detail": str(exc)})

    application.include_router(pages.router)
    application.include_router(system.router)
    application.include_router(sessions.router)
    application.include_router(control.router)
    application.include_router(websockets.router)
    return application


app = create_app()
hub = app.state.services.hub
