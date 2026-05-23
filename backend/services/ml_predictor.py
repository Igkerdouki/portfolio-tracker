"""
ML-Based Stock Predictor
Uses Random Forest and LSTM to predict next-day returns.
Includes backtesting with Monte Carlo resampling evaluation.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')

# ML imports
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import joblib
import os

# Try importing deep learning (optional)
try:
    import tensorflow as tf
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import LSTM, Dense, Dropout
    from tensorflow.keras.callbacks import EarlyStopping
    HAS_TENSORFLOW = True
except ImportError:
    HAS_TENSORFLOW = False
    Sequential = None  # Placeholder for type hints

# Try importing yfinance
try:
    import yfinance as yf
    HAS_YFINANCE = True
except ImportError:
    HAS_YFINANCE = False


class FeatureEngineer:
    """Create technical features for ML models."""

    @staticmethod
    def create_features(df: pd.DataFrame, include_target: bool = True) -> pd.DataFrame:
        """
        Create features from OHLCV data.

        Features:
        - Moving averages (5, 10, 20, 50, 200 day)
        - Lagged returns (1, 2, 3, 5, 10 days)
        - Rolling volatility (5, 10, 20 days)
        - RSI, MACD, Bollinger Bands
        - Volume features
        """
        df = df.copy()
        close = df['Close']
        high = df['High']
        low = df['Low']
        volume = df['Volume']

        # Price returns
        df['return_1d'] = close.pct_change(1)
        df['return_2d'] = close.pct_change(2)
        df['return_3d'] = close.pct_change(3)
        df['return_5d'] = close.pct_change(5)
        df['return_10d'] = close.pct_change(10)

        # Lagged returns (previous days' returns as features)
        for lag in [1, 2, 3, 5, 10]:
            df[f'lag_return_{lag}d'] = df['return_1d'].shift(lag)

        # Moving averages
        for window in [5, 10, 20, 50, 200]:
            df[f'sma_{window}'] = close.rolling(window=window).mean()
            df[f'sma_{window}_ratio'] = close / df[f'sma_{window}']

        # Exponential moving averages
        for window in [12, 26]:
            df[f'ema_{window}'] = close.ewm(span=window, adjust=False).mean()

        # Rolling volatility (standard deviation of returns)
        for window in [5, 10, 20]:
            df[f'volatility_{window}d'] = df['return_1d'].rolling(window=window).std()

        # RSI (Relative Strength Index)
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))

        # MACD
        df['macd'] = df['ema_12'] - df['ema_26']
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_histogram'] = df['macd'] - df['macd_signal']

        # Bollinger Bands
        df['bb_middle'] = close.rolling(window=20).mean()
        bb_std = close.rolling(window=20).std()
        df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
        df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
        df['bb_position'] = (close - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])

        # Average True Range (ATR)
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        df['atr'] = tr.rolling(window=14).mean()
        df['atr_ratio'] = df['atr'] / close

        # Volume features
        df['volume_sma_20'] = volume.rolling(window=20).mean()
        df['volume_ratio'] = volume / df['volume_sma_20']
        df['volume_change'] = volume.pct_change()

        # Price position (where price is relative to recent range)
        df['price_position_20d'] = (close - close.rolling(20).min()) / (close.rolling(20).max() - close.rolling(20).min())
        df['price_position_50d'] = (close - close.rolling(50).min()) / (close.rolling(50).max() - close.rolling(50).min())

        # Day of week (cyclical encoding)
        df['day_of_week'] = df.index.dayofweek
        df['day_sin'] = np.sin(2 * np.pi * df['day_of_week'] / 5)
        df['day_cos'] = np.cos(2 * np.pi * df['day_of_week'] / 5)

        # Target: Next day return (for training)
        if include_target:
            df['target'] = df['return_1d'].shift(-1)  # Next day's return
            df['target_direction'] = (df['target'] > 0).astype(int)  # 1 if up, 0 if down

        return df

    @staticmethod
    def get_feature_columns() -> List[str]:
        """Return list of feature column names."""
        return [
            # Lagged returns
            'lag_return_1d', 'lag_return_2d', 'lag_return_3d', 'lag_return_5d', 'lag_return_10d',
            # MA ratios
            'sma_5_ratio', 'sma_10_ratio', 'sma_20_ratio', 'sma_50_ratio', 'sma_200_ratio',
            # Volatility
            'volatility_5d', 'volatility_10d', 'volatility_20d',
            # Technical indicators
            'rsi', 'macd', 'macd_signal', 'macd_histogram',
            'bb_width', 'bb_position', 'atr_ratio',
            # Volume
            'volume_ratio', 'volume_change',
            # Price position
            'price_position_20d', 'price_position_50d',
            # Time
            'day_sin', 'day_cos'
        ]


class RandomForestPredictor:
    """Random Forest model for predicting next-day returns."""

    def __init__(self, n_estimators: int = 100, max_depth: int = 10):
        self.classifier = RandomForestClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            min_samples_split=20,
            min_samples_leaf=10,
            random_state=42,
            n_jobs=-1
        )
        self.regressor = RandomForestRegressor(
            n_estimators=n_estimators,
            max_depth=max_depth,
            min_samples_split=20,
            min_samples_leaf=10,
            random_state=42,
            n_jobs=-1
        )
        self.scaler = StandardScaler()
        self.feature_columns = FeatureEngineer.get_feature_columns()
        self.is_fitted = False

    def prepare_data(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Prepare features and targets from dataframe."""
        df_clean = df.dropna(subset=self.feature_columns + ['target', 'target_direction'])

        X = df_clean[self.feature_columns].values
        y_direction = df_clean['target_direction'].values
        y_return = df_clean['target'].values

        return X, y_direction, y_return

    def train(self, df: pd.DataFrame) -> Dict:
        """Train the model on historical data."""
        X, y_direction, y_return = self.prepare_data(df)

        # Scale features
        X_scaled = self.scaler.fit_transform(X)

        # Time series cross-validation
        tscv = TimeSeriesSplit(n_splits=5)
        cv_scores = []

        for train_idx, val_idx in tscv.split(X_scaled):
            X_train, X_val = X_scaled[train_idx], X_scaled[val_idx]
            y_train, y_val = y_direction[train_idx], y_direction[val_idx]

            self.classifier.fit(X_train, y_train)
            score = self.classifier.score(X_val, y_val)
            cv_scores.append(score)

        # Final training on all data
        self.classifier.fit(X_scaled, y_direction)
        self.regressor.fit(X_scaled, y_return)
        self.is_fitted = True

        # Feature importance
        importance = dict(zip(
            self.feature_columns,
            self.classifier.feature_importances_
        ))

        return {
            "cv_accuracy": np.mean(cv_scores),
            "cv_std": np.std(cv_scores),
            "feature_importance": dict(sorted(importance.items(), key=lambda x: x[1], reverse=True)[:10]),
            "training_samples": len(X)
        }

    def predict(self, df: pd.DataFrame) -> Dict:
        """Predict next-day direction and return."""
        if not self.is_fitted:
            raise ValueError("Model not trained. Call train() first.")

        df_clean = df.dropna(subset=self.feature_columns)
        if len(df_clean) == 0:
            return {"error": "No valid data for prediction"}

        X = df_clean[self.feature_columns].values[-1:]  # Last row
        X_scaled = self.scaler.transform(X)

        direction_prob = self.classifier.predict_proba(X_scaled)[0]
        predicted_return = self.regressor.predict(X_scaled)[0]

        return {
            "direction": "UP" if direction_prob[1] > 0.5 else "DOWN",
            "confidence": float(max(direction_prob)),
            "up_probability": float(direction_prob[1]),
            "down_probability": float(direction_prob[0]),
            "predicted_return": float(predicted_return),
            "predicted_return_pct": float(predicted_return * 100)
        }


class LSTMPredictor:
    """LSTM model for predicting next-day returns."""

    def __init__(self, sequence_length: int = 20):
        self.sequence_length = sequence_length
        self.model = None
        self.scaler = StandardScaler()
        self.feature_columns = FeatureEngineer.get_feature_columns()
        self.is_fitted = False

    def create_sequences(self, X: np.ndarray, y: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Create sequences for LSTM input."""
        X_seq, y_seq = [], []
        for i in range(self.sequence_length, len(X)):
            X_seq.append(X[i-self.sequence_length:i])
            y_seq.append(y[i])
        return np.array(X_seq), np.array(y_seq)

    def build_model(self, input_shape: Tuple[int, int]):
        """Build LSTM model architecture."""
        model = Sequential([
            LSTM(50, return_sequences=True, input_shape=input_shape),
            Dropout(0.2),
            LSTM(50, return_sequences=False),
            Dropout(0.2),
            Dense(25, activation='relu'),
            Dense(1, activation='sigmoid')  # Binary classification
        ])
        model.compile(
            optimizer='adam',
            loss='binary_crossentropy',
            metrics=['accuracy']
        )
        return model

    def train(self, df: pd.DataFrame, epochs: int = 50, batch_size: int = 32) -> Dict:
        """Train LSTM model."""
        if not HAS_TENSORFLOW:
            return {"error": "TensorFlow not installed. Use Random Forest instead."}

        df_clean = df.dropna(subset=self.feature_columns + ['target_direction'])

        X = df_clean[self.feature_columns].values
        y = df_clean['target_direction'].values

        # Scale features
        X_scaled = self.scaler.fit_transform(X)

        # Create sequences
        X_seq, y_seq = self.create_sequences(X_scaled, y)

        # Train/validation split (time-aware)
        split_idx = int(len(X_seq) * 0.8)
        X_train, X_val = X_seq[:split_idx], X_seq[split_idx:]
        y_train, y_val = y_seq[:split_idx], y_seq[split_idx:]

        # Build and train model
        self.model = self.build_model((self.sequence_length, len(self.feature_columns)))

        early_stop = EarlyStopping(
            monitor='val_loss',
            patience=10,
            restore_best_weights=True
        )

        history = self.model.fit(
            X_train, y_train,
            validation_data=(X_val, y_val),
            epochs=epochs,
            batch_size=batch_size,
            callbacks=[early_stop],
            verbose=0
        )

        self.is_fitted = True

        # Evaluate
        val_predictions = (self.model.predict(X_val, verbose=0) > 0.5).astype(int).flatten()

        return {
            "val_accuracy": float(accuracy_score(y_val, val_predictions)),
            "val_precision": float(precision_score(y_val, val_predictions)),
            "val_recall": float(recall_score(y_val, val_predictions)),
            "epochs_trained": len(history.history['loss']),
            "training_samples": len(X_train),
            "validation_samples": len(X_val)
        }

    def predict(self, df: pd.DataFrame) -> Dict:
        """Predict next-day direction."""
        if not self.is_fitted or self.model is None:
            return {"error": "Model not trained"}

        df_clean = df.dropna(subset=self.feature_columns)
        if len(df_clean) < self.sequence_length:
            return {"error": f"Need at least {self.sequence_length} days of data"}

        X = df_clean[self.feature_columns].values[-self.sequence_length:]
        X_scaled = self.scaler.transform(X)
        X_seq = X_scaled.reshape(1, self.sequence_length, -1)

        prob = float(self.model.predict(X_seq, verbose=0)[0][0])

        return {
            "direction": "UP" if prob > 0.5 else "DOWN",
            "confidence": float(max(prob, 1 - prob)),
            "up_probability": prob,
            "down_probability": 1 - prob
        }


class Backtester:
    """Backtest trading strategies with Monte Carlo evaluation."""

    def __init__(self, initial_capital: float = 100000):
        self.initial_capital = initial_capital

    def run_backtest(
        self,
        df: pd.DataFrame,
        predictions: np.ndarray,
        strategy: str = "long_short"
    ) -> Dict:
        """
        Run backtest on historical data.

        Strategies:
        - long_short: Go long when predicted UP, short when predicted DOWN
        - long_only: Go long when predicted UP, cash otherwise
        - buy_hold: Simple buy and hold benchmark
        """
        df = df.copy()
        returns = df['return_1d'].values

        # Align predictions with returns (predictions are for next day)
        aligned_preds = predictions[:-1]  # Remove last prediction (no return to compare)
        aligned_returns = returns[1:len(predictions)]  # Shift returns forward

        # Strategy returns
        if strategy == "long_short":
            # +1 for UP prediction, -1 for DOWN
            positions = np.where(aligned_preds == 1, 1, -1)
            strategy_returns = positions * aligned_returns
        elif strategy == "long_only":
            # +1 for UP prediction, 0 for DOWN
            positions = np.where(aligned_preds == 1, 1, 0)
            strategy_returns = positions * aligned_returns
        else:  # buy_hold
            strategy_returns = aligned_returns
            positions = np.ones_like(aligned_returns)

        # Calculate equity curve
        equity_curve = self.initial_capital * np.cumprod(1 + strategy_returns)

        # Calculate metrics
        total_return = (equity_curve[-1] / self.initial_capital - 1) * 100
        annual_return = ((equity_curve[-1] / self.initial_capital) ** (252 / len(equity_curve)) - 1) * 100

        # Sharpe ratio (assuming 252 trading days, 0% risk-free rate)
        sharpe = np.sqrt(252) * np.mean(strategy_returns) / np.std(strategy_returns) if np.std(strategy_returns) > 0 else 0

        # Max drawdown
        peak = np.maximum.accumulate(equity_curve)
        drawdown = (equity_curve - peak) / peak
        max_drawdown = np.min(drawdown) * 100

        # Win rate
        winning_trades = np.sum(strategy_returns > 0)
        total_trades = np.sum(positions != 0)
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

        return {
            "strategy": strategy,
            "total_return_pct": float(total_return),
            "annual_return_pct": float(annual_return),
            "sharpe_ratio": float(sharpe),
            "max_drawdown_pct": float(max_drawdown),
            "win_rate_pct": float(win_rate),
            "total_trades": int(total_trades),
            "winning_trades": int(winning_trades),
            "final_equity": float(equity_curve[-1]),
            "equity_curve": equity_curve.tolist()
        }

    def monte_carlo_evaluation(
        self,
        strategy_returns: np.ndarray,
        n_simulations: int = 1000,
        n_periods: int = 252
    ) -> Dict:
        """
        Monte Carlo resampling to evaluate strategy robustness.

        Instead of relying on a single equity curve, we resample returns
        to generate many possible equity paths and evaluate statistics.
        """
        np.random.seed(42)

        # Bootstrap resampling
        simulated_final_values = []
        simulated_sharpes = []
        simulated_max_drawdowns = []

        for _ in range(n_simulations):
            # Resample returns with replacement
            resampled_returns = np.random.choice(strategy_returns, size=n_periods, replace=True)

            # Calculate equity curve
            equity = self.initial_capital * np.cumprod(1 + resampled_returns)

            # Final value
            simulated_final_values.append(equity[-1])

            # Sharpe ratio
            sharpe = np.sqrt(252) * np.mean(resampled_returns) / np.std(resampled_returns) if np.std(resampled_returns) > 0 else 0
            simulated_sharpes.append(sharpe)

            # Max drawdown
            peak = np.maximum.accumulate(equity)
            drawdown = (equity - peak) / peak
            simulated_max_drawdowns.append(np.min(drawdown) * 100)

        simulated_final_values = np.array(simulated_final_values)
        simulated_sharpes = np.array(simulated_sharpes)
        simulated_max_drawdowns = np.array(simulated_max_drawdowns)

        # Calculate statistics
        final_returns = (simulated_final_values / self.initial_capital - 1) * 100

        return {
            "n_simulations": n_simulations,
            "return_statistics": {
                "mean": float(np.mean(final_returns)),
                "median": float(np.median(final_returns)),
                "std": float(np.std(final_returns)),
                "percentile_5": float(np.percentile(final_returns, 5)),
                "percentile_25": float(np.percentile(final_returns, 25)),
                "percentile_75": float(np.percentile(final_returns, 75)),
                "percentile_95": float(np.percentile(final_returns, 95)),
                "probability_positive": float(np.mean(final_returns > 0) * 100)
            },
            "sharpe_statistics": {
                "mean": float(np.mean(simulated_sharpes)),
                "median": float(np.median(simulated_sharpes)),
                "std": float(np.std(simulated_sharpes)),
                "percentile_5": float(np.percentile(simulated_sharpes, 5)),
                "percentile_95": float(np.percentile(simulated_sharpes, 95))
            },
            "drawdown_statistics": {
                "mean": float(np.mean(simulated_max_drawdowns)),
                "median": float(np.median(simulated_max_drawdowns)),
                "worst_5_percentile": float(np.percentile(simulated_max_drawdowns, 5)),
                "best_5_percentile": float(np.percentile(simulated_max_drawdowns, 95))
            },
            "simulated_final_values": simulated_final_values.tolist()[:100]  # First 100 for visualization
        }


class MLTradingSystem:
    """Main class orchestrating ML prediction and backtesting."""

    def __init__(self):
        self.feature_engineer = FeatureEngineer()
        self.rf_model = RandomForestPredictor()
        self.lstm_model = LSTMPredictor() if HAS_TENSORFLOW else None
        self.backtester = Backtester()
        self.data_cache: Dict[str, pd.DataFrame] = {}

    def fetch_data(self, symbol: str, period: str = "5y") -> pd.DataFrame:
        """Fetch historical data from yfinance."""
        if not HAS_YFINANCE:
            raise ImportError("yfinance not installed. Run: pip install yfinance")

        cache_key = f"{symbol}_{period}"
        if cache_key in self.data_cache:
            return self.data_cache[cache_key]

        # Use yf.download (more reliable than Ticker.history)
        df = yf.download(symbol, period=period, progress=False)

        if len(df) == 0:
            raise ValueError(f"No data found for {symbol}")

        # Flatten multi-index columns if present
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # Add features
        df = self.feature_engineer.create_features(df)

        self.data_cache[cache_key] = df
        return df

    def train_and_evaluate(
        self,
        symbol: str,
        model_type: str = "random_forest",
        period: str = "5y"
    ) -> Dict:
        """
        Full pipeline: fetch data, train model, backtest, Monte Carlo evaluation.
        """
        # Fetch and prepare data
        df = self.fetch_data(symbol, period)

        # Split data (80% train, 20% test)
        split_idx = int(len(df) * 0.8)
        train_df = df.iloc[:split_idx]
        test_df = df.iloc[split_idx:]

        # Train model
        if model_type == "lstm" and self.lstm_model:
            training_result = self.lstm_model.train(train_df)
            model = self.lstm_model
        else:
            training_result = self.rf_model.train(train_df)
            model = self.rf_model

        # Generate predictions on test set
        test_features = test_df.dropna(subset=FeatureEngineer.get_feature_columns())

        if model_type == "lstm" and self.lstm_model:
            # For LSTM, we need to predict one at a time
            predictions = []
            for i in range(len(test_features)):
                pred = model.predict(test_features.iloc[:i+1])
                predictions.append(1 if pred.get("direction") == "UP" else 0)
            predictions = np.array(predictions)
        else:
            X_test = test_features[FeatureEngineer.get_feature_columns()].values
            X_test_scaled = model.scaler.transform(X_test)
            predictions = model.classifier.predict(X_test_scaled)

        # Backtest strategies
        long_short_results = self.backtester.run_backtest(test_features, predictions, "long_short")
        long_only_results = self.backtester.run_backtest(test_features, predictions, "long_only")
        buy_hold_results = self.backtester.run_backtest(test_features, predictions, "buy_hold")

        # Calculate strategy returns for Monte Carlo
        test_returns = test_features['return_1d'].values
        positions = np.where(predictions[:-1] == 1, 1, -1)
        strategy_returns = positions * test_returns[1:len(predictions)]

        # Monte Carlo evaluation
        monte_carlo = self.backtester.monte_carlo_evaluation(strategy_returns)

        # Get current prediction
        current_prediction = model.predict(df)

        return {
            "symbol": symbol,
            "model_type": model_type,
            "data_info": {
                "total_samples": len(df),
                "training_samples": len(train_df),
                "test_samples": len(test_df),
                "date_range": {
                    "start": str(df.index[0].date()),
                    "end": str(df.index[-1].date())
                }
            },
            "training": training_result,
            "backtest": {
                "long_short": long_short_results,
                "long_only": long_only_results,
                "buy_hold": buy_hold_results
            },
            "monte_carlo": monte_carlo,
            "current_prediction": current_prediction,
            "comparison": {
                "long_short_vs_buy_hold": long_short_results["total_return_pct"] - buy_hold_results["total_return_pct"],
                "long_only_vs_buy_hold": long_only_results["total_return_pct"] - buy_hold_results["total_return_pct"],
                "sharpe_improvement": long_short_results["sharpe_ratio"] - buy_hold_results["sharpe_ratio"]
            }
        }

    def quick_predict(self, symbol: str) -> Dict:
        """Quick prediction for a symbol using cached or trained model."""
        try:
            df = self.fetch_data(symbol, "2y")

            if not self.rf_model.is_fitted:
                self.rf_model.train(df)

            return self.rf_model.predict(df)
        except Exception as e:
            return {"error": str(e)}


# Global instance
ml_system = MLTradingSystem()
