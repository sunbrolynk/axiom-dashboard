# Axiom Geo Dashboard

A real-time geographic heatmap dashboard for visualizing API request traffic from [Axiom](https://axiom.co) datasets. See where your users are, which endpoints they hit, and how your API performs — all on an interactive map.

## Features

- **Interactive heatmap** — Google Maps with weighted heat visualization based on request volume
- **Zoom-level detail** — zoomed out shows density heatmap, zoom in to see individual IP markers with request counts
- **Live Axiom queries** — configurable time ranges (6h / 24h / 7d / 30d) powered by APL
- **Local IP geolocation** — MaxMind GeoLite2 database for instant, unlimited IP → coordinate lookups
- **Analytics sidebar** — top source IPs, status code breakdown, most-hit endpoints
- **PWA** — installable on mobile with offline shell support
- **Responsive** — desktop side panels + mobile bottom sheet
- **Dockerized** — single container deployment with Traefik-ready labels

## Screenshots

*Coming soon*

## Quick Start

### Prerequisites

| Service | What you need | Link |
|---------|--------------|------|
| Axiom | API token with query permission on your dataset | [axiom.co](https://axiom.co) |
| Google Maps | JavaScript API key with Maps JavaScript API enabled | [console.cloud.google.com](https://console.cloud.google.com) |
| MaxMind | GeoLite2-City.mmdb database file | [maxmind.com](https://www.maxmind.com/en/geolite2/signup) |

### Docker (recommended)
```bash
git clone https://github.com/sunbrolynk/axiom-dashboard.git
cd axiom-dashboard

cp .env.example .env
# Edit .env with your API keys and dataset name

# Place your MaxMind database
cp /path/to/GeoLite2-City.mmdb backend/data/

docker compose up -d
```

Dashboard available at `http://localhost:8050`

### Local Development
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

cd backend
python -m uvicorn server:app --host 0.0.0.0 --port 8050 --reload
```

### Reverse Proxy (Traefik)

Uncomment the labels and network sections in `docker-compose.yml` and update the hostname to your domain.

## Configuration

All configuration is via environment variables (`.env` file):

| Variable | Description | Required |
|----------|-------------|----------|
| `AXIOM_API_TOKEN` | Axiom API token with query permission | Yes |
| `AXIOM_DATASET` | Axiom dataset name to query | Yes |
| `GOOGLE_MAPS_API_KEY` | Google Maps JavaScript API key | Yes |
| `MAXMIND_DB_PATH` | Path to GeoLite2-City.mmdb | No (falls back to ip-api.com) |

## Dataset Requirements

Your Axiom dataset needs at minimum an `ip` field containing client IP addresses. The dashboard also utilizes these fields if present:

- `url` or `path` — request endpoint
- `status` — HTTP status code
- `method` — HTTP method

## Stack

| Component | Technology |
|-----------|------------|
| Backend | Python, FastAPI, uvicorn |
| Frontend | Vanilla JS, Google Maps Visualization API |
| Geolocation | MaxMind GeoLite2 (ip-api.com fallback) |
| Data | Axiom APL queries |
| Deployment | Docker |

## License

MIT
