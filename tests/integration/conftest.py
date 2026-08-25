"""Fixture condivise per i test di integrazione: Postgres reale via testcontainers.

Il container e le migrazioni Alembic sono a livello di sessione (costosi, una
volta sola); engine e sessione sono per-test (evita di condividere un
AsyncEngine/pool asyncpg tra event loop diversi di test distinti) con rollback
a fine test per isolamento reciproco.
"""

import asyncio
import datetime
from collections.abc import AsyncGenerator, Generator, Iterator
from dataclasses import dataclass
from decimal import Decimal

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from testcontainers.community.postgres import PostgresContainer

from price_service.db.base import create_engine, create_session_factory
from price_service.db.models import Price
from price_service.deps import get_session
from price_service.main import app


@pytest.fixture(scope="session")
def postgres_url() -> Generator[str, None, None]:
    with PostgresContainer(
        "postgres:17", username="test", password="test", dbname="test", driver="asyncpg"
    ) as container:
        url = container.get_connection_url()

        alembic_cfg = Config("alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", url)
        command.upgrade(alembic_cfg, "head")

        yield url


@pytest.fixture
async def db_session(postgres_url: str) -> AsyncGenerator[AsyncSession, None]:
    engine = create_engine(postgres_url)
    session_factory = create_session_factory(engine)
    async with session_factory() as session:
        yield session
        await session.rollback()
    await engine.dispose()


@pytest.fixture(autouse=True)
def _clean_prices_table(postgres_url: str) -> None:
    """Autouse: garantisce una tabella `prices` vuota prima di OGNI test in
    `tests/integration`, indipendentemente dalle fixture che usa.

    `db_session` da solo basterebbe (rollback a fine test), ma i test HTTP
    (`api_client`) passano dalla vera `get_session` dell'app, che fa commit
    reale sul successo — dati che altrimenti resterebbero nel container
    condiviso (session-scoped) e sporcherebbero i test successivi. Gira in
    un event loop isolato come `seed_prices`, per lo stesso motivo (evitare
    di legare connessioni al loop di un test diverso).
    """

    async def _truncate() -> None:
        engine = create_engine(postgres_url)
        session_factory = create_session_factory(engine)
        async with session_factory() as session:
            await session.execute(delete(Price))
            await session.commit()
        await engine.dispose()

    asyncio.run(_truncate())


@dataclass(frozen=True)
class SeededPrice:
    """Snapshot semplice (non un oggetto ORM agganciato a una sessione ormai
    chiusa) di un record inserito da `seed_prices` prima del test."""

    id: int
    symbol: str
    price_date: datetime.date
    value: Decimal


@pytest.fixture
def seed_prices(postgres_url: str, _clean_prices_table: None) -> list[SeededPrice]:
    """Popola la tabella (già vuota grazie a `_clean_prices_table`, richiesta
    esplicitamente per fissare l'ordine) con 2 record noti PRIMA della
    richiesta HTTP e non tramite l'API sotto test — stato deterministico,
    indipendente da ciò che si sta verificando.

    Fixture sincrona che usa un proprio `asyncio.run()`: gira in un event
    loop isolato, creato e chiuso qui, così l'engine usato per seminare i
    dati non condivide connessioni col loop interno del `TestClient` in
    `api_client` — la stessa classe di bug incontrata in Fase 4
    (MissingGreenlet/connessioni legate a un loop diverso).
    """

    async def _seed() -> list[SeededPrice]:
        engine = create_engine(postgres_url)
        session_factory = create_session_factory(engine)
        async with session_factory() as session:
            rows = [
                Price(
                    symbol="AAPL", price_date=datetime.date(2026, 1, 2), value=Decimal("190.500000")
                ),
                Price(
                    symbol="MSFT", price_date=datetime.date(2026, 1, 3), value=Decimal("410.100000")
                ),
            ]
            session.add_all(rows)
            await session.commit()
            for row in rows:
                await session.refresh(row)
            # Letti in attributi semplici finché la sessione è ancora aperta:
            # dopo, gli oggetti ORM sarebbero "detached" e inutilizzabili.
            snapshot = [
                SeededPrice(id=r.id, symbol=r.symbol, price_date=r.price_date, value=r.value)
                for r in rows
            ]
        await engine.dispose()
        return snapshot

    return asyncio.run(_seed())


@pytest.fixture
def api_engine(postgres_url: str) -> AsyncEngine:
    # Costruito qui, non con un `async def` a livello di fixture: l'oggetto
    # engine non fa I/O finché non gli si chiede una connessione, quindi non
    # importa in quale loop viene istanziato — solo dove viene *usato* (qui,
    # esclusivamente dentro il loop interno del TestClient sotto).
    return create_engine(postgres_url)


@pytest.fixture
def api_client(api_engine: AsyncEngine) -> Iterator[TestClient]:
    """TestClient con la dependency injection reale fino al DB: si sovrascrive
    solo `get_session` (per puntare al Postgres del container invece che a
    quello di produzione/dev), non `get_price_repository` — il repository,
    la sessione e le query eseguite sono esattamente quelli usati a runtime.
    """
    session_factory = create_session_factory(api_engine)

    async def override_get_session() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            else:
                await session.commit()

    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
