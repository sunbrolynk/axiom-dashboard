"""
Centralized configuration — all environment variables loaded here.

Every other module imports from config rather than calling os.getenv()
directly. This makes it easy to see every setting in one place and
ensures consistent defaults across the app.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env — works both in local dev and Docker
# Local:  backend/config.py → parent.parent = project root
# Docker: /app/backend/config.py → parent.parent = /app
_env_path = Path(__file__).parent.parent / ".env"
if _env_path.exists():
    load_dotenv(_env_path)

# ── Axiom ───────────────────────────────────────────────────
AXIOM_API_TOKEN: str = os.getenv("AXIOM_API_TOKEN", "")
AXIOM_DATASET: str = os.getenv("AXIOM_DATASET", "audimeta")
AXIOM_API_URL: str = "https://api.axiom.co/v1/datasets/_apl?format=tabular"

# ── Geolocation ─────────────────────────────────────────────
MAXMIND_DB_PATH: str = os.getenv("MAXMIND_DB_PATH", "./backend/data/GeoLite2-City.mmdb")

# ── Google Maps ─────────────────────────────────────────────
GOOGLE_MAPS_API_KEY: str = os.getenv("GOOGLE_MAPS_API_KEY", "")

# ── Paths ───────────────────────────────────────────────────
FRONTEND_DIR: Path = Path(__file__).parent.parent / "frontend"
