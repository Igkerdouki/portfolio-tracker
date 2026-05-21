"""Interactive Brokers integration endpoints."""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import date

from database import get_db
from models import Position
from services.ibkr import ibkr_service

router = APIRouter(prefix="/ibkr", tags=["ibkr"])


@router.post("/connect")
def ibkr_connect(host: str = "127.0.0.1", port: int = 7497, client_id: int = 1):
    """
    Connect to Interactive Brokers TWS or IB Gateway.

    Ports:
    - TWS Live: 7496
    - TWS Paper: 7497
    - IB Gateway Live: 4001
    - IB Gateway Paper: 4002
    """
    try:
        success = ibkr_service.connect_sync(host, port, client_id)
        if success:
            return {"status": "connected", "host": host, "port": port}
        else:
            raise HTTPException(status_code=500, detail="Failed to connect to IBKR")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/disconnect")
def ibkr_disconnect():
    """Disconnect from Interactive Brokers."""
    ibkr_service.disconnect()
    return {"status": "disconnected"}


@router.get("/status")
def ibkr_status():
    """Check IBKR connection status."""
    return {"connected": ibkr_service.is_connected()}


@router.get("/positions")
def ibkr_positions():
    """Get positions from IBKR account."""
    if not ibkr_service.is_connected():
        raise HTTPException(status_code=400, detail="Not connected to IBKR. Call /ibkr/connect first.")

    try:
        positions = ibkr_service.get_positions()
        return {"positions": positions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/portfolio")
def ibkr_portfolio():
    """Get portfolio with market values from IBKR."""
    if not ibkr_service.is_connected():
        raise HTTPException(status_code=400, detail="Not connected to IBKR. Call /ibkr/connect first.")

    try:
        portfolio = ibkr_service.get_portfolio()
        return {"portfolio": portfolio}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/account")
def ibkr_account():
    """Get account summary from IBKR."""
    if not ibkr_service.is_connected():
        raise HTTPException(status_code=400, detail="Not connected to IBKR. Call /ibkr/connect first.")

    try:
        summary = ibkr_service.get_account_summary()
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync")
def ibkr_sync_positions(db: Session = Depends(get_db)):
    """Sync positions from IBKR to local database."""
    if not ibkr_service.is_connected():
        raise HTTPException(status_code=400, detail="Not connected to IBKR. Call /ibkr/connect first.")

    try:
        ibkr_positions = ibkr_service.get_positions()

        synced = 0
        for pos in ibkr_positions:
            if pos["shares"] == 0:
                continue

            # Check if position already exists (match by symbol AND currency)
            existing = db.query(Position).filter(
                Position.symbol == pos["symbol"],
                Position.currency == pos.get("currency", "USD")
            ).first()

            if existing:
                existing.shares = pos["shares"]
                existing.cost_basis = pos["cost_basis"]
            else:
                new_position = Position(
                    symbol=pos["symbol"],
                    shares=pos["shares"],
                    cost_basis=pos["cost_basis"],
                    purchase_date=date.today(),
                    asset_type=pos["asset_type"],
                    currency=pos.get("currency", "USD")
                )
                db.add(new_position)

            synced += 1

        db.commit()
        return {"status": "success", "positions_synced": synced}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
