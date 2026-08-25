"""Unit test per il router `/api/v1/prices` — repository mockato, nessun DB reale.

Verificano il routing HTTP (status code, serializzazione, validazione Pydantic),
non la logica del repository (coperta da `test_price_repository.py`) né la SQL
reale (coperta dai test di integrazione).
"""

import datetime
from collections.abc import Iterator
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from price_service.db.models import Price
from price_service.deps import get_price_repository
from price_service.main import app
from price_service.repositories.price_repository import DuplicatePriceError


@pytest.fixture
def repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def client(repo: AsyncMock) -> Iterator[TestClient]:
    app.dependency_overrides[get_price_repository] = lambda: repo
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _price(
    *,
    id: int = 1,
    symbol: str = "AAPL",
    price_date: datetime.date = datetime.date(2026, 1, 2),
    value: Decimal = Decimal("190.5"),
) -> Price:
    return Price(
        id=id,
        symbol=symbol,
        price_date=price_date,
        value=value,
        created_at=datetime.datetime(2026, 1, 2, 12, 0, tzinfo=datetime.UTC),
    )


class TestCreate:
    def test_create_success(self, client: TestClient, repo: AsyncMock) -> None:
        repo.create.return_value = _price()

        response = client.post(
            "/api/v1/prices",
            json={"symbol": "AAPL", "price_date": "2026-01-02", "value": "190.5"},
        )

        assert response.status_code == 201
        body = response.json()
        assert body["symbol"] == "AAPL"
        assert body["id"] == 1
        repo.create.assert_awaited_once_with(
            symbol="AAPL", price_date=datetime.date(2026, 1, 2), value=Decimal("190.5")
        )

    def test_create_duplicate_returns_409(self, client: TestClient, repo: AsyncMock) -> None:
        repo.create.side_effect = DuplicatePriceError("AAPL", datetime.date(2026, 1, 2))

        response = client.post(
            "/api/v1/prices",
            json={"symbol": "AAPL", "price_date": "2026-01-02", "value": "190.5"},
        )

        assert response.status_code == 409

    def test_create_invalid_value_returns_422(self, client: TestClient, repo: AsyncMock) -> None:
        response = client.post(
            "/api/v1/prices",
            json={"symbol": "AAPL", "price_date": "2026-01-02", "value": "-1"},
        )

        assert response.status_code == 422
        repo.create.assert_not_awaited()


class TestList:
    def test_list_returns_page(self, client: TestClient, repo: AsyncMock) -> None:
        repo.list.return_value = ([_price()], 1)

        response = client.get("/api/v1/prices", params={"symbol": "AAPL"})

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert len(body["items"]) == 1
        assert body["items"][0]["symbol"] == "AAPL"
        repo.list.assert_awaited_once_with(
            symbol="AAPL", date_from=None, date_to=None, limit=50, offset=0
        )

    def test_list_rejects_limit_over_max(self, client: TestClient, repo: AsyncMock) -> None:
        response = client.get("/api/v1/prices", params={"limit": 1000})

        assert response.status_code == 422


class TestGet:
    def test_get_found(self, client: TestClient, repo: AsyncMock) -> None:
        repo.get.return_value = _price()

        response = client.get("/api/v1/prices/1")

        assert response.status_code == 200
        assert response.json()["id"] == 1

    def test_get_missing_returns_404(self, client: TestClient, repo: AsyncMock) -> None:
        repo.get.return_value = None

        response = client.get("/api/v1/prices/999")

        assert response.status_code == 404


class TestUpdate:
    def test_update_success(self, client: TestClient, repo: AsyncMock) -> None:
        repo.update.return_value = _price(value=Decimal("200.0"))

        response = client.put("/api/v1/prices/1", json={"value": "200.0"})

        assert response.status_code == 200
        assert response.json()["value"] == "200.0"

    def test_update_missing_returns_404(self, client: TestClient, repo: AsyncMock) -> None:
        repo.update.return_value = None

        response = client.put("/api/v1/prices/999", json={"value": "1"})

        assert response.status_code == 404

    def test_update_duplicate_returns_409(self, client: TestClient, repo: AsyncMock) -> None:
        repo.update.side_effect = DuplicatePriceError("AAPL", datetime.date(2026, 1, 2))

        response = client.put("/api/v1/prices/1", json={"price_date": "2026-01-02"})

        assert response.status_code == 409


class TestDelete:
    def test_delete_success(self, client: TestClient, repo: AsyncMock) -> None:
        repo.delete.return_value = True

        response = client.delete("/api/v1/prices/1")

        assert response.status_code == 204

    def test_delete_missing_returns_404(self, client: TestClient, repo: AsyncMock) -> None:
        repo.delete.return_value = False

        response = client.delete("/api/v1/prices/999")

        assert response.status_code == 404
