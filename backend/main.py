from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
from datetime import date

from database import engine, get_db, Base
from models import Position, Transaction
from schemas import (
    PositionCreate, PositionUpdate, PositionResponse,
    TransactionCreate, TransactionResponse,
    PortfolioSummary, PortfolioHistoryItem, PriceResponse
)
from services.prices import get_current_price, get_prices_batch
from services.portfolio import (
    calculate_position_metrics, get_portfolio_summary,
    get_portfolio_history, save_daily_snapshot
)
from services.ibkr import ibkr_service

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Portfolio Tracker API",
    description="API for tracking investment portfolio performance",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"message": "Portfolio Tracker API", "version": "1.0.0"}


# Position endpoints
@app.get("/positions", response_model=List[PositionResponse])
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

        pos_dict = {
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
            pos_dict.update(metrics)

        result.append(pos_dict)

    return result


@app.post("/positions", response_model=PositionResponse, status_code=201)
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

    # Fetch current price
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


@app.get("/positions/{position_id}", response_model=PositionResponse)
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


@app.put("/positions/{position_id}", response_model=PositionResponse)
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


@app.delete("/positions/{position_id}", status_code=204)
def delete_position(position_id: int, db: Session = Depends(get_db)):
    """Delete a position."""
    position = db.query(Position).filter(Position.id == position_id).first()

    if not position:
        raise HTTPException(status_code=404, detail="Position not found")

    db.delete(position)
    db.commit()


# Portfolio endpoints
@app.get("/portfolio/summary", response_model=PortfolioSummary)
def portfolio_summary(db: Session = Depends(get_db)):
    """Get portfolio summary with total value, P&L, and allocation."""
    return get_portfolio_summary(db)


@app.get("/portfolio/history", response_model=List[PortfolioHistoryItem])
def portfolio_history(days: int = 30, db: Session = Depends(get_db)):
    """Get portfolio history for the specified number of days."""
    return get_portfolio_history(db, days)


@app.post("/portfolio/snapshot")
def create_snapshot(db: Session = Depends(get_db)):
    """Create a daily portfolio snapshot."""
    snapshot = save_daily_snapshot(db)
    return {
        "date": snapshot.date,
        "total_value": snapshot.total_value,
        "total_cost": snapshot.total_cost,
        "daily_return": snapshot.daily_return
    }


# Price endpoints
@app.get("/prices/{symbol}", response_model=PriceResponse)
def get_price(symbol: str):
    """Get current price for a symbol."""
    price_data = get_current_price(symbol.upper())

    if not price_data:
        raise HTTPException(status_code=404, detail=f"Price not found for {symbol}")

    return price_data


# Transaction endpoints
@app.get("/transactions", response_model=List[TransactionResponse])
def list_transactions(symbol: str = None, db: Session = Depends(get_db)):
    """List all transactions, optionally filtered by symbol."""
    query = db.query(Transaction)

    if symbol:
        query = query.filter(Transaction.symbol == symbol.upper())

    return query.order_by(Transaction.date.desc()).all()


@app.post("/transactions", response_model=TransactionResponse, status_code=201)
def create_transaction(transaction: TransactionCreate, db: Session = Depends(get_db)):
    """Record a new transaction."""
    db_transaction = Transaction(
        symbol=transaction.symbol.upper(),
        shares=transaction.shares,
        price=transaction.price,
        date=transaction.date,
        transaction_type=transaction.transaction_type.value
    )

    db.add(db_transaction)
    db.commit()
    db.refresh(db_transaction)

    return db_transaction


# IBKR Integration endpoints
@app.post("/ibkr/connect")
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


@app.post("/ibkr/disconnect")
def ibkr_disconnect():
    """Disconnect from Interactive Brokers."""
    ibkr_service.disconnect()
    return {"status": "disconnected"}


@app.get("/ibkr/status")
def ibkr_status():
    """Check IBKR connection status."""
    return {"connected": ibkr_service.is_connected()}


@app.get("/ibkr/positions")
def ibkr_positions():
    """Get positions from IBKR account."""
    if not ibkr_service.is_connected():
        raise HTTPException(status_code=400, detail="Not connected to IBKR. Call /ibkr/connect first.")

    try:
        positions = ibkr_service.get_positions()
        return {"positions": positions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/ibkr/portfolio")
def ibkr_portfolio():
    """Get portfolio with market values from IBKR."""
    if not ibkr_service.is_connected():
        raise HTTPException(status_code=400, detail="Not connected to IBKR. Call /ibkr/connect first.")

    try:
        portfolio = ibkr_service.get_portfolio()
        return {"portfolio": portfolio}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/ibkr/account")
def ibkr_account():
    """Get account summary from IBKR."""
    if not ibkr_service.is_connected():
        raise HTTPException(status_code=400, detail="Not connected to IBKR. Call /ibkr/connect first.")

    try:
        summary = ibkr_service.get_account_summary()
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ibkr/sync")
def ibkr_sync_positions(db: Session = Depends(get_db)):
    """Sync positions from IBKR to local database."""
    if not ibkr_service.is_connected():
        raise HTTPException(status_code=400, detail="Not connected to IBKR. Call /ibkr/connect first.")

    try:
        ibkr_positions = ibkr_service.get_portfolio()

        synced = 0
        for pos in ibkr_positions:
            if pos["shares"] == 0:
                continue

            # Check if position already exists
            existing = db.query(Position).filter(Position.symbol == pos["symbol"]).first()

            if existing:
                # Update existing position
                existing.shares = pos["shares"]
                existing.cost_basis = pos["cost_basis"]
            else:
                # Create new position
                new_position = Position(
                    symbol=pos["symbol"],
                    shares=pos["shares"],
                    cost_basis=pos["cost_basis"],
                    purchase_date=date.today(),
                    asset_type=pos["asset_type"]
                )
                db.add(new_position)

            synced += 1

        db.commit()
        return {"status": "success", "positions_synced": synced}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
