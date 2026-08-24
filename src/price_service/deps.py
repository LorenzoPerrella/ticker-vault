"""Dependency injection FastAPI: una `AsyncSession` per richiesta.

Commit se l'handler completa senza eccezioni, rollback altrimenti — così un
errore (es. `DuplicatePriceError`) chiude in modo pulito l'intera unità di
lavoro della richiesta, invece di lasciare la sessione a metà.
"""

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from price_service.config import get_settings
from price_service.db.base import create_engine, create_session_factory
from price_service.repositories.price_repository import PriceRepository

_engine = create_engine(get_settings().database_url)
_session_factory = create_session_factory(_engine)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with _session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        else:
            await session.commit()


SessionDep = Annotated[AsyncSession, Depends(get_session)]


def get_price_repository(session: SessionDep) -> PriceRepository:
    return PriceRepository(session)


PriceRepositoryDep = Annotated[PriceRepository, Depends(get_price_repository)]
