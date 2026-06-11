# ── Stage 1: Build Angular frontend ─────────────────────────────────────────
FROM node:22-alpine AS frontend-builder
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm install --prefer-offline
COPY frontend/ ./
RUN npm run build

# ── Stage 2: Python runtime ──────────────────────────────────────────────────
FROM python:3.11-slim

# curl is required for the HEALTHCHECK
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/conwo

# Install Python dependencies before copying source (better layer caching)
COPY requirements-backend.txt requirements.txt ./
RUN pip install --no-cache-dir -r requirements-backend.txt -r requirements.txt

# Copy application source
COPY backend/ backend/
COPY config/ config/
COPY scripts/ scripts/
COPY migrations/ migrations/
COPY CLAUDE.md ./

# Bake the wiki/ knowledge-base baseline (~700KB) into the image. In prod, wiki/
# lives on a mounted PVC (CONWO_DATA_DIR=/app/data) that starts empty; the app
# seeds it from this baked copy on first boot (see api.py _seed_wiki_if_empty).
COPY wiki/ wiki/

# Copy pre-built Angular app from Stage 1.
# Backend expects: Path(__file__).parent.parent / "frontend/dist/frontend/browser"
# = /opt/conwo/frontend/dist/frontend/browser/
COPY --from=frontend-builder /build/dist/frontend/browser/ \
     frontend/dist/frontend/browser/

# Create volume mount points for persistent runtime data.
# These directories are populated at runtime via -v mounts — never baked in.
RUN mkdir -p raw wiki

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Schema is created/updated automatically at startup by the FastAPI lifespan
# (backend.api → db.init_db(), advisory-locked + idempotent), against the
# PostgreSQL database configured via CONWO_DB_*. No pre-start SQLite init needed.
# (Multi-replica: set CONWO_RUN_MIGRATIONS=false on replicas and run migrations
#  as a one-shot job if you prefer not to migrate-on-boot; the advisory lock makes
#  concurrent boot safe either way.)
CMD ["uvicorn", "backend.api:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
