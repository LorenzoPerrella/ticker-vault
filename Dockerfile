# syntax=docker/dockerfile:1

# ---- builder: risolve le dipendenze e installa il progetto in un venv ----
FROM ghcr.io/astral-sh/uv:python3.12-trixie-slim AS builder

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_DEV=1

# Dipendenze separate dal codice sorgente per il caching dei layer: se cambia
# solo il codice, questo layer (il più lento) resta cache-hit.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project

COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-editable

# ---- runtime: nessun tool di build, solo l'ambiente risolto ----
FROM python:3.12-slim-trixie

RUN groupadd --system --gid 999 nonroot \
 && useradd --system --gid 999 --uid 999 --create-home nonroot

WORKDIR /app
COPY --from=builder --chown=nonroot:nonroot /app /app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

USER nonroot

EXPOSE 8000

# Comando di default: serve l'API. Lo stesso immagine viene usata anche per
# le migrazioni (Job k8s dedicato, Fase 6; servizio `migrate` in
# docker-compose) sovrascrivendo il comando con `alembic upgrade head` —
# un'unica immagine per entrambi i ruoli, nessuna duplicazione di build.
CMD ["uvicorn", "price_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
