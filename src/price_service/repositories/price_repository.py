"""Repository per l'accesso ai dati dei prezzi.

Le scritture fanno `flush`, non `commit`: il confine della transazione è
responsabilità del chiamante. Il design atteso è una sessione per richiesta
HTTP (dependency in `deps.py`, Fase 3) che fa commit a fine richiesta e
rollback se propaga un'eccezione — quindi se una scrittura qui fallisce
(es. `DuplicatePriceError`), l'intera richiesta corrente termina in errore:
non si tenta di recuperare la sessione per operazioni successive nella
stessa unità di lavoro, che qui non è un caso d'uso reale.
"""

import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from price_service.db.models import Price


class DuplicatePriceError(Exception):
    """Sollevato quando esiste già un prezzo per lo stesso `symbol`/`price_date`."""

    def __init__(self, symbol: str, price_date: datetime.date) -> None:
        self.symbol = symbol
        self.price_date = price_date
        super().__init__(f"Prezzo già esistente per {symbol} in data {price_date}")


class PriceRepository:
    """Operazioni CRUD sulla tabella `prices`, su una singola `AsyncSession`."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, *, symbol: str, price_date: datetime.date, value: Decimal) -> Price:
        price = Price(symbol=symbol, price_date=price_date, value=value)
        self._session.add(price)
        try:
            await self._session.flush()
        except IntegrityError as exc:
            raise DuplicatePriceError(symbol, price_date) from exc
        return price

    async def get(self, price_id: int) -> Price | None:
        return await self._session.get(Price, price_id)

    async def list(
        self,
        *,
        symbol: str | None = None,
        date_from: datetime.date | None = None,
        date_to: datetime.date | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Price], int]:
        filters = []
        if symbol is not None:
            filters.append(Price.symbol == symbol)
        if date_from is not None:
            filters.append(Price.price_date >= date_from)
        if date_to is not None:
            filters.append(Price.price_date <= date_to)

        count_stmt = select(func.count()).select_from(Price).where(*filters)
        total = (await self._session.execute(count_stmt)).scalar_one()

        stmt = (
            select(Price)
            .where(*filters)
            .order_by(Price.price_date.desc(), Price.symbol)
            .limit(limit)
            .offset(offset)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return list(rows), total

    async def update(
        self,
        price_id: int,
        *,
        symbol: str | None = None,
        price_date: datetime.date | None = None,
        value: Decimal | None = None,
    ) -> Price | None:
        price = await self.get(price_id)
        if price is None:
            return None

        # Catturati prima della mutazione, per il messaggio d'errore: se il
        # flush sotto fallisce e viene propagato, un chiamante che ispezionasse
        # di nuovo `price` dopo un rollback vedrebbe comunque gli attributi
        # scaduti ricaricare i valori originali, non quelli richiesti.
        target_symbol = symbol if symbol is not None else price.symbol
        target_price_date = price_date if price_date is not None else price.price_date

        if symbol is not None:
            price.symbol = symbol
        if price_date is not None:
            price.price_date = price_date
        if value is not None:
            price.value = value
        try:
            await self._session.flush()
        except IntegrityError as exc:
            raise DuplicatePriceError(target_symbol, target_price_date) from exc
        return price

    async def delete(self, price_id: int) -> bool:
        price = await self.get(price_id)
        if price is None:
            return False
        await self._session.delete(price)
        await self._session.flush()
        return True
