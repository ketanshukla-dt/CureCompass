"""
CureCompass — Intelligent Incident Remediation Platform
=======================================================
Monolith entry point: FastAPI serves both the REST API
and the pre-built React frontend as static files.

Start: python main.py
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api import database
from api.config import get_settings
from routes.history import router as history_router
from routes.incidents import router as incidents_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("curecompass")

STATIC_DIR = Path(__file__).resolve().parent / "static"


def _mode_label() -> str:
    settings = get_settings()
    return "SIMULATION" if settings.simulation_mode else "LIVE"


@asynccontextmanager
async def lifespan(app: FastAPI):
    await database.init_db()
    settings = get_settings()
    logger.info(
        "Started: mode=%s dynatrace=%s llm_provider=%s",
        _mode_label(),
        "live" if settings.dynatrace_is_live else "mock",
        settings.llm_provider,
    )
    logger.info("Open http://%s:%s", settings.host, settings.port)
    yield


app = FastAPI(
    title="CureCompass — Incident Remediation Platform",
    description="AI-powered remediation guidance built on top of Davis AI",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origin_list,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

app.include_router(incidents_router)
app.include_router(history_router)


@app.get("/healthz", tags=["health"])
async def healthz():
    """Liveness/readiness probe: reports mode and configured providers, never secrets."""
    settings = get_settings()
    return {
        "status": "ok",
        "mode": _mode_label(),
        "dynatrace": "live" if settings.dynatrace_is_live else "mock",
        "llm_provider": settings.llm_provider,
    }


# Serve the React frontend (built static files)
if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_frontend(full_path: str):
        # Unknown /api/* paths should 404 as JSON, not return the SPA shell
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")
        return FileResponse(STATIC_DIR / "index.html")
else:

    @app.get("/", include_in_schema=False)
    async def no_frontend():
        return {
            "message": "Frontend not built yet. Run: cd frontend && npm install && npm run build",
            "api_docs": "/docs",
        }


if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run("main:app", host=settings.host, port=settings.port, reload=False)
