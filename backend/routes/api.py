"""
API Routes — thin HTTP layer over services.

These endpoints take query params, call the appropriate service,
and return JSON. No business logic lives here.
"""

from fastapi import APIRouter, Query

from backend.services.axiom import query_ip_counts, query_stats
from backend.services.geolocation import geocode_ips

router = APIRouter(prefix="/api")


@router.get("/geodata")
async def get_geodata(hours: int = Query(default=24, ge=1, le=720)):
    """
    Geocoded IP data for the map.

    1. Queries Axiom for IP request counts
    2. Geocodes each IP to lat/lng
    3. Merges and returns the combined data
    """
    ip_data = await query_ip_counts(hours=hours)
    if not ip_data:
        return []

    unique_ips = [row["ip"] for row in ip_data if row.get("ip")]
    geo_results = await geocode_ips(unique_ips)

    geo_lookup = {g["ip"]: g for g in geo_results}

    return [
        {**geo_lookup[row["ip"]], "request_count": row.get("request_count", 0)}
        for row in ip_data
        if row.get("ip") and row["ip"] in geo_lookup
    ]


@router.get("/stats")
async def get_stats(hours: int = Query(default=24, ge=1, le=720)):
    """Top endpoints and status code breakdown."""
    return await query_stats(hours=hours)
