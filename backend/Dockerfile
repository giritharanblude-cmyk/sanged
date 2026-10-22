# SANGAD — API image (also serves the SPA, per docs/SANGAD_ARCHITECTURE_v0_3.md ADR-17).
# Build context is the repository root:
#   docker build -f backend/Dockerfile .

# ---------------------------------------------------------------------------
# Stage 1: build the React SPA with Vite.
# ---------------------------------------------------------------------------
FROM node:20.19-alpine AS frontend

WORKDIR /build

# Install exactly the frontend dependency tree committed in the lockfile.
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund

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

# Keep the image's package installer on the approved security-fixed release.
RUN python -m pip install --no-cache-dir --upgrade "pip==26.2.1"

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

# The backup and restore drill (T-008, T-011) dumps a database and
# restores it into a scratch database to check the row counts, which
# needs pg_dump, pg_restore and psql. They have to be the same major
# version as the server: Debian bookworm ships the 15 client, which
# refuses to dump a 16 server, so the client comes from the PostgreSQL
# apt repository instead.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        gnupg \
    && install -d /usr/share/postgresql-common/pgdg \
    && curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc \
        -o /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc \
    && echo "deb [signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.asc] https://apt.postgresql.org/pub/repos/apt bookworm-pgdg main" \
        > /etc/apt/sources.list.d/pgdg.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        postgresql-client-16 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/requirements.txt ./requirements.txt
RUN pip install -r requirements.txt

COPY backend/pyproject.toml ./pyproject.toml
COPY backend/app ./app
# Alembic needs its config and migration scripts in the image so the API can
# apply migrations on start.
COPY backend/alembic.ini ./alembic.ini
COPY backend/migrations ./migrations
COPY --from=frontend /build/dist ./static

# Drop privileges for the runtime process.
RUN useradd --create-home --uid 10001 sangad \
    && mkdir -p /var/lib/sangad/storage \
    && chown -R sangad:sangad /app /var/lib/sangad
USER sangad

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=5 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=4)"]

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]