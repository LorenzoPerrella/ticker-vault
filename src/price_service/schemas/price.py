"""Schema Pydantic per l'API dei prezzi."""

import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class PriceBase(BaseModel):
    symbol: str = Field(min_length=1, max_length=16)
    price_date: datetime.date
    value: Decimal = Field(gt=0)


class PriceCreate(PriceBase):
    pass


class PriceUpdate(BaseModel):
    """Tutti i campi opzionali: solo quelli forniti vengono aggiornati (PUT parziale)."""

    symbol: str | None = Field(default=None, min_length=1, max_length=16)
    price_date: datetime.date | None = None
    value: Decimal | None = Field(default=None, gt=0)


class PriceRead(PriceBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime.datetime


class PricePage(BaseModel):
    """Pagina di risultati per `GET /api/v1/prices`."""

    items: list[PriceRead]
    total: int
    limit: int
    offset: int
