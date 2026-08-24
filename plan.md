# Piano di progetto — Price Service

Prototipo da portfolio: API per prezzi di titoli finanziari, con stack Postgres +
SQLAlchemy async + FastAPI + Alembic, containerizzato e orchestrato su Kubernetes.

## Decisioni architetturali

| Decisione | Scelta |
|---|---|
| Ingestion dati | API CRUD completa (no fonti esterne in v1) |
| Manifest k8s | Kustomize (base + overlay dev/prod), cluster locale via `kind` |
| Hosting repo | GitHub pubblico ([LorenzoPerrella/ticker-vault](https://github.com/LorenzoPerrella/ticker-vault)) + GitHub Actions |
| Package manager | `uv` |
| Numeri | `Numeric`/`Decimal`, mai `float`, per i prezzi |
| SQLAlchemy | 2.0 stile typed, async (`asyncpg`) coerente con FastAPI async |
| Migrazioni in k8s | `Job` dedicato pre-rollout, non eseguite dai pod app |
| Postgres in k8s | `StatefulSet` + `PersistentVolumeClaim` (trade-off da prototipo; in produzione si userebbe un servizio managed) |
| Auth | Assente in v1, scope escluso esplicitamente |

## Modello dati v1

Tabella `prices`: `id` (PK), `symbol` (str, indicizzato), `price_date` (date),
`value` (`Numeric(18,6)`), `created_at`. Vincolo `UNIQUE(symbol, price_date)`.

Endpoint `/api/v1/prices`: `POST`, `GET` (filtri `symbol`/`date_from`/`date_to` +
paginazione), `GET/PUT/DELETE /{id}`. `/health` e `/ready` separati.

## Struttura repository

Tutti i percorsi sotto sono relativi alla **radice del repo** `ticker-vault/`
(nessuna sottocartella intermedia; il nome `web-server-app` è solo descrittivo).

```
├── pyproject.toml / uv.lock
├── .pre-commit-config.yaml
├── .github/workflows/ci.yml
├── docker-compose.yml
├── Dockerfile
├── alembic.ini
├── migrations/
├── src/price_service/
│   ├── main.py, config.py
│   ├── db/ (base.py, models.py)
│   ├── repositories/price_repository.py
│   ├── schemas/price.py
│   ├── api/v1/ (router.py, prices.py) , api/health.py
│   └── deps.py
├── tests/{unit,integration}/
└── k8s/
    ├── base/ (namespace.yaml, postgres.yaml, app.yaml, migration-job.yaml, kustomization.yaml)
    └── overlays/{dev,prod}/kustomization.yaml
```

Secrets: mai committati. Generati per overlay via `secretGenerator` di Kustomize da
un file locale gitignored (`.env.secret`), oppure creati manualmente con
`kubectl create secret generic db-credentials --from-literal=...`.

Nota per estendibilità futura: un'eventuale seconda applicazione consumer (es. batch
Airflow) che debba leggere/scrivere sullo stesso Postgres dovrà girare nello stesso
cluster kind, con un proprio overlay applicato separatamente (`kubectl apply -k`),
e generare un proprio `Secret` (namespace-scoped) a partire da un `.env.secret`
locale con le **stesse variabili** (`POSTGRES_USER`, `POSTGRES_PASSWORD`,
`POSTGRES_DB`) usate da ticker-vault — solo le credenziali devono coincidere,
non l'host (che cambia legittimamente tra `localhost` in dev e il DNS del Service
k8s, es. `postgres.ticker-vault.svc.cluster.local`, tra un contesto e l'altro).
La sincronizzazione manuale tra i due file `.env.secret` è un trade-off consapevole
da prototipo, non una soluzione da produzione (dove si userebbe un secret manager
o un operator dedicato).

## Tre modalità di esecuzione

1. **Dev loop locale**: `docker compose up postgres` + `uv run uvicorn price_service.main:app --reload` → `localhost:8000/docs`
2. **Container buildato**: `docker compose up` (app + postgres containerizzati) → `localhost:8000/docs`
3. **Deploy k8s locale**: `kind create cluster` + `kubectl apply -k k8s/overlays/dev` + `kubectl port-forward` → `localhost:8000/docs`

## Piano dei commit

Un commit per unità di lavoro coerente, in ordine. La CI viene attivata **subito
dopo il bootstrap**, non come step finale: da quel momento in poi ogni push è
verificato automaticamente. Il workflow `.github/workflows/ci.yml` viene poi
**esteso negli stessi commit** che introducono ciò che deve validare (non un
commit CI separato a fine percorso) — così ogni pezzo nuovo è coperto fin da
subito e la cronologia mostra CI verde crescere insieme al codice.

- [ ] `chore: bootstrap project with uv, ruff, mypy, pre-commit` — Fase 0: pyproject.toml, uv.lock, config ruff/mypy, pre-commit hooks, .gitignore, README scheletro
- [ ] `ci: add GitHub Actions workflow (lint + type-check)` — scheletro minimo, gira da qui in poi su ogni push/PR
- [ ] `feat(db): add async SQLAlchemy models and Alembic setup` — Fase 1: `db/models.py`, `db/base.py`, `alembic.ini`, `migrations/env.py`
- [ ] `feat(db): add initial migration for prices table` — Fase 1: prima revisione Alembic + `docker-compose.yml` con solo Postgres
- [ ] `feat(repo): add price repository and pydantic schemas` — Fase 2
- [ ] `feat(api): add FastAPI CRUD endpoints for prices` — Fase 3: app factory, deps, router `/api/v1/prices`
- [ ] `feat(api): add health and readiness endpoints` — Fase 3
- [ ] `test: add unit tests for repository and API` + estendo CI con job unit test — Fase 4 (repository mockato)
- [ ] `test: add integration tests with testcontainers` + estendo CI con job integration test (Docker disponibile nei runner Actions) — Fase 4
- [ ] `chore(docker): add multi-stage Dockerfile and extend docker-compose` + estendo CI con job build immagine — Fase 5
- [ ] `chore(k8s): add base Kustomize manifests` — Fase 6: namespace, postgres (StatefulSet+PVC+Service), app (Deployment+Service), migration Job
- [ ] `chore(k8s): add dev/prod overlays with secret generator` + estendo CI con validazione `kubectl kustomize build` — Fase 6
- [ ] `docs: add architecture README and portfolio polish` — Fase 8

Il primo commit crea anche il repository Git locale (`git init`). Il repo remoto
`LorenzoPerrella/ticker-vault` esiste già su GitHub (pubblico, vuoto): dopo il primo
commit viene collegato come `origin` e da quel momento **ogni commit verificato
localmente (lint/type-check, e test dove applicabile) viene pushato in autonomia**,
senza chiedere conferma ad ogni singolo push — così la CI parte gradualmente e
cresce verde insieme al codice, commit dopo commit. Ogni push viene comunque
segnalato dopo averlo eseguito.

## Verifica end-to-end

- `uv run pytest tests/unit` — unit test
- `uv run pytest tests/integration` — integration test (richiede Docker)
- `uv run ruff check .` / `uv run mypy src` — lint/type-check
- Push su GitHub → verifica che il workflow Actions passi
