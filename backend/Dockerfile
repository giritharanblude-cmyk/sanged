# SANGAD — API image (also serves the SPA, per docs/SANGAD_ARCHITECTURE_v0_3.md ADR-17).
# Build context is the repository root:
#   docker build -f backend/Dockerfile .

# ---------------------------------------------------------------------------
# Stage 1: build the React SPA with Vite.
# ---------------------------------------------------------------------------
FROM node:20.19-alpine AS frontend

WORKDIR /build

# Install dependencies from the lockfile-free manifest first so this layer is
# cached until package.json actually changes.
COPY frontend/package.json ./
RUN npm install --no-audit --no-fund

COPY frontend/ ./
RUN npm run build

# ---------------------------------------------------------------------------
# Stage 2: Python runtime serving the API and the built SPA from one origin.
# ---------------------------------------------------------------------------
FROM python:3.12.8-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# WeasyPrint (PDF generation, ADR-03) links against system Pango/HarfBuzz/fontconfig
# rather than bundling it, so these are hard runtime requirements, not build extras.
# fonts-liberation gives PDF output a real font to embed (V-PAY-04).
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libpango-1.0-0 \
        libpangoft2-1.0-0 \
        libharfbuzz-subset0 \
        libgdk-pixbuf-2.0-0 \
        libjpeg62-turbo \
        shared-mime-info \
        fontconfig \
        fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/requirements.txt ./requirements.txt
RUN pip install -r requirements.txt

COPY backend/app ./app
# Alembic needs its config and migration scripts in the image so the API can
# apply migrations on start.
COPY backend/alembic.ini ./alembic.ini
COPY backend/migrations ./migrations
COPY --from=frontend /build/dist ./static

# Drop privileges for the runtime process.
RUN useradd --create-home --uid 10001 sangad \
    && chown -R sangad:sangad /app
USER sangad

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=5 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=4)"]

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]