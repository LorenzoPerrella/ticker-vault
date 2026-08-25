"""Unit test per `PriceRepository` — sessione SQLAlchemy mockata, nessun DB reale.

Verificano la logica del repository (routing dei metodi, traduzione degli
errori, gestione della paginazione), non la correttezza SQL: quella è compito
dei test di integrazione contro Postgres reale (`tests/integration`).
"""

import datetime
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from price_service.db.models import Price
from price_service.repositories.price_repository import DuplicatePriceError, PriceRepository


@pytest.fixture
def session() -> MagicMock:
    return MagicMock(spec=AsyncSession)


@pytest.fixture
def repo(session: MagicMock) -> PriceRepository:
    return PriceRepository(session)


def _integrity_error() -> IntegrityError:
    return IntegrityError("INSERT INTO prices ...", {}, Exception("duplicate key"))


class TestCreate:
    async def test_create_adds_and_flushes(self, repo: PriceRepository, session: MagicMock) -> None:
        price = await repo.create(
            symbol="AAPL", price_date=datetime.date(2026, 1, 2), value=Decimal("190.5")
        )

        session.add.assert_called_once()
        added = session.add.call_args.args[0]
        assert added is price
        assert isinstance(added, Price)
        assert added.symbol == "AAPL"
        session.flush.assert_awaited_once()

    async def test_create_duplicate_raises_domain_error(
        self, repo: PriceRepository, session: MagicMock
    ) -> None:
        session.flush.side_effect = _integrity_error()

        with pytest.raises(DuplicatePriceError) as exc_info:
            await repo.create(
                symbol="AAPL", price_date=datetime.date(2026, 1, 2), value=Decimal("190.5")
            )

        assert exc_info.value.symbol == "AAPL"
        assert exc_info.value.price_date == datetime.date(2026, 1, 2)


class TestGet:
    async def test_get_delegates_to_session(
        self, repo: PriceRepository, session: MagicMock
    ) -> None:
        expected = Price(
            id=1, symbol="AAPL", price_date=datetime.date(2026, 1, 2), value=Decimal("1")
        )
        session.get.return_value = expected

        result = await repo.get(1)

        session.get.assert_awaited_once_with(Price, 1)
        assert result is expected

    async def test_get_missing_returns_none(
        self, repo: PriceRepository, session: MagicMock
    ) -> None:
        session.get.return_value = None

        assert await repo.get(999) is None


class TestList:
    async def test_list_returns_items_and_total(
        self, repo: PriceRepository, session: MagicMock
    ) -> None:
        rows = [
            Price(id=1, symbol="AAPL", price_date=datetime.date(2026, 1, 2), value=Decimal("1"))
        ]
        count_result = MagicMock()
        count_result.scalar_one.return_value = 1
        rows_result = MagicMock()
        rows_result.scalars.return_value.all.return_value = rows
        session.execute.side_effect = [count_result, rows_result]

        items, total = await repo.list(symbol="AAPL")

        assert items == rows
        assert total == 1
        assert session.execute.await_count == 2

    async def test_list_default_pagination_empty(
        self, repo: PriceRepository, session: MagicMock
    ) -> None:
        count_result = MagicMock()
        count_result.scalar_one.return_value = 0
        rows_result = MagicMock()
        rows_result.scalars.return_value.all.return_value = []
        session.execute.side_effect = [count_result, rows_result]

        items, total = await repo.list()

        assert items == []
        assert total == 0


class TestUpdate:
    async def test_update_missing_returns_none(
        self, repo: PriceRepository, session: MagicMock
    ) -> None:
        session.get.return_value = None

        assert await repo.update(1, value=Decimal("1")) is None
        session.flush.assert_not_awaited()

    async def test_update_applies_only_given_fields(
        self, repo: PriceRepository, session: MagicMock
    ) -> None:
        existing = Price(
            id=1, symbol="AAPL", price_date=datetime.date(2026, 1, 2), value=Decimal("190.5")
        )
        session.get.return_value = existing

        result = await repo.update(1, value=Decimal("200.0"))

        assert result is existing
        assert existing.value == Decimal("200.0")
        assert existing.symbol == "AAPL"  # non toccato
        session.flush.assert_awaited_once()

    async def test_update_duplicate_raises_domain_error_with_target_values(
        self, repo: PriceRepository, session: MagicMock
    ) -> None:
        existing = Price(
            id=2, symbol="AAPL", price_date=datetime.date(2026, 1, 3), value=Decimal("1")
        )
        session.get.return_value = existing
        session.flush.side_effect = _integrity_error()

        with pytest.raises(DuplicatePriceError) as exc_info:
            await repo.update(2, price_date=datetime.date(2026, 1, 2))

        # Il target richiesto (2026-01-02) è quello riportato, non il valore
        # originale (2026-01-03) del record prima della modifica.
        assert exc_info.value.symbol == "AAPL"
        assert exc_info.value.price_date == datetime.date(2026, 1, 2)


class TestDelete:
    async def test_delete_missing_returns_false(
        self, repo: PriceRepository, session: MagicMock
    ) -> None:
        session.get.return_value = None

        assert await repo.delete(1) is False
        session.delete.assert_not_awaited()

    async def test_delete_existing_returns_true(
        self, repo: PriceRepository, session: MagicMock
    ) -> None:
        existing = Price(
            id=1, symbol="AAPL", price_date=datetime.date(2026, 1, 2), value=Decimal("1")
        )
        session.get.return_value = existing

        assert await repo.delete(1) is True
        session.delete.assert_awaited_once_with(existing)
        session.flush.assert_awaited_once()
