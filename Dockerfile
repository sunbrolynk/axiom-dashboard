# ── Build stage ─────────────────────────────────────────────
# Using slim Python image to keep the container small.
# We don't need a build stage for the frontend since it's
# just a static HTML file — no npm/webpack needed.
FROM python:3.12-slim

# Set labels for container metadata
LABEL maintainer="sunbrolynk"
LABEL description="AudiMeta request analytics dashboard"

# Create non-root user for security
# Running containers as root is a security risk — if the
# container is compromised, the attacker has root access.
RUN groupadd -r dashboard && useradd -r -g dashboard -m dashboard

WORKDIR /app

# Install Python dependencies first (layer caching)
# Docker caches each layer. By copying requirements.txt
# separately, we only re-install dependencies when they
# change — not on every code change.
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/ ./backend/
COPY frontend/ ./frontend/

# The .env and GeoLite2-City.mmdb are mounted at runtime,
# NOT baked into the image. This keeps secrets out of the
# image layers and lets you update the DB without rebuilding.

# Switch to non-root user
USER dashboard

# Expose the dashboard port
EXPOSE 8050

# Health check — Docker/Portainer can monitor this
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8050/api/stats?hours=1')" || exit 1

# Run with uvicorn
# --proxy-headers: trusts X-Forwarded-* from Traefik/nginx
# --forwarded-allow-ips='*': allows any reverse proxy
CMD ["python", "-m", "uvicorn", "backend.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8050", \
     "--proxy-headers", \
     "--forwarded-allow-ips=*"]
