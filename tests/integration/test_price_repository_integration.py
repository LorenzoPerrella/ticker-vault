"""Test di integrazione per `PriceRepository` contro Postgres reale (testcontainers).

Verificano ciò che i mock non possono: vincoli reali dello schema (UNIQUE),
precisione di `Numeric`, ordinamento e filtri effettivi lato SQL. La logica
di routing/traduzione errori è già coperta dagli unit test.
"""

import datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from price_service.repositories.price_repository import DuplicatePriceError, PriceRepository


async def test_create_assigns_id_and_created_at(db_session: AsyncSession) -> None:
    repo = PriceRepository(db_session)

    price = await repo.create(
        symbol="AAPL", price_date=datetime.date(2026, 1, 2), value=Decimal("190.500000")
    )

    assert price.id is not None
    assert price.created_at is not None


async def test_unique_constraint_enforced_by_db(db_session: AsyncSession) -> None:
    repo = PriceRepository(db_session)
    await repo.create(symbol="AAPL", price_date=datetime.date(2026, 1, 2), value=Decimal("1"))

    try:
        await repo.create(symbol="AAPL", price_date=datetime.date(2026, 1, 2), value=Decimal("2"))
        raise AssertionError("doveva sollevare DuplicatePriceError")
    except DuplicatePriceError:
        pass


async def test_numeric_precision_round_trips_through_db(db_session: AsyncSession) -> None:
    repo = PriceRepository(db_session)
    value = Decimal("190.123456")

    created = await repo.create(symbol="AAPL", price_date=datetime.date(2026, 1, 2), value=value)
    # `refresh` forza una SELECT reale dal DB (a differenza di `expire_all` +
    # `get`, che su un oggetto già in identity map innesca un lazy-load
    # dell'attributo scaduto — non supportato in async fuori da un contesto
    # greenlet esplicito: solleverebbe `MissingGreenlet`).
    await db_session.refresh(created)

    assert created.value == value


async def test_list_filters_by_symbol_and_date_range(db_session: AsyncSession) -> None:
    repo = PriceRepository(db_session)
    await repo.create(symbol="AAPL", price_date=datetime.date(2026, 1, 1), value=Decimal("1"))
    await repo.create(symbol="AAPL", price_date=datetime.date(2026, 1, 2), value=Decimal("2"))
    await repo.create(symbol="AAPL", price_date=datetime.date(2026, 1, 3), value=Decimal("3"))
    await repo.create(symbol="MSFT", price_date=datetime.date(2026, 1, 2), value=Decimal("4"))

    items, total = await repo.list(
        symbol="AAPL", date_from=datetime.date(2026, 1, 2), date_to=datetime.date(2026, 1, 3)
    )

    assert total == 2
    assert {item.price_date for item in items} == {
        datetime.date(2026, 1, 2),
        datetime.date(2026, 1, 3),
    }


async def test_list_orders_by_price_date_desc_then_symbol(db_session: AsyncSession) -> None:
    repo = PriceRepository(db_session)
    await repo.create(symbol="MSFT", price_date=datetime.date(2026, 1, 2), value=Decimal("1"))
    await repo.create(symbol="AAPL", price_date=datetime.date(2026, 1, 2), value=Decimal("2"))
    await repo.create(symbol="GOOG", price_date=datetime.date(2026, 1, 1), value=Decimal("3"))

    items, _total = await repo.list()

    assert [(i.price_date, i.symbol) for i in items] == [
        (datetime.date(2026, 1, 2), "AAPL"),
        (datetime.date(2026, 1, 2), "MSFT"),
        (datetime.date(2026, 1, 1), "GOOG"),
    ]


async def test_list_pagination(db_session: AsyncSession) -> None:
    repo = PriceRepository(db_session)
    for day in range(1, 6):
        await repo.create(symbol="AAPL", price_date=datetime.date(2026, 1, day), value=Decimal(day))

    page1, total = await repo.list(limit=2, offset=0)
    page2, _ = await repo.list(limit=2, offset=2)

    assert total == 5
    assert len(page1) == 2
    assert len(page2) == 2
    assert {i.id for i in page1}.isdisjoint({i.id for i in page2})


async def test_update_persists_to_db(db_session: AsyncSession) -> None:
    repo = PriceRepository(db_session)
    created = await repo.create(
        symbol="AAPL", price_date=datetime.date(2026, 1, 2), value=Decimal("1")
    )

    updated = await repo.update(created.id, value=Decimal("999.999999"))
    assert updated is not None
    await db_session.refresh(updated)

    assert updated.value == Decimal("999.999999")


async def test_delete_removes_row_from_db(db_session: AsyncSession) -> None:
    repo = PriceRepository(db_session)
    created = await repo.create(
        symbol="AAPL", price_date=datetime.date(2026, 1, 2), value=Decimal("1")
    )

    deleted = await repo.delete(created.id)

    assert deleted is True
    # Nessun `refresh`/`expire_all` necessario qui: `delete` rimuove l'oggetto
    # dalla identity map, quindi `get` esegue comunque una SELECT reale.
    assert await repo.get(created.id) is None
