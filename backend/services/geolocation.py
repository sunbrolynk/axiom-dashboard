"""
IP Geolocation Service

Strategy pattern: tries MaxMind local DB first, falls back to ipwho.is.
The rest of the app only calls geocode_ips() and doesn't care which
method is used underneath.

MaxMind:  microsecond lookups, no network, no rate limits
ipwho.is: free HTTPS API, no key required, ~200ms per lookup
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional

import httpx

from backend.config import MAXMIND_DB_PATH

logger = logging.getLogger(__name__)

# ── MaxMind reader (loaded once at import time) ─────────────

_geoip_reader = None


def _init_maxmind():
    """Try to load the MaxMind database. Sets module-level reader or None."""
    global _geoip_reader
    db_path = Path(MAXMIND_DB_PATH)
    if db_path.exists():
        import geoip2.database
        _geoip_reader = geoip2.database.Reader(str(db_path))
        logger.info(f"✓ MaxMind GeoLite2 loaded from {db_path}")
    else:
        logger.warning(f"⚠ MaxMind DB not found at {db_path}, using ipwho.is fallback")


_init_maxmind()


# ── Lookup implementations ──────────────────────────────────

def _lookup_maxmind(ip: str) -> Optional[dict]:
    """Local MaxMind database lookup. Microsecond-fast."""
    if not _geoip_reader:
        return None
    try:
        resp = _geoip_reader.city(ip)
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


async def _lookup_ipwho(ip: str, client: httpx.AsyncClient) -> Optional[dict]:
    """Fallback: HTTPS geolocation via ipwho.is. Free, no API key."""
    try:
        resp = await client.get(f"https://ipwho.is/{ip}", timeout=5.0)
        data = resp.json()
        if data.get("success", False):
            return {
                "ip": ip,
                "lat": data["latitude"],
                "lng": data["longitude"],
                "city": data.get("city", "Unknown"),
                "country": data.get("country", "Unknown"),
                "country_code": data.get("country_code", "??"),
            }
        else:
            logger.warning(f"Geolocation failed for {ip}: {data.get('message', 'unknown')}")
    except Exception as e:
        logger.warning(f"Geolocation error for {ip}: {e}")
    return None


# ── Public interface ────────────────────────────────────────

async def geocode_ips(ips: list[str]) -> list[dict]:
    """
    Geocode a list of IPs. Uses MaxMind if available, otherwise ipwho.is.

    This is the only function the rest of the app should call.
    """
    results = []

    if _geoip_reader:
        for ip in ips:
            result = _lookup_maxmind(ip)
            if result:
                results.append(result)
    else:
        async with httpx.AsyncClient() as client:
            for ip in ips:
                result = await _lookup_ipwho(ip, client)
                if result:
                    results.append(result)
                await asyncio.sleep(0.1)  # Courtesy delay

    return results
