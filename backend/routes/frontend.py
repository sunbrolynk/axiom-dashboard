"""
Frontend Routes — serves the HTML shell, PWA files, and static assets.

The main index.html has a placeholder __GOOGLE_MAPS_API_KEY__ that gets
replaced at serve time so the key stays in environment variables only.
"""

from fastapi import APIRouter
from fastapi.responses import FileResponse, HTMLResponse

from backend.config import FRONTEND_DIR, GOOGLE_MAPS_API_KEY

router = APIRouter()


@router.get("/")
async def serve_index():
    """Serve frontend with Google Maps API key injected."""
    html = (FRONTEND_DIR / "index.html").read_text()
    html = html.replace("__GOOGLE_MAPS_API_KEY__", GOOGLE_MAPS_API_KEY)
    return HTMLResponse(html)


@router.get("/manifest.json")
async def serve_manifest():
    return FileResponse(
        FRONTEND_DIR / "manifest.json",
        media_type="application/manifest+json",
    )


@router.get("/service-worker.js")
async def serve_service_worker():
    """Service worker must be served from root path for correct scope."""
    return FileResponse(
        FRONTEND_DIR / "service-worker.js",
        media_type="application/javascript",
    )
