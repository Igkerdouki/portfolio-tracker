"""Stock analysis and AI agent endpoints."""

from fastapi import APIRouter, HTTPException
from typing import List
import threading

from services.stock_analyzer import stock_analyzer
from services.analysis_agent import analysis_agent
from services.analysis_cache import analysis_cache

router = APIRouter(prefix="/analysis", tags=["analysis"])

_agent_thread = None


@router.get("/analyze/{symbol}")
def analyze_stock(symbol: str, use_cache: bool = True):
    """Analyze a single stock using fundamental and technical metrics."""
    symbol = symbol.upper()

    # Check cache first
    if use_cache:
        cached = analysis_cache.get(symbol)
        if cached:
            cached['from_cache'] = True
            return cached

    try:
        analysis = stock_analyzer.analyze_stock(symbol)

        # Cache the result
        if 'error' not in analysis:
            analysis_cache.set(symbol, analysis)

        return analysis
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze-multiple")
def analyze_multiple(symbols: List[str], use_cache: bool = True):
    """Analyze multiple stocks."""
    results = []
    for symbol in symbols:
        try:
            symbol = symbol.upper()

            # Check cache first
            if use_cache:
                cached = analysis_cache.get(symbol)
                if cached:
                    cached['from_cache'] = True
                    results.append(cached)
                    continue

            analysis = stock_analyzer.analyze_stock(symbol)

            if 'error' not in analysis:
                analysis_cache.set(symbol, analysis)

            results.append(analysis)
        except Exception as e:
            results.append({"symbol": symbol, "error": str(e)})
    return {"analyses": results}


@router.get("/suggestions")
def get_suggestions():
    """Get current analysis suggestions and top picks."""
    return analysis_agent.get_suggestions()


@router.get("/watchlist")
def get_watchlist():
    """Get current watchlist."""
    return {"watchlist": analysis_agent.state['watchlist']}


@router.post("/watchlist/add")
def add_to_watchlist(symbols: List[str]):
    """Add symbols to watchlist."""
    analysis_agent.add_to_watchlist(symbols)
    return {"watchlist": analysis_agent.state['watchlist']}


@router.post("/watchlist/remove")
def remove_from_watchlist(symbols: List[str]):
    """Remove symbols from watchlist."""
    analysis_agent.remove_from_watchlist(symbols)
    return {"watchlist": analysis_agent.state['watchlist']}


@router.post("/run-cycle")
def run_analysis_cycle():
    """Run a single analysis cycle on all watchlist stocks."""
    try:
        results = analysis_agent.run_analysis_cycle()
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/start-agent")
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


@router.post("/stop-agent")
def stop_analysis_agent():
    """Stop the continuous analysis agent."""
    if not analysis_agent.running:
        return {"status": "not_running"}

    analysis_agent.stop()
    return {"status": "stopping"}


@router.get("/agent-status")
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


@router.get("/predictions")
def get_predictions():
    """Get all predictions (pending and completed)."""
    return {
        "pending": analysis_agent.state['pending_predictions'],
        "completed": analysis_agent.state['completed_predictions'][-20:],
    }


@router.post("/check-predictions")
def check_predictions():
    """Check pending predictions against actual outcomes."""
    try:
        results = analysis_agent.check_predictions()
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/report")
def get_analysis_report():
    """Generate and return the analysis report."""
    try:
        report = analysis_agent.analyzer.generate_report(analysis_agent.state['watchlist'])
        return {"report": report}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/weights")
def get_model_weights():
    """Get current model weights used for scoring."""
    return {
        "weights": analysis_agent.analyzer.weights,
        "default_weights": analysis_agent.analyzer.DEFAULT_WEIGHTS,
    }


@router.get("/cache-stats")
def get_cache_stats():
    """Get analysis cache statistics."""
    return analysis_cache.get_stats()


@router.post("/cache-clear")
def clear_cache(symbol: str = None):
    """Clear analysis cache (all or specific symbol)."""
    if symbol:
        analysis_cache.invalidate(symbol.upper())
        return {"cleared": symbol.upper()}
    else:
        analysis_cache.clear()
        return {"cleared": "all"}
