"""
Axiom Dashboard Backend
Queries Axiom for request data, geocodes IPs, serves to frontend map.
"""

import os
import json
import asyncio
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
import uvicorn
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv

# Load .env — works both in local dev and Docker
# Local: backend/server.py → parent.parent = project root
# Docker: /app/backend/server.py → parent.parent = /app
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    # Docker may have env vars injected via docker-compose env_file
    pass

AXIOM_TOKEN = os.getenv("AXIOM_API_TOKEN")
AXIOM_DATASET = os.getenv("AXIOM_DATASET", "audimeta")
MAXMIND_DB_PATH = os.getenv("MAXMIND_DB_PATH", "./backend/data/GeoLite2-City.mmdb")
GOOGLE_MAPS_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")

# ---------------------------------------------------------------------------
# MaxMind GeoIP reader (lazy-loaded)
# ---------------------------------------------------------------------------
# We try to load the .mmdb file. If it doesn't exist yet (waiting on MaxMind
# support), we fall back to ip-api.com. The rest of the app doesn't care
# which method is used — it just calls geocode_ip().
# ---------------------------------------------------------------------------

geoip_reader = None

def _init_maxmind():
    """Try to load the MaxMind database. Returns reader or None."""
    global geoip_reader
    db_path = Path(MAXMIND_DB_PATH)
    if db_path.exists():
        import geoip2.database
        geoip_reader = geoip2.database.Reader(str(db_path))
        print(f"✓ MaxMind GeoLite2 loaded from {db_path}")
    else:
        print(f"⚠ MaxMind DB not found at {db_path}, using ip-api.com fallback")

_init_maxmind()


def geocode_ip_maxmind(ip: str) -> Optional[dict]:
    """Look up IP using local MaxMind database. Microsecond-fast."""
    if not geoip_reader:
        return None
    try:
        resp = geoip_reader.city(ip)
        if resp.location.latitude and resp.location.longitude:
            return {
                "ip": ip,
                "lat": resp.location.latitude,
                "lng": resp.location.longitude,
                "city": resp.city.name or "Unknown",
                "country": resp.country.name or "Unknown",
                "country_code": resp.country.iso_code or "??",
            }
    except Exception:
        pass
    return None


async def geocode_ip_fallback(ip: str, client: httpx.AsyncClient) -> Optional[dict]:
    """
    Fallback: query ip-api.com for geolocation.
    Free tier: 45 requests/minute. We batch to stay under this.
    """
    try:
        resp = await client.get(
            f"http://ip-api.com/json/{ip}",
            params={"fields": "status,lat,lon,city,country,countryCode"},
            timeout=5.0,
        )
        data = resp.json()
        if data.get("status") == "success":
            return {
                "ip": ip,
                "lat": data["lat"],
                "lng": data["lon"],
                "city": data.get("city", "Unknown"),
                "country": data.get("country", "Unknown"),
                "country_code": data.get("countryCode", "??"),
            }
    except Exception:
        pass
    return None


async def geocode_ips(ips: list[str]) -> list[dict]:
    """
    Geocode a list of IPs. Uses MaxMind if available, otherwise ip-api.com.
    
    This is the "pluggable" function — the rest of the app calls this
    and doesn't care about the underlying implementation.
    """
    results = []

    if geoip_reader:
        # MaxMind path: instant, no rate limits
        for ip in ips:
            result = geocode_ip_maxmind(ip)
            if result:
                results.append(result)
    else:
        # Fallback path: external API, rate limited
        async with httpx.AsyncClient() as client:
            for ip in ips:
                result = await geocode_ip_fallback(ip, client)
                if result:
                    results.append(result)
                # Respect rate limit: 45/min ≈ 1 every 1.4 seconds
                await asyncio.sleep(1.5)

    return results


# ---------------------------------------------------------------------------
# Axiom API client
# ---------------------------------------------------------------------------
# APL (Axiom Processing Language) is similar to Kusto Query Language (KQL).
# We query the dataset, group by IP, count requests per IP, and also grab
# useful metadata like top endpoints and status codes.
# ---------------------------------------------------------------------------

async def query_axiom(hours: int = 24) -> dict:
    """
    Query the Axiom API using APL to get IP request counts.
    
    The APL query does:
    - Filters to the last N hours
    - Groups by IP address
    - Counts requests per IP
    - Returns top 500 IPs by request count
    
    Returns raw Axiom response parsed as dict.
    """
    # APL query — this is like SQL but for Axiom
    apl = f"""
    ['audimeta']
    | where _time >= ago({hours}h)
    | where isnotnull(ip) and ip != ""
    | summarize request_count = count() by ip
    | order by request_count desc
    | take 500
    """

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.axiom.co/v1/datasets/_apl?format=tabular",
            headers={
                "Authorization": f"Bearer {AXIOM_TOKEN}",
                "Content-Type": "application/json",
            },
            json={
                "apl": apl,
                "startTime": (
                    datetime.now(timezone.utc) - timedelta(hours=hours)
                ).isoformat(),
                "endTime": datetime.now(timezone.utc).isoformat(),
            },
            timeout=30.0,
        )
        resp.raise_for_status()
        return resp.json()


def parse_axiom_response(data: dict) -> list[dict]:
    """
    Parse Axiom's tabular response format into a simple list.
    
    Axiom returns data in a columnar format:
    {
        "tables": [{
            "fields": [{"name": "ip"}, {"name": "request_count"}],
            "columns": [["1.2.3.4", "5.6.7.8"], [100, 50]]
        }]
    }
    
    We convert this to:
    [{"ip": "1.2.3.4", "request_count": 100}, {"ip": "5.6.7.8", "request_count": 50}]
    """
    results = []
    tables = data.get("tables", [])
    if not tables:
        return results

    table = tables[0]
    fields = [f["name"] for f in table.get("fields", [])]
    columns = table.get("columns", [])

    if not columns or not fields:
        return results

    # Transpose columns to rows
    num_rows = len(columns[0]) if columns else 0
    for i in range(num_rows):
        row = {}
        for j, field in enumerate(fields):
            row[field] = columns[j][i] if j < len(columns) else None
        results.append(row)

    return results


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(title="Axiom Dashboard")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Fine for local/self-hosted dashboard
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/geodata")
async def get_geodata(hours: int = Query(default=24, ge=1, le=720)):
    """
    Main endpoint: returns geocoded IP data for the map.
    
    1. Queries Axiom for IP request counts over the last N hours
    2. Geocodes each IP to lat/lng
    3. Merges the data and returns it
    
    Response format:
    [
        {
            "ip": "1.2.3.4",
            "lat": 37.7749,
            "lng": -122.4194,
            "city": "San Francisco",
            "country": "United States",
            "country_code": "US",
            "request_count": 142
        },
        ...
    ]
    """
    # Step 1: Query Axiom
    raw = await query_axiom(hours=hours)
    ip_data = parse_axiom_response(raw)

    if not ip_data:
        return []

    # Step 2: Geocode all unique IPs
    unique_ips = [row["ip"] for row in ip_data if row.get("ip")]
    geo_results = await geocode_ips(unique_ips)

    # Step 3: Merge — create a lookup from IP → geo data
    geo_lookup = {g["ip"]: g for g in geo_results}

    merged = []
    for row in ip_data:
        ip = row.get("ip")
        if ip and ip in geo_lookup:
            entry = geo_lookup[ip].copy()
            entry["request_count"] = row.get("request_count", 0)
            merged.append(entry)

    return merged


@app.get("/api/stats")
async def get_stats(hours: int = Query(default=24, ge=1, le=720)):
    """
    Supplementary stats: top endpoints, status code breakdown, etc.
    """
    apl_endpoints = f"""
    ['audimeta']
    | where _time >= ago({hours}h)
    | summarize hits = count() by url
    | order by hits desc
    | take 20
    """

    apl_statuses = f"""
    ['audimeta']
    | where _time >= ago({hours}h)
    | where isnotnull(status)
    | summarize count = count() by status
    | order by count desc
    """

    async with httpx.AsyncClient() as client:
        headers = {
            "Authorization": f"Bearer {AXIOM_TOKEN}",
            "Content-Type": "application/json",
        }
        time_range = {
            "startTime": (
                datetime.now(timezone.utc) - timedelta(hours=hours)
            ).isoformat(),
            "endTime": datetime.now(timezone.utc).isoformat(),
        }

        ep_resp, st_resp = await asyncio.gather(
            client.post(
                "https://api.axiom.co/v1/datasets/_apl?format=tabular",
                headers=headers,
                json={"apl": apl_endpoints, **time_range},
                timeout=30.0,
            ),
            client.post(
                "https://api.axiom.co/v1/datasets/_apl?format=tabular",
                headers=headers,
                json={"apl": apl_statuses, **time_range},
                timeout=30.0,
            ),
        )

    return {
        "top_endpoints": parse_axiom_response(ep_resp.json()),
        "status_codes": parse_axiom_response(st_resp.json()),
    }


# Serve frontend
frontend_dir = Path(__file__).parent.parent / "frontend"


@app.get("/")
async def serve_frontend():
    """Serve frontend with Google Maps API key injected from environment."""
    html = (frontend_dir / "index.html").read_text()
    html = html.replace("__GOOGLE_MAPS_API_KEY__", GOOGLE_MAPS_KEY)
    from fastapi.responses import HTMLResponse
    return HTMLResponse(html)


@app.get("/manifest.json")
async def serve_manifest():
    return FileResponse(frontend_dir / "manifest.json", media_type="application/manifest+json")


@app.get("/service-worker.js")
async def serve_sw():
    """Service worker must be served from root path for correct scope."""
    return FileResponse(frontend_dir / "service-worker.js", media_type="application/javascript")


# Mount static files (CSS, JS if we add them later)
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")


if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8050, reload=True)
