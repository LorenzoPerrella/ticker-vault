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
- [ ] API CRUD `/api/v1/prices`
- [ ] Test unitari e di integrazione
- [ ] Containerizzazione (Dockerfile, docker-compose)
- [ ] Manifest Kubernetes (Kustomize, overlay dev/prod)
- [ ] Documentazione architetturale completa

## Sviluppo locale

Richiede [`uv`](https://docs.astral.sh/uv/) installato.

```bash
uv sync              # crea il virtualenv e installa le dipendenze
uv run ruff check .  # lint
uv run mypy          # type-check
uv run pre-commit install  # (opzionale) hook pre-commit locali
```

### Database

```bash
docker compose up -d postgres   # Postgres 17 in locale (default dev già validi, nessun .env richiesto)
uv run alembic upgrade head     # applica le migrazioni
```

Per personalizzare le credenziali locali, copia `.env.secret.example` in
`.env.secret` (gitignored) — vedi il file per i dettagli.

Istruzioni per l'avvio dell'app e per le altre modalità di esecuzione (container,
k8s locale) verranno aggiunte man mano che quelle fasi sono pronte — vedi
[`plan.md`](plan.md) per i dettagli.
