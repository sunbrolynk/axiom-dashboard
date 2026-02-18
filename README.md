# Axiom Geo Dashboard

A real-time geographic heatmap dashboard for visualizing API request traffic from [Axiom](https://axiom.co) datasets.

## Features

- **Interactive heatmap** — Google Maps with weighted heat visualization, zoom in to see individual IP markers
- **Live Axiom queries** — configurable time ranges powered by APL
- **Local IP geolocation** — MaxMind GeoLite2 for instant, unlimited lookups
- **Analytics panels** — top source IPs, status codes, most-hit endpoints
- **PWA** — installable on mobile with offline shell support
- **Responsive** — desktop side panels + mobile bottom sheet

## Deployment

### 1. Add your MaxMind database

Download `GeoLite2-City.mmdb` from [maxmind.com](https://www.maxmind.com/en/geolite2/signup) and place it at `backend/data/GeoLite2-City.mmdb`.

### 2. Start the container
```yaml
services:
  axiom-dashboard:
    image: ghcr.io/sunbrolynk/axiom-dashboard:latest
    container_name: axiom-dashboard
    restart: unless-stopped
    ports:
      - "8050:8050"
    environment:
      - AXIOM_API_TOKEN=
      - AXIOM_DATASET=
      - GOOGLE_MAPS_API_KEY=
      - MAXMIND_DB_PATH=/app/backend/data/GeoLite2-City.mmdb
    volumes:
      - ./backend/data:/app/backend/data:ro
```

Fill in the environment variables and `docker compose up -d`.

## Configuration

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `AXIOM_API_TOKEN` | Axiom API token with query permission | Yes | — |
| `AXIOM_DATASET` | Axiom dataset name to query | Yes | — |
| `GOOGLE_MAPS_API_KEY` | Google Maps JavaScript API key | Yes | — |
| `MAXMIND_DB_PATH` | Path to GeoLite2-City.mmdb inside container | No | Falls back to ip-api.com |

### Axiom Dataset Requirements

Your dataset needs at minimum an `ip` field. The dashboard also uses these fields if present:

| Field | Used for |
|-------|----------|
| `ip` | Geolocation + request counting |
| `url` | Top endpoints breakdown |
| `status` | Status code distribution |

### Google Maps API

Enable **Maps JavaScript API** at [console.cloud.google.com](https://console.cloud.google.com). The $200/month free credit covers typical dashboard usage.

## Stack

| Component | Technology |
|-----------|------------|
| Backend | Python, FastAPI, uvicorn |
| Frontend | Vanilla JS, Google Maps Visualization API |
| Geolocation | MaxMind GeoLite2 |
| Data | Axiom APL |
| CI/CD | GitHub Actions, ghcr.io |

## License

GPL-3.0
