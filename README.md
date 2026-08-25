# ticker-vault

[![CI](https://github.com/LorenzoPerrella/ticker-vault/actions/workflows/ci.yml/badge.svg)](https://github.com/LorenzoPerrella/ticker-vault/actions/workflows/ci.yml)

API CRUD asincrona per prezzi di titoli finanziari — progetto da portfolio.

Stack: **FastAPI** + **SQLAlchemy 2.0 async** (`asyncpg`) + **PostgreSQL** + **Alembic**,
containerizzato e orchestrato su **Kubernetes** (Kustomize, cluster locale via `kind`).

> 🚧 Progetto in sviluppo incrementale — questo README viene esteso man mano che
> le fasi del piano vengono completate. Architettura e decisioni complete in
> [`plan.md`](plan.md).

## Stato

- [x] Bootstrap progetto (`uv`, `ruff`, `mypy`, `pre-commit`)
- [x] CI GitHub Actions (lint + type-check)
- [x] Modelli dati e migrazioni Alembic
- [x] API CRUD `/api/v1/prices` (+ `/health`, `/ready`)
- [x] Test unitari (repository e API, mockati)
- [x] Test di integrazione (testcontainers)
- [x] Containerizzazione (Dockerfile, docker-compose)
- [ ] Manifest Kubernetes (Kustomize, overlay dev/prod)
- [ ] Documentazione architetturale completa

## Sviluppo locale

Richiede [`uv`](https://docs.astral.sh/uv/) installato.

```bash
uv sync              # crea il virtualenv e installa le dipendenze
uv run ruff check .  # lint
uv run mypy          # type-check
uv run pre-commit install  # (opzionale) hook pre-commit locali
uv run pytest tests/unit         # unit test (nessun DB richiesto)
uv run pytest tests/integration  # integration test (richiede Docker, avvia Postgres in un container)
```

### Database

```bash
docker compose up -d postgres   # Postgres 17 in locale (default dev già validi, nessun .env richiesto)
uv run alembic upgrade head     # applica le migrazioni
```

Per personalizzare le credenziali locali, copia `.env.secret.example` in
`.env.secret` (gitignored) — vedi il file per i dettagli.

### Avvio app (dev loop locale)

```bash
uv run uvicorn price_service.main:app --reload
```

→ [http://localhost:8000/docs](http://localhost:8000/docs) (Swagger UI, `/api/v1/prices`).

### Avvio app (container buildato)

```bash
docker compose up --build
```

Costruisce l'immagine, avvia Postgres, esegue le migrazioni (servizio `migrate`,
one-shot) e solo dopo avvia l'app — stessa API su
[http://localhost:8000/docs](http://localhost:8000/docs), ma tutto containerizzato.

Istruzioni per il deploy k8s locale verranno aggiunte man mano che quella fase
è pronta — vedi [`plan.md`](plan.md) per i dettagli.
