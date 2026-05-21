from sqlalchemy.orm import Session
from datetime import date, timedelta
from typing import List, Dict
from models import Position, PortfolioSnapshot
from services.prices import get_current_price, get_prices_batch
from collections import defaultdict


def calculate_position_metrics(position: Position, current_price: float) -> dict:
    """Calculate metrics for a single position."""
    current_value = position.shares * current_price
    gain_loss = current_value - position.cost_basis
    gain_loss_percent = (gain_loss / position.cost_basis * 100) if position.cost_basis > 0 else 0

    return {
        "current_price": round(current_price, 2),
        "current_value": round(current_value, 2),
        "gain_loss": round(gain_loss, 2),
        "gain_loss_percent": round(gain_loss_percent, 2)
    }


def get_portfolio_summary(db: Session) -> dict:
    """Calculate portfolio summary with allocation breakdown."""
    positions = db.query(Position).all()

    if not positions:
        return {
            "total_value": 0,
            "total_cost": 0,
            "total_gain_loss": 0,
            "total_gain_loss_percent": 0,
            "positions_count": 0,
            "allocation": []
        }

    # Fetch all prices
    symbols = list(set(p.symbol for p in positions))
    prices = get_prices_batch(symbols)

    total_value = 0
    total_cost = 0
    allocation_data: Dict[str, dict] = defaultdict(lambda: {"value": 0, "symbols": []})

    for position in positions:
        price_data = prices.get(position.symbol.upper())
        if price_data:
            current_value = position.shares * price_data["price"]
            total_value += current_value
            total_cost += position.cost_basis

            asset_type = position.asset_type
            allocation_data[asset_type]["value"] += current_value
            if position.symbol not in allocation_data[asset_type]["symbols"]:
                allocation_data[asset_type]["symbols"].append(position.symbol)

    total_gain_loss = total_value - total_cost
    total_gain_loss_percent = (total_gain_loss / total_cost * 100) if total_cost > 0 else 0

    # Calculate allocation percentages
    allocation = [
        {
            "asset_type": asset_type,
            "value": round(data["value"], 2),
            "percentage": round(data["value"] / total_value * 100, 2) if total_value > 0 else 0,
            "symbols": data["symbols"]
        }
        for asset_type, data in allocation_data.items()
    ]

    return {
        "total_value": round(total_value, 2),
        "total_cost": round(total_cost, 2),
        "total_gain_loss": round(total_gain_loss, 2),
        "total_gain_loss_percent": round(total_gain_loss_percent, 2),
        "positions_count": len(positions),
        "allocation": allocation
    }


def save_daily_snapshot(db: Session):
    """Save a daily portfolio snapshot."""
    today = date.today()

    # Check if snapshot already exists for today
    existing = db.query(PortfolioSnapshot).filter(PortfolioSnapshot.date == today).first()
    if existing:
        return existing

    summary = get_portfolio_summary(db)

    # Get yesterday's snapshot for daily return calculation
    yesterday = today - timedelta(days=1)
    yesterday_snapshot = db.query(PortfolioSnapshot).filter(
        PortfolioSnapshot.date == yesterday
    ).first()

    daily_return = 0
    if yesterday_snapshot and yesterday_snapshot.total_value > 0:
        daily_return = (summary["total_value"] - yesterday_snapshot.total_value) / yesterday_snapshot.total_value * 100

    snapshot = PortfolioSnapshot(
        date=today,
        total_value=summary["total_value"],
        total_cost=summary["total_cost"],
        daily_return=round(daily_return, 2)
    )

    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)

    return snapshot


def get_portfolio_history(db: Session, days: int = 30) -> List[dict]:
    """Get portfolio history for the last N days."""
    start_date = date.today() - timedelta(days=days)

    snapshots = db.query(PortfolioSnapshot).filter(
        PortfolioSnapshot.date >= start_date
    ).order_by(PortfolioSnapshot.date).all()

    return [
        {
            "date": s.date,
            "total_value": s.total_value,
            "total_cost": s.total_cost,
            "daily_return": s.daily_return
        }
        for s in snapshots
    ]
