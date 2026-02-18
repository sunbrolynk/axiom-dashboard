"""
Application factory — assembles the FastAPI app from its parts.

This is the entrypoint uvicorn loads:
    uvicorn backend.main:app
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.config import FRONTEND_DIR
from backend.routes.api import router as api_router
from backend.routes.frontend import router as frontend_router

# ── Logging ─────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(name)-28s │ %(levelname)-7s │ %(message)s",
    datefmt="%H:%M:%S",
)

# ── App ─────────────────────────────────────────────────────
app = FastAPI(title="Axiom Geo Dashboard")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ──────────────────────────────────────────────────
app.include_router(api_router)
app.include_router(frontend_router)

# ── Static files (must be last — catches all unmatched paths) ─
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
