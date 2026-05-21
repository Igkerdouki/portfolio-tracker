"""Portfolio summary and history endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from schemas import PortfolioSummary, PortfolioHistoryItem
from services.portfolio import get_portfolio_summary, get_portfolio_history, save_daily_snapshot

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("/summary", response_model=PortfolioSummary)
def portfolio_summary(db: Session = Depends(get_db)):
    """Get portfolio summary with total value, P&L, and allocation."""
    return get_portfolio_summary(db)


@router.get("/history", response_model=List[PortfolioHistoryItem])
def portfolio_history(days: int = 30, db: Session = Depends(get_db)):
    """Get portfolio history for the specified number of days."""
    return get_portfolio_history(db, days)


@router.post("/snapshot")
def create_snapshot(db: Session = Depends(get_db)):
    """Create a daily portfolio snapshot."""
    snapshot = save_daily_snapshot(db)
    return {
        "date": snapshot.date,
        "total_value": snapshot.total_value,
        "total_cost": snapshot.total_cost,
        "daily_return": snapshot.daily_return
    }
