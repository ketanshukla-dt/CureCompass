"""
FixIQ — Intelligent Incident Remediation Platform
===================================================
Monolith entry point: FastAPI serves both the REST API
and the pre-built React frontend as static files.

Start: python main.py
"""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pathlib import Path
import uvicorn
import logging

# Show INFO-level logs in the console (so we can see DT connection details)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

from api import database
from api.config import get_settings
from routes.incidents import router as incidents_router
from routes.history import router as history_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await database.init_db()
    settings = get_settings()
    mode = "SIMULATION" if settings.simulation_mode or not settings.dt_api_token else "LIVE DYNATRACE"
    print(f"\n[FixIQ] Started - Mode: {mode}")
    print(f"   Open: http://localhost:{settings.port}\n")
    yield


app = FastAPI(
    title="FixIQ — Incident Remediation Platform",
    description="AI-powered remediation guidance built on top of Davis AI + Claude",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(incidents_router)
app.include_router(history_router)

# Serve React frontend (built static files)
STATIC_DIR = Path("static")
if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_frontend(full_path: str):
        # Unknown /api/* paths should 404 as JSON, not return the SPA shell
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")
        # All other routes → React SPA
        index = STATIC_DIR / "index.html"
        return FileResponse(str(index))
else:
    @app.get("/", include_in_schema=False)
    async def no_frontend():
        return {
            "message": "Frontend not built yet. Run: cd frontend && npm install && npm run build",
            "api_docs": "/docs"
        }


if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run("main:app", host="0.0.0.0", port=settings.port, reload=False)
