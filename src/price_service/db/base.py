"""Base ORM dichiarativa e factory per engine/sessioni async.

Il wiring concreto (istanza di engine/session usata a runtime dai router FastAPI)
vive in `deps.py`: qui restano solo i costruttori, così Alembic (`migrations/env.py`)
può importare `Base` e creare un proprio engine senza dipendere da uno stato globale.
"""

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Classe base per tutti i modelli ORM."""


def create_engine(database_url: str) -> AsyncEngine:
    return create_async_engine(database_url, pool_pre_ping=True)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)
