"""Data collection endpoints."""

from fastapi import APIRouter, HTTPException
from typing import List

from services.data_collector import data_collector
from services.analysis_agent import analysis_agent

router = APIRouter(prefix="/data", tags=["data"])


@router.post("/collect")
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


@router.get("/stock/{symbol}")
def get_collected_data(symbol: str):
    """Get collected data for a specific symbol."""
    data = data_collector.get_stock_data(symbol)
    if not data:
        raise HTTPException(status_code=404, detail=f"No data collected for {symbol}")
    return data


@router.get("/signals/{symbol}")
def get_signals(symbol: str):
    """Get trading signals based on collected data."""
    signals = data_collector.get_signals(symbol)
    if 'error' in signals:
        raise HTTPException(status_code=404, detail=signals['error'])
    return signals


@router.get("/stats")
def get_collection_stats():
    """Get data collection statistics."""
    return data_collector.get_collection_stats()


@router.post("/collect-and-analyze")
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
