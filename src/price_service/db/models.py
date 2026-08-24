"""Modelli ORM."""

import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from price_service.db.base import Base


class Price(Base):
    """Prezzo di chiusura di un titolo (`symbol`) in una data (`price_date`).

    Vincolo `UNIQUE(symbol, price_date)`: un solo prezzo per titolo per giorno.
    """

    __tablename__ = "prices"
    __table_args__ = (UniqueConstraint("symbol", "price_date", name="uq_prices_symbol_price_date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    symbol: Mapped[str] = mapped_column(String(16), index=True)
    price_date: Mapped[datetime.date]
    value: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"Price(id={self.id!r}, symbol={self.symbol!r}, price_date={self.price_date!r})"
