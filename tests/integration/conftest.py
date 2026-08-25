"""Fixture condivise per i test di integrazione: Postgres reale via testcontainers.

Il container e le migrazioni Alembic sono a livello di sessione (costosi, una
volta sola); engine e sessione sono per-test (evita di condividere un
AsyncEngine/pool asyncpg tra event loop diversi di test distinti) con rollback
a fine test per isolamento reciproco.
"""

from collections.abc import AsyncGenerator, Generator

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy.ext.asyncio import AsyncSession
from testcontainers.community.postgres import PostgresContainer

from price_service.db.base import create_engine, create_session_factory


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
