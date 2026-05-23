"""
ML Prediction API endpoints.
Train models, run backtests, and get predictions.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime

from services.ml_predictor import ml_system, HAS_YFINANCE, HAS_TENSORFLOW

router = APIRouter(prefix="/ml", tags=["machine-learning"])

# Store for background training jobs
_training_jobs: Dict[str, Dict] = {}


class TrainRequest(BaseModel):
    symbol: str
    model_type: str = "random_forest"  # or "lstm"
    period: str = "5y"


class PredictRequest(BaseModel):
    symbol: str


class BacktestRequest(BaseModel):
    symbol: str
    model_type: str = "random_forest"
    period: str = "5y"


@router.get("/status")
def get_ml_status():
    """Get ML system status and capabilities."""
    return {
        "yfinance_available": HAS_YFINANCE,
        "tensorflow_available": HAS_TENSORFLOW,
        "available_models": ["random_forest"] + (["lstm"] if HAS_TENSORFLOW else []),
        "rf_model_trained": ml_system.rf_model.is_fitted,
        "lstm_model_trained": ml_system.lstm_model.is_fitted if ml_system.lstm_model else False,
        "cached_symbols": list(ml_system.data_cache.keys()),
        "features": ml_system.feature_engineer.get_feature_columns()
    }


@router.post("/train")
async def train_model(request: TrainRequest):
    """
    Train an ML model on historical data for a symbol.

    Returns training metrics and validation scores.
    """
    if not HAS_YFINANCE:
        raise HTTPException(status_code=500, detail="yfinance not installed")

    if request.model_type == "lstm" and not HAS_TENSORFLOW:
        raise HTTPException(status_code=500, detail="TensorFlow not installed. Use random_forest instead.")

    try:
        # Fetch data
        df = ml_system.fetch_data(request.symbol.upper(), request.period)

        # Train model
        if request.model_type == "lstm":
            result = ml_system.lstm_model.train(df)
        else:
            result = ml_system.rf_model.train(df)

        return {
            "status": "success",
            "symbol": request.symbol.upper(),
            "model_type": request.model_type,
            "training_result": result,
            "data_points": len(df)
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/predict")
async def predict(request: PredictRequest):
    """
    Get prediction for next trading day.

    Returns direction (UP/DOWN), confidence, and predicted return.
    """
    if not HAS_YFINANCE:
        raise HTTPException(status_code=500, detail="yfinance not installed")

    try:
        result = ml_system.quick_predict(request.symbol.upper())

        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])

        return {
            "symbol": request.symbol.upper(),
            "prediction": result,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/backtest")
async def run_backtest(request: BacktestRequest):
    """
    Run full ML pipeline with backtest and Monte Carlo evaluation.

    This trains a model, backtests long/short strategy vs buy-and-hold,
    and evaluates with Monte Carlo resampling.
    """
    if not HAS_YFINANCE:
        raise HTTPException(status_code=500, detail="yfinance not installed")

    try:
        result = ml_system.train_and_evaluate(
            symbol=request.symbol.upper(),
            model_type=request.model_type,
            period=request.period
        )

        return result

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/features/{symbol}")
async def get_features(symbol: str, period: str = "1y"):
    """
    Get calculated features for a symbol.

    Useful for understanding what the model sees.
    """
    if not HAS_YFINANCE:
        raise HTTPException(status_code=500, detail="yfinance not installed")

    try:
        df = ml_system.fetch_data(symbol.upper(), period)

        # Get latest features
        latest = df.iloc[-1]
        feature_cols = ml_system.feature_engineer.get_feature_columns()

        features = {}
        for col in feature_cols:
            if col in latest.index:
                val = latest[col]
                features[col] = float(val) if not pd.isna(val) else None

        return {
            "symbol": symbol.upper(),
            "date": str(df.index[-1].date()),
            "close_price": float(latest['Close']),
            "features": features
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/history/{symbol}")
async def get_price_history(symbol: str, period: str = "1y"):
    """
    Get historical price data with features.
    """
    if not HAS_YFINANCE:
        raise HTTPException(status_code=500, detail="yfinance not installed")

    try:
        df = ml_system.fetch_data(symbol.upper(), period)

        # Prepare response data
        history = []
        for idx, row in df.tail(252).iterrows():  # Last year of data
            history.append({
                "date": str(idx.date()),
                "open": float(row['Open']),
                "high": float(row['High']),
                "low": float(row['Low']),
                "close": float(row['Close']),
                "volume": int(row['Volume']),
                "return_1d": float(row['return_1d']) if not pd.isna(row['return_1d']) else None,
                "rsi": float(row['rsi']) if not pd.isna(row['rsi']) else None,
                "macd": float(row['macd']) if not pd.isna(row['macd']) else None,
            })

        return {
            "symbol": symbol.upper(),
            "period": period,
            "data_points": len(history),
            "history": history
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/batch-predict")
async def batch_predict(symbols: List[str]):
    """
    Get predictions for multiple symbols.
    """
    if not HAS_YFINANCE:
        raise HTTPException(status_code=500, detail="yfinance not installed")

    results = []
    for symbol in symbols[:20]:  # Limit to 20 symbols
        try:
            prediction = ml_system.quick_predict(symbol.upper())
            results.append({
                "symbol": symbol.upper(),
                "prediction": prediction,
                "status": "success" if "error" not in prediction else "error"
            })
        except Exception as e:
            results.append({
                "symbol": symbol.upper(),
                "error": str(e),
                "status": "error"
            })

    return {
        "predictions": results,
        "timestamp": datetime.now().isoformat()
    }


# Import pandas for feature endpoint
import pandas as pd
