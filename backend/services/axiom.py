"""
Axiom API Client

Handles all communication with the Axiom APL query API.
APL (Axiom Processing Language) is pipe-based, similar to KQL.

Two responsibilities:
1. Execute APL queries against the Axiom API
2. Parse Axiom's columnar response format into row dicts
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

import httpx

from backend.config import AXIOM_API_TOKEN, AXIOM_DATASET, AXIOM_API_URL

logger = logging.getLogger(__name__)


def _time_range(hours: int) -> dict:
    """Build the time range dict Axiom expects."""
    now = datetime.now(timezone.utc)
    return {
        "startTime": (now - timedelta(hours=hours)).isoformat(),
        "endTime": now.isoformat(),
    }


def _headers() -> dict:
    """Auth headers for Axiom API."""
    return {
        "Authorization": f"Bearer {AXIOM_API_TOKEN}",
        "Content-Type": "application/json",
    }


def parse_tabular_response(data: dict) -> list[dict]:
    """
    Convert Axiom's columnar format to a list of row dicts.

    Axiom returns:
        {"tables": [{"fields": [{"name": "ip"}, ...], "columns": [["1.2.3.4", ...], ...]}]}

    We produce:
        [{"ip": "1.2.3.4", "request_count": 100}, ...]
    """
    tables = data.get("tables", [])
    if not tables:
        return []

    table = tables[0]
    fields = [f["name"] for f in table.get("fields", [])]
    columns = table.get("columns", [])

    if not columns or not fields:
        return []

    num_rows = len(columns[0])
    return [
        {fields[j]: columns[j][i] for j in range(len(fields))}
        for i in range(num_rows)
    ]


async def query_ip_counts(hours: int = 24) -> list[dict]:
    """
    Get IP request counts for the last N hours.

    Returns: [{"ip": "1.2.3.4", "request_count": 100}, ...]
    """
    apl = f"""
    ['{AXIOM_DATASET}']
    | where _time >= ago({hours}h)
    | where isnotnull(ip) and ip != ""
    | summarize request_count = count() by ip
    | order by request_count desc
    | take 500
    """

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            AXIOM_API_URL,
            headers=_headers(),
            json={"apl": apl, **_time_range(hours)},
            timeout=30.0,
        )
        resp.raise_for_status()
        return parse_tabular_response(resp.json())


async def query_stats(hours: int = 24) -> dict:
    """
    Get endpoint and status code stats for the last N hours.

    Returns: {"top_endpoints": [...], "status_codes": [...]}
    """
    apl_endpoints = f"""
    ['{AXIOM_DATASET}']
    | where _time >= ago({hours}h)
    | summarize hits = count() by url
    | order by hits desc
    | take 20
    """

    apl_statuses = f"""
    ['{AXIOM_DATASET}']
    | where _time >= ago({hours}h)
    | where isnotnull(status)
    | summarize count = count() by status
    | order by count desc
    """

    time = _time_range(hours)

    async with httpx.AsyncClient() as client:
        ep_resp, st_resp = await asyncio.gather(
            client.post(
                AXIOM_API_URL,
                headers=_headers(),
                json={"apl": apl_endpoints, **time},
                timeout=30.0,
            ),
            client.post(
                AXIOM_API_URL,
                headers=_headers(),
                json={"apl": apl_statuses, **time},
                timeout=30.0,
            ),
        )

    return {
        "top_endpoints": parse_tabular_response(ep_resp.json()),
        "status_codes": parse_tabular_response(st_resp.json()),
    }
