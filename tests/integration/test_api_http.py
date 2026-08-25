"""Test HTTP end-to-end: `TestClient` -> FastAPI -> dependency injection reale
-> `PriceRepository` -> `AsyncSession` -> Postgres reale (testcontainers).

A differenza di `tests/unit/test_api_prices.py` (repository mockato) e di
`test_price_repository_integration.py` (repository usato direttamente, senza
passare dall'HTTP), qui non si sovrascrive nulla del livello applicativo:
solo `get_session` punta al container invece che alle impostazioni di
produzione/dev. È la stessa filiera che gira davvero in produzione, dalla
richiesta HTTP fino alla riga nella tabella `prices`.
"""

from decimal import Decimal

from fastapi.testclient import TestClient

from tests.integration.conftest import SeededPrice


class TestHealthAndReady:
    def test_health_does_not_need_db(self, api_client: TestClient) -> None:
        response = api_client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_ready_checks_real_db(self, api_client: TestClient) -> None:
        response = api_client.get("/ready")

        assert response.status_code == 200
        assert response.json() == {"status": "ready"}


class TestList:
    def test_list_returns_seeded_prices(
        self, api_client: TestClient, seed_prices: list[SeededPrice]
    ) -> None:
        response = api_client.get("/api/v1/prices")

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 2
        assert {item["symbol"] for item in body["items"]} == {"AAPL", "MSFT"}

    def test_list_filters_by_symbol(
        self, api_client: TestClient, seed_prices: list[SeededPrice]
    ) -> None:
        response = api_client.get("/api/v1/prices", params={"symbol": "AAPL"})

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert body["items"][0]["symbol"] == "AAPL"


class TestGet:
    def test_get_by_id_returns_seeded_price(
        self, api_client: TestClient, seed_prices: list[SeededPrice]
    ) -> None:
        aapl = next(p for p in seed_prices if p.symbol == "AAPL")

        response = api_client.get(f"/api/v1/prices/{aapl.id}")

        assert response.status_code == 200
        body = response.json()
        assert body["symbol"] == "AAPL"
        assert Decimal(body["value"]) == aapl.value

    def test_get_missing_returns_404(
        self, api_client: TestClient, seed_prices: list[SeededPrice]
    ) -> None:
        response = api_client.get("/api/v1/prices/999999")

        assert response.status_code == 404


class TestCreate:
    def test_create_then_get_in_a_separate_request_persists(
        self, api_client: TestClient, seed_prices: list[SeededPrice]
    ) -> None:
        create_response = api_client.post(
            "/api/v1/prices",
            json={"symbol": "GOOG", "price_date": "2026-01-05", "value": "150.250000"},
        )
        assert create_response.status_code == 201
        new_id = create_response.json()["id"]

        # Richiesta separata: get_session crea una sessione nuova ad ogni
        # chiamata, quindi questo GET non può leggere da una identity map
        # condivisa con la POST — è una lettura reale dal DB.
        get_response = api_client.get(f"/api/v1/prices/{new_id}")

        assert get_response.status_code == 200
        assert get_response.json()["symbol"] == "GOOG"

    def test_create_duplicate_of_seeded_price_returns_409(
        self, api_client: TestClient, seed_prices: list[SeededPrice]
    ) -> None:
        aapl = next(p for p in seed_prices if p.symbol == "AAPL")

        response = api_client.post(
            "/api/v1/prices",
            json={
                "symbol": aapl.symbol,
                "price_date": aapl.price_date.isoformat(),
                "value": "1.0",
            },
        )

        assert response.status_code == 409


class TestUpdate:
    def test_update_persists_across_requests(
        self, api_client: TestClient, seed_prices: list[SeededPrice]
    ) -> None:
        aapl = next(p for p in seed_prices if p.symbol == "AAPL")

        put_response = api_client.put(f"/api/v1/prices/{aapl.id}", json={"value": "999.999999"})
        assert put_response.status_code == 200

        get_response = api_client.get(f"/api/v1/prices/{aapl.id}")
        assert Decimal(get_response.json()["value"]) == Decimal("999.999999")


class TestDelete:
    def test_delete_then_get_404_then_list_shrinks(
        self, api_client: TestClient, seed_prices: list[SeededPrice]
    ) -> None:
        msft = next(p for p in seed_prices if p.symbol == "MSFT")

        delete_response = api_client.delete(f"/api/v1/prices/{msft.id}")
        assert delete_response.status_code == 204

        get_response = api_client.get(f"/api/v1/prices/{msft.id}")
        assert get_response.status_code == 404

        list_response = api_client.get("/api/v1/prices")
        assert list_response.json()["total"] == 1


def test_full_crud_lifecycle_e2e_debug(
    api_client: TestClient, seed_prices: list[SeededPrice]
) -> None:
    """Un solo test che attraversa l'intero ciclo di vita in ordine narrativo,
    con stampe ad ogni passo — pensato per essere eseguito isolato in caso di
    debug, non per la copertura (quella la danno i test sopra):

        uv run pytest -s -k test_full_crud_lifecycle_e2e_debug

    `-s` mostra i print anche quando il test passa. Ogni passo stampa
    request/response prima di asserire, così un fallimento mostra subito
    l'intera sequenza fino al punto di rottura, senza dover rilanciare con
    più verbosità.
    """
    print(f"\n[seed] 2 record precaricati: {[(p.symbol, p.id) for p in seed_prices]}")

    print("[1] GET /health")
    r = api_client.get("/health")
    print(f"    -> {r.status_code} {r.json()}")
    assert r.status_code == 200

    print("[2] GET /ready (tocca il DB reale)")
    r = api_client.get("/ready")
    print(f"    -> {r.status_code} {r.json()}")
    assert r.status_code == 200

    print("[3] POST /api/v1/prices — crea un nuovo prezzo")
    payload = {"symbol": "TSLA", "price_date": "2026-02-10", "value": "245.750000"}
    r = api_client.post("/api/v1/prices", json=payload)
    print(f"    -> {r.status_code} {r.json()}")
    assert r.status_code == 201
    new_id = r.json()["id"]

    print(f"[4] GET /api/v1/prices/{new_id} — richiesta separata, deve trovarlo")
    r = api_client.get(f"/api/v1/prices/{new_id}")
    print(f"    -> {r.status_code} {r.json()}")
    assert r.status_code == 200
    assert r.json()["symbol"] == "TSLA"

    print("[5] POST duplicato (stesso symbol/price_date) — deve dare 409")
    r = api_client.post("/api/v1/prices", json=payload)
    print(f"    -> {r.status_code} {r.json()}")
    assert r.status_code == 409

    print(f"[6] PUT /api/v1/prices/{new_id} — aggiorna il valore")
    r = api_client.put(f"/api/v1/prices/{new_id}", json={"value": "250.000000"})
    print(f"    -> {r.status_code} {r.json()}")
    assert r.status_code == 200
    assert Decimal(r.json()["value"]) == Decimal("250.000000")

    print("[7] GET /api/v1/prices?symbol=TSLA — verifica il filtro")
    r = api_client.get("/api/v1/prices", params={"symbol": "TSLA"})
    print(f"    -> {r.status_code} total={r.json()['total']}")
    assert r.json()["total"] == 1

    print(f"[8] DELETE /api/v1/prices/{new_id}")
    r = api_client.delete(f"/api/v1/prices/{new_id}")
    print(f"    -> {r.status_code}")
    assert r.status_code == 204

    print(f"[9] GET /api/v1/prices/{new_id} — deve dare 404 dopo la cancellazione")
    r = api_client.get(f"/api/v1/prices/{new_id}")
    print(f"    -> {r.status_code}")
    assert r.status_code == 404

    print("[10] GET /api/v1/prices — solo i 2 record seminati devono restare")
    r = api_client.get("/api/v1/prices")
    print(f"    -> total={r.json()['total']}")
    assert r.json()["total"] == 2

    print("[OK] ciclo di vita completo verificato end-to-end.\n")
