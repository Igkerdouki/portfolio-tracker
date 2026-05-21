"""Position management endpoints."""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from models import Position
from schemas import PositionCreate, PositionUpdate, PositionResponse
from services.prices import get_current_price, get_prices_batch
from services.portfolio import calculate_position_metrics

router = APIRouter(prefix="/positions", tags=["positions"])


@router.get("", response_model=List[PositionResponse])
def list_positions(db: Session = Depends(get_db)):
    """List all positions with current prices and metrics."""
    positions = db.query(Position).all()

    if not positions:
        return []

    # Fetch all prices in batch
    symbols = list(set(p.symbol for p in positions))
    prices = get_prices_batch(symbols)

    result = []
    for position in positions:
        price_data = prices.get(position.symbol.upper())

        # Calculate avg cost as fallback price
        avg_cost = position.cost_basis / position.shares if position.shares > 0 else 0

        pos_dict = {
            "id": position.id,
            "symbol": position.symbol,
            "shares": position.shares,
            "cost_basis": position.cost_basis,
            "purchase_date": position.purchase_date,
            "asset_type": position.asset_type,
            "current_price": round(avg_cost, 2),
            "current_value": round(position.cost_basis, 2),
            "gain_loss": 0.0,
            "gain_loss_percent": 0.0
        }

        if price_data:
            metrics = calculate_position_metrics(position, price_data["price"])
            pos_dict.update(metrics)

        result.append(pos_dict)

    return result


@router.post("", response_model=PositionResponse, status_code=201)
def create_position(position: PositionCreate, db: Session = Depends(get_db)):
    """Create a new position."""
    db_position = Position(
        symbol=position.symbol.upper(),
        shares=position.shares,
        cost_basis=position.cost_basis,
        purchase_date=position.purchase_date,
        asset_type=position.asset_type.value
    )

    db.add(db_position)
    db.commit()
    db.refresh(db_position)

    price_data = get_current_price(db_position.symbol)

    result = {
        "id": db_position.id,
        "symbol": db_position.symbol,
        "shares": db_position.shares,
        "cost_basis": db_position.cost_basis,
        "purchase_date": db_position.purchase_date,
        "asset_type": db_position.asset_type,
        "current_price": None,
        "current_value": None,
        "gain_loss": None,
        "gain_loss_percent": None
    }

    if price_data:
        metrics = calculate_position_metrics(db_position, price_data["price"])
        result.update(metrics)

    return result


@router.get("/{position_id}", response_model=PositionResponse)
def get_position(position_id: int, db: Session = Depends(get_db)):
    """Get a specific position by ID."""
    position = db.query(Position).filter(Position.id == position_id).first()

    if not position:
        raise HTTPException(status_code=404, detail="Position not found")

    price_data = get_current_price(position.symbol)

    result = {
        "id": position.id,
        "symbol": position.symbol,
        "shares": position.shares,
        "cost_basis": position.cost_basis,
        "purchase_date": position.purchase_date,
        "asset_type": position.asset_type,
        "current_price": None,
        "current_value": None,
        "gain_loss": None,
        "gain_loss_percent": None
    }

    if price_data:
        metrics = calculate_position_metrics(position, price_data["price"])
        result.update(metrics)

    return result


@router.put("/{position_id}", response_model=PositionResponse)
def update_position(position_id: int, position: PositionUpdate, db: Session = Depends(get_db)):
    """Update an existing position."""
    db_position = db.query(Position).filter(Position.id == position_id).first()

    if not db_position:
        raise HTTPException(status_code=404, detail="Position not found")

    update_data = position.model_dump(exclude_unset=True)

    if "symbol" in update_data:
        update_data["symbol"] = update_data["symbol"].upper()
    if "asset_type" in update_data:
        update_data["asset_type"] = update_data["asset_type"].value

    for field, value in update_data.items():
        setattr(db_position, field, value)

    db.commit()
    db.refresh(db_position)

    price_data = get_current_price(db_position.symbol)

    result = {
        "id": db_position.id,
        "symbol": db_position.symbol,
        "shares": db_position.shares,
        "cost_basis": db_position.cost_basis,
        "purchase_date": db_position.purchase_date,
        "asset_type": db_position.asset_type,
        "current_price": None,
        "current_value": None,
        "gain_loss": None,
        "gain_loss_percent": None
    }

    if price_data:
        metrics = calculate_position_metrics(db_position, price_data["price"])
        result.update(metrics)

    return result


@router.delete("/{position_id}", status_code=204)
def delete_position(position_id: int, db: Session = Depends(get_db)):
    """Delete a position."""
    position = db.query(Position).filter(Position.id == position_id).first()

    if not position:
        raise HTTPException(status_code=404, detail="Position not found")

    db.delete(position)
    db.commit()
