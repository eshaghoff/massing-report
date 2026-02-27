from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import settings
from app.api.routes import router
from app.api.reports_saas import router as reports_saas_router
from app.api.billing import router as billing_router
from app.api.lots import router as lots_router

app = FastAPI(
    title="NYC Zoning Feasibility Engine",
    description=(
        "Analyze NYC lots for development potential. "
        "Enter an address to get zoning data, FAR calculations, "
        "building scenarios, and 3D massing diagrams."
    ),
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins + ["http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Core zoning engine routes
app.include_router(router)

# SaaS routes (auth-protected)
app.include_router(reports_saas_router)
app.include_router(billing_router)
app.include_router(lots_router)

# Serve massing-viewer (Three.js) built files
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "frontend")
MASSING_VIEWER_DIR = os.path.join(FRONTEND_DIR, "massing-viewer", "dist")
if os.path.isdir(MASSING_VIEWER_DIR):
    app.mount("/massing-viewer", StaticFiles(directory=MASSING_VIEWER_DIR, html=True),
              name="massing-viewer")

# Serve frontend static files
if os.path.isdir(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/")
async def root():
    """Serve the web UI if available, otherwise return API info."""
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.isfile(index_path):
        return FileResponse(index_path)
    return {
        "name": "NYC Zoning Feasibility Engine",
        "version": "2.0.0",
        "endpoints": {
            "web_ui": "/",
            "api_docs": "/docs",
            "health": "/health",
            "full_analysis": "POST /api/v1/full-analysis",
            "lookup": "GET /api/lookup?address=...",
            "report": "POST /api/report",
            "saas_preview": "POST /api/v1/saas/reports/preview",
            "saas_generate": "POST /api/v1/saas/reports/generate",
            "saas_reports": "GET /api/v1/saas/reports/",
            "saas_checkout": "POST /api/v1/saas/billing/checkout",
            "saas_subscribe": "POST /api/v1/saas/billing/subscribe",
        },
    }


@app.get("/health")
async def health():
    """Health check with dependency status."""
    status = {"status": "healthy", "version": "2.0.0"}

    # Check Redis
    try:
        from app.services.cache import get_redis
        r = await get_redis()
        if r:
            await r.ping()
            status["redis"] = "connected"
        else:
            status["redis"] = "not configured"
    except Exception as e:
        status["redis"] = f"error: {e}"

    return status
