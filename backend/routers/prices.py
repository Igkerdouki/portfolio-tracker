"""Price lookup endpoints."""

from fastapi import APIRouter, HTTPException

from schemas import PriceResponse
from services.prices import get_current_price

router = APIRouter(prefix="/prices", tags=["prices"])


@router.get("/{symbol}", response_model=PriceResponse)
def get_price(symbol: str):
    """Get current price for a symbol."""
    price_data = get_current_price(symbol.upper())

    if not price_data:
        raise HTTPException(status_code=404, detail=f"Price not found for {symbol}")

    return price_data
