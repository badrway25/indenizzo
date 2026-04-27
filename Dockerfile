# syntax=docker/dockerfile:1.7
#
# Multi-stage Dockerfile for Studio Legale Badrane LegalTech.
# Target: staging/production. NOT a dev image (dev resta su `runserver` +
# venv locale).
#
# Build:
#   docker build -t badrane-legaltech:staging .
# Run (single container, behind external nginx):
#   docker run --rm -p 8000:8000 --env-file .env.staging badrane-legaltech:staging
# Compose (recommended):
#   docker compose -f docker-compose.staging.yml up -d --build

# ---------------------------------------------------------------------------
# Stage 1 — builder: installa dipendenze Python in /opt/venv
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# System deps richieste solo a build-time (gcc per psycopg fallback,
# libpq-dev per psycopg2; psycopg[binary] in requirements.txt evita la
# necessità di compilare ma teniamo gcc per Pillow/lxml fallback).
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        libjpeg-dev \
        zlib1g-dev \
        libxml2-dev \
        libxslt1-dev \
 && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /build
COPY requirements.txt .
# gunicorn aggiunto qui: NON è in requirements.txt perché lo usiamo solo
# in container (dev usa `runserver`).
RUN pip install --upgrade pip \
 && pip install -r requirements.txt \
 && pip install gunicorn>=22

# ---------------------------------------------------------------------------
# Stage 2 — runtime: immagine slim con solo libs runtime + venv copiato
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    DJANGO_SETTINGS_MODULE=config.settings

# Runtime libs only (no -dev). libpq5 per psycopg, libjpeg per Pillow,
# libxml2/libxslt per lxml.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        libpq5 \
        libjpeg62-turbo \
        libxml2 \
        libxslt1.1 \
        curl \
 && rm -rf /var/lib/apt/lists/*

# Utente non-root: la piattaforma serve dati legali, mai girare come root.
RUN groupadd --system --gid 1000 app \
 && useradd  --system --uid 1000 --gid app --create-home --shell /bin/bash app

# Copia il venv dal builder (no toolchain in immagine finale).
COPY --from=builder /opt/venv /opt/venv

WORKDIR /app

# Copia codice. .dockerignore esclude .env, db.sqlite3, media/,
# legal_data/exports/, .venv ecc.
COPY --chown=app:app . /app

# Cartelle scrivibili (volumi montati in compose, ma servono comunque
# i mount-point con permessi app).
RUN mkdir -p /app/staticfiles /app/media \
 && chown -R app:app /app

USER app

# collectstatic in build time è opzionale — preferiamo lasciarlo allo
# startup (entrypoint compose) così che le modifiche template non
# richiedano rebuild.
EXPOSE 8000

# Healthcheck: probe HTTP semplice. nginx davanti farà il vero check.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl --fail --silent http://127.0.0.1:8000/ || exit 1

# 3 worker gunicorn = pragmatico per staging single-host. Il timeout 60s
# copre la generazione PDF di reportlab (~5-10 secondi sui report
# grandi).
CMD ["gunicorn", "config.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "3", \
     "--timeout", "60", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
