# ticker-vault

API CRUD asincrona per prezzi di titoli finanziari — progetto da portfolio.

Stack: **FastAPI** + **SQLAlchemy 2.0 async** (`asyncpg`) + **PostgreSQL** + **Alembic**,
containerizzato e orchestrato su **Kubernetes** (Kustomize, cluster locale via `kind`).

> 🚧 Progetto in sviluppo incrementale — questo README viene esteso man mano che
> le fasi del piano vengono completate. Architettura e decisioni complete in
> [`plan.md`](plan.md).

## Stato

- [x] Bootstrap progetto (`uv`, `ruff`, `mypy`, `pre-commit`)
- [ ] CI GitHub Actions
- [ ] Modelli dati e migrazioni Alembic
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
uv run mypy src      # type-check
uv run pre-commit install  # (opzionale) hook pre-commit locali
```

Istruzioni per l'avvio dell'app e per le tre modalità di esecuzione (dev loop,
container, k8s locale) verranno aggiunte man mano che quelle fasi sono pronte —
vedi [`plan.md`](plan.md) per i dettagli.
