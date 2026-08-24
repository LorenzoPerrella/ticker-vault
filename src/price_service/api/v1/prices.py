"""Router CRUD per `/api/v1/prices`."""

import datetime

from fastapi import APIRouter, HTTPException, Query, status

from price_service.deps import PriceRepositoryDep
from price_service.repositories.price_repository import DuplicatePriceError
from price_service.schemas.price import PriceCreate, PricePage, PriceRead, PriceUpdate

router = APIRouter(prefix="/prices", tags=["prices"])


@router.post("", response_model=PriceRead, status_code=status.HTTP_201_CREATED)
async def create_price(payload: PriceCreate, repo: PriceRepositoryDep) -> PriceRead:
    try:
        price = await repo.create(
            symbol=payload.symbol, price_date=payload.price_date, value=payload.value
        )
    except DuplicatePriceError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return PriceRead.model_validate(price)


@router.get("", response_model=PricePage)
async def list_prices(
    repo: PriceRepositoryDep,
    symbol: str | None = None,
    date_from: datetime.date | None = None,
    date_to: datetime.date | None = None,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> PricePage:
    items, total = await repo.list(
        symbol=symbol, date_from=date_from, date_to=date_to, limit=limit, offset=offset
    )
    return PricePage(
        items=[PriceRead.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{price_id}", response_model=PriceRead)
async def get_price(price_id: int, repo: PriceRepositoryDep) -> PriceRead:
    price = await repo.get(price_id)
    if price is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="price not found")
    return PriceRead.model_validate(price)


@router.put("/{price_id}", response_model=PriceRead)
async def update_price(price_id: int, payload: PriceUpdate, repo: PriceRepositoryDep) -> PriceRead:
    try:
        price = await repo.update(
            price_id,
            symbol=payload.symbol,
            price_date=payload.price_date,
            value=payload.value,
        )
    except DuplicatePriceError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if price is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="price not found")
    return PriceRead.model_validate(price)


@router.delete("/{price_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_price(price_id: int, repo: PriceRepositoryDep) -> None:
    deleted = await repo.delete(price_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="price not found")
