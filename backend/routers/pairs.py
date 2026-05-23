"""
Pairs Trading API endpoints.
Statistical arbitrage with Kalman filter hedge ratio estimation.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Tuple, Optional
from datetime import datetime

from services.pairs_trading import PairsTrader, pairs_scanner, COMMON_PAIRS, HAS_YFINANCE

router = APIRouter(prefix="/pairs", tags=["pairs-trading"])


class PairRequest(BaseModel):
    symbol_x: str = "V"
    symbol_y: str = "MA"
    period: str = "5y"
    lookback: int = 60
    entry_z: float = 2.0
    exit_z: float = 0.5


class ScanRequest(BaseModel):
    pairs: List[List[str]]


@router.get("/status")
def get_status():
    """Get pairs trading system status."""
    return {
        "yfinance_available": HAS_YFINANCE,
        "cached_pairs": list(pairs_scanner.pairs_cache.keys()),
        "common_pairs": [f"{x}/{y}" for x, y in COMMON_PAIRS]
    }


@router.post("/backtest")
async def backtest_pair(request: PairRequest):
    """
    Backtest a pairs trading strategy.

    Uses Kalman filter for dynamic hedge ratio estimation and
    Z-score for entry/exit signals.
    """
    if not HAS_YFINANCE:
        raise HTTPException(status_code=500, detail="yfinance not installed")

    try:
        trader = PairsTrader(
            symbol_x=request.symbol_x.upper(),
            symbol_y=request.symbol_y.upper(),
            lookback=request.lookback,
            entry_z=request.entry_z,
            exit_z=request.exit_z
        )

        trader.fetch_data(request.period)
        trader.generate_signals()
        result = trader.backtest()

        return result

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/signal/{symbol_x}/{symbol_y}")
async def get_pair_signal(symbol_x: str, symbol_y: str, period: str = "2y"):
    """
    Get current trading signal for a pair.
    """
    if not HAS_YFINANCE:
        raise HTTPException(status_code=500, detail="yfinance not installed")

    try:
        signal = pairs_scanner.scan_pair(symbol_x.upper(), symbol_y.upper(), period)
        return signal

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/scan")
async def scan_common_pairs():
    """
    Scan all common pairs for trading opportunities.
    """
    if not HAS_YFINANCE:
        raise HTTPException(status_code=500, detail="yfinance not installed")

    try:
        results = pairs_scanner.scan_multiple(COMMON_PAIRS)
        return {
            "pairs_scanned": len(COMMON_PAIRS),
            "results": results,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/scan-custom")
async def scan_custom_pairs(request: ScanRequest):
    """
    Scan custom pairs for trading opportunities.
    """
    if not HAS_YFINANCE:
        raise HTTPException(status_code=500, detail="yfinance not installed")

    pairs = [(p[0].upper(), p[1].upper()) for p in request.pairs if len(p) == 2]

    if not pairs:
        raise HTTPException(status_code=400, detail="No valid pairs provided")

    try:
        results = pairs_scanner.scan_multiple(pairs)
        return {
            "pairs_scanned": len(pairs),
            "results": results,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/explain")
def explain_strategy():
    """
    Explain the pairs trading strategy.
    """
    return {
        "name": "Statistical Arbitrage Pairs Trading",
        "description": "Mean-reversion strategy for correlated stock pairs using Kalman filter",
        "how_it_works": {
            "1_correlation": "Find highly correlated stocks (e.g., V and MA both in payment processing)",
            "2_kalman_filter": "Dynamically estimate the hedge ratio (how many shares of Y to hold per share of X)",
            "3_spread": "Calculate spread = X_price - hedge_ratio * Y_price",
            "4_z_score": "Normalize spread using 60-day rolling mean and std deviation",
            "5_entry": "Enter when Z-score > 2 (short spread) or < -2 (long spread)",
            "6_exit": "Exit when Z-score returns near 0 (mean reversion complete)",
            "7_position_sizing": "Scale position inversely to 14-day ATR (higher volatility = smaller position)"
        },
        "signals": {
            "LONG_SPREAD": "Z < -2: Buy X, Sell Y (expect spread to widen)",
            "SHORT_SPREAD": "Z > 2: Sell X, Buy Y (expect spread to narrow)",
            "EXIT": "Z near 0: Close position",
            "STOP_LOSS": "Z > 4 or < -4: Cut losses"
        },
        "parameters": {
            "lookback": "Rolling window for Z-score calculation (default: 60 days)",
            "entry_z": "Z-score threshold for entry (default: 2.0)",
            "exit_z": "Z-score threshold for exit (default: 0.5)",
            "atr_period": "Period for ATR calculation (default: 14 days)",
            "stop_loss_z": "Z-score threshold for stop loss (default: 4.0)"
        },
        "risks": [
            "Correlation breakdown (pairs can decouple during market stress)",
            "Transaction costs eating into small profits",
            "Regime changes making historical patterns invalid",
            "Execution slippage in fast markets"
        ]
    }


@router.get("/demo")
async def demo_backtest():
    """
    Run a demo backtest on V/MA pair.
    """
    if not HAS_YFINANCE:
        return {
            "error": "yfinance not installed",
            "demo_explanation": "This would backtest Visa (V) vs Mastercard (MA) pairs trading"
        }

    try:
        trader = PairsTrader(symbol_x="V", symbol_y="MA")
        trader.fetch_data("3y")
        trader.generate_signals()
        result = trader.backtest()

        return {
            "status": "success",
            "pair": "V/MA",
            "backtest": result
        }

    except Exception as e:
        return {"error": str(e)}
