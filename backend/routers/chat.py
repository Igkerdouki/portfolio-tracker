"""
Chat Router
API endpoints for Claude-powered investment chat interface.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from services.claude_chat import claude_advisor
from services.agent_chat import agent_chat
from services.stock_screener import stock_screener
from services.enhanced_ml import EnhancedMLPredictor, run_enhanced_analysis
from services.hedge_fund_metrics import HedgeFundMetrics, calculate_metrics_for_returns

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatMessage(BaseModel):
    message: str


class ChatResponse(BaseModel):
    type: str
    message: str
    data: Optional[Any] = None


@router.post("/message")
async def send_message(msg: ChatMessage):
    """
    Send a message to the Claude-powered investment advisor.
    Provides friendly, educational, data-driven investment advice.
    """
    try:
        response = await claude_advisor.chat(msg.message)
        return response
    except Exception as e:
        # Fallback to basic agent if Claude fails
        try:
            response = agent_chat.process_message(msg.message)
            return response
        except:
            raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_history():
    """Get conversation history."""
    return {"history": agent_chat.get_history()}


@router.delete("/history")
async def clear_history():
    """Clear conversation history."""
    agent_chat.clear_history()
    return {"message": "History cleared"}


@router.get("/suggestions")
async def get_suggestions():
    """Get suggested prompts for users."""
    return {
        "suggestions": [
            "Give me stock recommendations",
            "Analyze AAPL",
            "Short term trading ideas",
            "Long term investments",
            "Compare TSLA vs NVDA",
            "How is the market today?",
            "What is Sharpe ratio?",
            "Find growth stocks",
            "Best dividend stocks",
            "Momentum plays"
        ]
    }


# ===== Stock Screener Endpoints =====

@router.get("/screener/short-term")
async def get_short_term_picks():
    """Get short-term trading recommendations."""
    try:
        return stock_screener.get_short_term_picks(limit=10)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/screener/long-term")
async def get_long_term_picks():
    """Get long-term investment recommendations."""
    try:
        return stock_screener.get_long_term_picks(limit=10)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/screener/all")
async def get_all_recommendations():
    """Get all recommendations."""
    try:
        return stock_screener.get_all_recommendations()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ScreenRequest(BaseModel):
    universe: str = "sp500"
    strategy: str = "momentum"
    min_volume: int = 1000000
    min_price: float = 5.0
    max_price: float = 10000.0
    limit: int = 20


@router.post("/screener/custom")
async def custom_screen(req: ScreenRequest):
    """Run custom stock screening."""
    try:
        results = stock_screener.screen_stocks(
            universe=req.universe,
            strategy=req.strategy,
            min_volume=req.min_volume,
            min_price=req.min_price,
            max_price=req.max_price,
            limit=req.limit
        )
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== Enhanced ML Endpoints =====

@router.get("/ml/analyze/{symbol}")
async def analyze_stock(symbol: str):
    """Run enhanced ML analysis on a stock."""
    try:
        result = run_enhanced_analysis(symbol.upper())
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ml/predict/{symbol}")
async def predict_stock(symbol: str):
    """Get ML prediction for a stock."""
    try:
        predictor = EnhancedMLPredictor(symbol.upper())
        predictor.fetch_and_prepare(period="2y")
        predictor.train()
        prediction = predictor.predict_next_day()
        return prediction
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ml/backtest/{symbol}")
async def backtest_stock(symbol: str):
    """Run full backtest with hedge fund metrics."""
    try:
        predictor = EnhancedMLPredictor(symbol.upper())
        predictor.fetch_and_prepare(period="3y")
        predictor.train()
        results = predictor.backtest_with_metrics()
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== Metrics Explanation Endpoints =====

@router.get("/metrics/explain")
async def explain_metrics():
    """Get explanations for all hedge fund metrics."""
    return {
        "return_metrics": {
            "total_return_pct": "Total percentage return over the period",
            "cagr_pct": "Compound Annual Growth Rate - annualized return",
            "positive_days_pct": "Percentage of days with positive returns"
        },
        "risk_metrics": {
            "annual_volatility_pct": "Standard deviation of returns, annualized",
            "downside_deviation_pct": "Volatility of negative returns only"
        },
        "risk_adjusted_metrics": {
            "sharpe_ratio": "Return per unit of risk. Above 1 is good, above 2 is excellent",
            "sortino_ratio": "Like Sharpe but only penalizes downside risk",
            "calmar_ratio": "Return divided by maximum drawdown",
            "omega_ratio": "Probability-weighted ratio of gains to losses"
        },
        "drawdown_metrics": {
            "max_drawdown_pct": "Largest peak-to-trough decline",
            "recovery_factor": "Total return divided by max drawdown"
        },
        "tail_risk_metrics": {
            "var_95_pct": "Maximum daily loss with 95% confidence",
            "cvar_95_pct": "Expected loss when losses exceed VaR (worst-case average)"
        },
        "trading_metrics": {
            "win_rate_pct": "Percentage of profitable trades/days",
            "profit_factor": "Gross profits divided by gross losses",
            "kelly_criterion_pct": "Optimal position size for maximum growth"
        }
    }


@router.get("/metrics/glossary")
async def metrics_glossary():
    """Get full glossary of financial terms."""
    return {
        "glossary": [
            {
                "term": "Alpha",
                "definition": "Excess return above benchmark. Positive alpha = beating the market.",
                "good_value": "> 0"
            },
            {
                "term": "Beta",
                "definition": "Volatility relative to market. Beta > 1 = more volatile than market.",
                "good_value": "Depends on risk tolerance"
            },
            {
                "term": "Sharpe Ratio",
                "definition": "Risk-adjusted return. Higher is better.",
                "good_value": "> 1.0"
            },
            {
                "term": "Sortino Ratio",
                "definition": "Like Sharpe but only considers downside risk.",
                "good_value": "> 1.5"
            },
            {
                "term": "Maximum Drawdown",
                "definition": "Largest peak-to-trough decline.",
                "good_value": "> -30%"
            },
            {
                "term": "VaR (Value at Risk)",
                "definition": "Maximum expected loss at confidence level.",
                "good_value": "Lower is better"
            },
            {
                "term": "CVaR/Expected Shortfall",
                "definition": "Average loss when losses exceed VaR.",
                "good_value": "Lower is better"
            },
            {
                "term": "Calmar Ratio",
                "definition": "Annual return / Max drawdown.",
                "good_value": "> 1.0"
            },
            {
                "term": "Omega Ratio",
                "definition": "Probability-weighted gains to losses ratio.",
                "good_value": "> 1.0"
            },
            {
                "term": "Information Ratio",
                "definition": "Active return / Tracking error.",
                "good_value": "> 0.5"
            },
            {
                "term": "Kelly Criterion",
                "definition": "Optimal bet size for maximum growth.",
                "good_value": "10-25%"
            },
            {
                "term": "Profit Factor",
                "definition": "Gross profit / Gross loss.",
                "good_value": "> 1.5"
            },
            {
                "term": "Win Rate",
                "definition": "Percentage of winning trades.",
                "good_value": "> 50%"
            },
            {
                "term": "RSI",
                "definition": "Momentum indicator. >70 overbought, <30 oversold.",
                "good_value": "30-70"
            },
            {
                "term": "MACD",
                "definition": "Trend following indicator. Crossovers signal trades.",
                "good_value": "Depends on signal"
            }
        ]
    }
