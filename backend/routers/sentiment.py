"""
Sentiment Analysis API endpoints.
Analyze earnings calls and news for trading signals.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from services.sentiment_analyzer import (
    sentiment_model, earnings_analyzer, event_study, sentiment_signal,
    HAS_TRANSFORMERS
)

router = APIRouter(prefix="/sentiment", tags=["sentiment-analysis"])


class TranscriptRequest(BaseModel):
    transcript: str
    symbol: Optional[str] = None


class NewsRequest(BaseModel):
    symbol: str
    news_items: List[str]


class EarningsEventRequest(BaseModel):
    symbol: str
    transcript: str
    earnings_date: str  # ISO format


@router.get("/status")
def get_status():
    """Get sentiment analysis system status."""
    return {
        "transformers_available": HAS_TRANSFORMERS,
        "model_loaded": sentiment_model is not None and sentiment_model.pipeline is not None,
        "model_name": sentiment_model.model_name if sentiment_model else None,
        "cached_signals": len(sentiment_signal.sentiment_cache),
        "events_analyzed": len(event_study.results)
    }


@router.post("/analyze-transcript")
async def analyze_transcript(request: TranscriptRequest):
    """
    Analyze an earnings call transcript for sentiment.

    Returns overall sentiment, section breakdown, and composite score.
    """
    if not HAS_TRANSFORMERS:
        raise HTTPException(
            status_code=500,
            detail="Transformers not installed. Run: pip install transformers torch"
        )

    try:
        result = earnings_analyzer.analyze_transcript(request.transcript)

        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])

        return {
            "status": "success",
            "symbol": request.symbol,
            "analysis": result
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/analyze-news")
async def analyze_news(request: NewsRequest):
    """
    Analyze news items for a symbol and generate trading signal.

    Aggregates sentiment from multiple news items into BUY/SELL/HOLD signal.
    """
    if not HAS_TRANSFORMERS:
        raise HTTPException(
            status_code=500,
            detail="Transformers not installed. Run: pip install transformers torch"
        )

    try:
        result = sentiment_signal.analyze_news(request.symbol, request.news_items)

        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])

        return result

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/analyze-text")
async def analyze_text(text: str):
    """
    Simple text sentiment analysis.

    Returns positive/negative/neutral label with confidence score.
    """
    if not HAS_TRANSFORMERS or not sentiment_model:
        raise HTTPException(
            status_code=500,
            detail="Transformers not installed. Run: pip install transformers torch"
        )

    try:
        result = sentiment_model.analyze(text)
        return result

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/earnings-event")
async def analyze_earnings_event(request: EarningsEventRequest):
    """
    Analyze an earnings event with event study.

    Correlates transcript sentiment with post-earnings price moves.
    """
    if not HAS_TRANSFORMERS:
        raise HTTPException(
            status_code=500,
            detail="Transformers not installed"
        )

    try:
        earnings_date = datetime.fromisoformat(request.earnings_date)
        result = event_study.analyze_earnings_event(
            symbol=request.symbol,
            transcript=request.transcript,
            earnings_date=earnings_date
        )

        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])

        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {e}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/backtest")
async def get_backtest_results():
    """
    Get backtest results from all analyzed earnings events.
    """
    if not event_study.results:
        return {
            "status": "no_data",
            "message": "No earnings events analyzed yet. Use /earnings-event endpoint first."
        }

    backtest = event_study.backtest_strategy(event_study.results)
    return {
        "status": "success",
        "backtest": backtest,
        "events": event_study.results[-10:]  # Last 10 events
    }


@router.get("/signals")
async def get_cached_signals():
    """
    Get all cached sentiment signals.
    """
    return {
        "signals": sentiment_signal.sentiment_cache,
        "count": len(sentiment_signal.sentiment_cache)
    }


@router.get("/signal/{symbol}")
async def get_signal(symbol: str):
    """
    Get cached sentiment signal for a symbol.
    """
    signal = sentiment_signal.get_signal(symbol.upper())
    if not signal:
        return {"status": "not_found", "symbol": symbol.upper()}

    return signal


# Sample earnings transcript for testing
SAMPLE_TRANSCRIPT = """
Good morning everyone, and thank you for joining our Q4 earnings call.

I'm pleased to report that we delivered exceptional results this quarter. Revenue increased 25% year-over-year to $5.2 billion, significantly beating analyst estimates of $4.8 billion. Our EPS came in at $3.45, well above the consensus estimate of $3.10.

Our cloud business continues to show strong momentum, with revenue growth accelerating to 35% this quarter. We're seeing strong enterprise adoption and our pipeline remains robust.

Looking ahead, we're raising our full-year guidance. We now expect revenue of $21 billion, up from our previous guidance of $20 billion. We're confident in our ability to continue executing and delivering value to shareholders.

We did face some headwinds in our legacy business, which declined 5%, but this was more than offset by strength in our growth initiatives.

Now I'll turn it over to our CFO for the financial details...

[Q&A Session]

Analyst: Can you talk about the margin trajectory going forward?

CEO: We expect margins to expand as we scale our cloud business. We're targeting a 200 basis point improvement in operating margins next year.

Analyst: What's driving the guidance raise?

CFO: We're seeing better-than-expected demand across all segments. Our backlog is at record levels, giving us confidence in the outlook.
"""


@router.get("/demo")
async def demo_analysis():
    """
    Demo endpoint with sample earnings transcript analysis.
    """
    if not HAS_TRANSFORMERS:
        return {
            "error": "Transformers not installed",
            "install": "pip install transformers torch",
            "sample_transcript": SAMPLE_TRANSCRIPT[:500] + "..."
        }

    try:
        result = earnings_analyzer.analyze_transcript(SAMPLE_TRANSCRIPT)
        return {
            "status": "success",
            "sample_analysis": result,
            "transcript_preview": SAMPLE_TRANSCRIPT[:500] + "..."
        }
    except Exception as e:
        return {"error": str(e)}
