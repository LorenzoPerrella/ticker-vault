"""Endpoint di health/readiness, separati dalla business API e da `/api/v1`.

Distinti perché controllano cose diverse: `/health` è una liveness probe (il
processo risponde, non tocca il DB); `/ready` è una readiness probe (il DB è
raggiungibile) — la distinzione è quella standard attesa dai probe k8s
(Fase 6): un DB temporaneamente giù non deve far riavviare il pod (liveness),
ma deve toglierlo dal load balancing finché non torna (readiness).
"""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text

from price_service.deps import SessionDep

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
async def ready(session: SessionDep) -> dict[str, str]:
    try:
        await session.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="database not ready"
        ) from exc
    return {"status": "ready"}
