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
from services.stock_analyzer import stock_analyzer
from services.analysis_agent import analysis_agent
from services.data_collector import data_collector
import threading

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

        # Calculate avg cost as fallback price
        avg_cost = position.cost_basis / position.shares if position.shares > 0 else 0

        pos_dict = {
            "id": position.id,
            "symbol": position.symbol,
            "shares": position.shares,
            "cost_basis": position.cost_basis,
            "purchase_date": position.purchase_date,
            "asset_type": position.asset_type,
            # Use actual price if available, otherwise show avg cost
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
        # Use get_positions() instead of get_portfolio() as it's more reliable
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


# Stock Analysis Agent endpoints
_agent_thread = None


@app.get("/analysis/analyze/{symbol}")
def analyze_stock(symbol: str):
    """Analyze a single stock using fundamental and technical metrics."""
    try:
        analysis = stock_analyzer.analyze_stock(symbol.upper())
        return analysis
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analysis/analyze-multiple")
def analyze_multiple(symbols: List[str]):
    """Analyze multiple stocks."""
    results = []
    for symbol in symbols:
        try:
            analysis = stock_analyzer.analyze_stock(symbol.upper())
            results.append(analysis)
        except Exception as e:
            results.append({"symbol": symbol, "error": str(e)})
    return {"analyses": results}


@app.get("/analysis/suggestions")
def get_suggestions():
    """Get current analysis suggestions and top picks."""
    return analysis_agent.get_suggestions()


@app.get("/analysis/watchlist")
def get_watchlist():
    """Get current watchlist."""
    return {"watchlist": analysis_agent.state['watchlist']}


@app.post("/analysis/watchlist/add")
def add_to_watchlist(symbols: List[str]):
    """Add symbols to watchlist."""
    analysis_agent.add_to_watchlist(symbols)
    return {"watchlist": analysis_agent.state['watchlist']}


@app.post("/analysis/watchlist/remove")
def remove_from_watchlist(symbols: List[str]):
    """Remove symbols from watchlist."""
    analysis_agent.remove_from_watchlist(symbols)
    return {"watchlist": analysis_agent.state['watchlist']}


@app.post("/analysis/run-cycle")
def run_analysis_cycle():
    """Run a single analysis cycle on all watchlist stocks."""
    try:
        results = analysis_agent.run_analysis_cycle()
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analysis/start-agent")
def start_analysis_agent(interval_hours: float = 4):
    """Start the continuous analysis agent in background."""
    global _agent_thread

    if analysis_agent.running:
        return {"status": "already_running"}

    def run_agent():
        analysis_agent.run_continuous(interval_hours)

    _agent_thread = threading.Thread(target=run_agent, daemon=True)
    _agent_thread.start()

    return {"status": "started", "interval_hours": interval_hours}


@app.post("/analysis/stop-agent")
def stop_analysis_agent():
    """Stop the continuous analysis agent."""
    if not analysis_agent.running:
        return {"status": "not_running"}

    analysis_agent.stop()
    return {"status": "stopping"}


@app.get("/analysis/agent-status")
def get_agent_status():
    """Get analysis agent status."""
    return {
        "running": analysis_agent.running,
        "analysis_count": analysis_agent.state['analysis_count'],
        "improvement_cycles": analysis_agent.state['improvement_cycles'],
        "pending_predictions": len(analysis_agent.state['pending_predictions']),
        "completed_predictions": len(analysis_agent.state['completed_predictions']),
        "last_analysis": analysis_agent.state['last_analysis'],
        "started_at": analysis_agent.state.get('started_at'),
    }


@app.get("/analysis/predictions")
def get_predictions():
    """Get all predictions (pending and completed)."""
    return {
        "pending": analysis_agent.state['pending_predictions'],
        "completed": analysis_agent.state['completed_predictions'][-20:],  # Last 20
    }


@app.post("/analysis/check-predictions")
def check_predictions():
    """Check pending predictions against actual outcomes."""
    try:
        results = analysis_agent.check_predictions()
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/analysis/report")
def get_analysis_report():
    """Generate and return the analysis report."""
    try:
        report = analysis_agent.analyzer.generate_report(analysis_agent.state['watchlist'])
        return {"report": report}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/analysis/weights")
def get_model_weights():
    """Get current model weights used for scoring."""
    return {
        "weights": analysis_agent.analyzer.weights,
        "default_weights": analysis_agent.analyzer.DEFAULT_WEIGHTS,
    }


# Data Collection endpoints
@app.post("/data/collect")
def collect_data(symbols: List[str] = None):
    """Collect data from all sources for given symbols (or watchlist)."""
    if not symbols:
        symbols = analysis_agent.state.get('watchlist', [])

    if not symbols:
        raise HTTPException(status_code=400, detail="No symbols provided")

    try:
        results = data_collector.collect_all(symbols)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/data/stock/{symbol}")
def get_collected_data(symbol: str):
    """Get collected data for a specific symbol."""
    data = data_collector.get_stock_data(symbol)
    if not data:
        raise HTTPException(status_code=404, detail=f"No data collected for {symbol}")
    return data


@app.get("/data/signals/{symbol}")
def get_signals(symbol: str):
    """Get trading signals based on collected data."""
    signals = data_collector.get_signals(symbol)
    if 'error' in signals:
        raise HTTPException(status_code=404, detail=signals['error'])
    return signals


@app.get("/data/stats")
def get_collection_stats():
    """Get data collection statistics."""
    return data_collector.get_collection_stats()


@app.post("/data/collect-and-analyze")
def collect_and_analyze(symbols: List[str] = None):
    """Collect data and run analysis in one call - the full self-improving cycle."""
    if not symbols:
        symbols = analysis_agent.state.get('watchlist', [])

    if not symbols:
        raise HTTPException(status_code=400, detail="No symbols provided")

    results = {
        'collection': {},
        'analysis': {},
        'signals': {},
        'top_picks': [],
    }

    try:
        # Step 1: Collect all data
        results['collection'] = data_collector.collect_all(symbols)

        # Step 2: Run analysis cycle
        results['analysis'] = analysis_agent.run_analysis_cycle()

        # Step 3: Generate signals for each symbol
        for symbol in symbols:
            signals = data_collector.get_signals(symbol)
            if 'error' not in signals:
                results['signals'][symbol] = signals

        # Step 4: Check past predictions (self-improvement)
        analysis_agent.check_predictions()

        results['top_picks'] = analysis_agent.state.get('top_picks', [])

        return results

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
