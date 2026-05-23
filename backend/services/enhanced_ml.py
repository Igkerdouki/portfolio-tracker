"""
Enhanced ML Price Predictor
Improved features, multiple models, and comprehensive evaluation.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, AdaBoostClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import TimeSeriesSplit
import warnings
warnings.filterwarnings('ignore')

try:
    import yfinance as yf
    HAS_YFINANCE = True
except ImportError:
    HAS_YFINANCE = False

from services.hedge_fund_metrics import HedgeFundMetrics


class EnhancedFeatureEngineer:
    """
    Creates 50+ technical and statistical features for ML models.
    """

    def __init__(self):
        self.feature_names = []

    def create_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create comprehensive feature set."""
        features = pd.DataFrame(index=df.index)

        close = df['Close']
        high = df['High']
        low = df['Low']
        open_ = df['Open']
        volume = df['Volume']

        # ===== PRICE FEATURES =====
        # Returns at various horizons
        for period in [1, 2, 3, 5, 10, 21, 63]:
            features[f'return_{period}d'] = close.pct_change(period)

        # Log returns
        features['log_return_1d'] = np.log(close / close.shift(1))

        # ===== MOVING AVERAGES =====
        for period in [5, 10, 20, 50, 100, 200]:
            sma = close.rolling(period).mean()
            features[f'sma_{period}'] = close / sma - 1
            features[f'sma_{period}_slope'] = sma.pct_change(5)

        # EMA
        for period in [12, 26, 50]:
            ema = close.ewm(span=period).mean()
            features[f'ema_{period}'] = close / ema - 1

        # ===== VOLATILITY FEATURES =====
        for period in [5, 10, 20, 60]:
            features[f'volatility_{period}d'] = close.pct_change().rolling(period).std() * np.sqrt(252)

        # Garman-Klass volatility
        log_hl = np.log(high / low) ** 2
        log_co = np.log(close / open_) ** 2
        features['gk_volatility'] = np.sqrt(0.5 * log_hl - (2 * np.log(2) - 1) * log_co).rolling(20).mean()

        # Parkinson volatility
        features['parkinson_vol'] = np.sqrt((1 / (4 * np.log(2))) * (np.log(high / low) ** 2)).rolling(20).mean()

        # ATR
        tr = pd.concat([high - low, abs(high - close.shift()), abs(low - close.shift())], axis=1).max(axis=1)
        for period in [7, 14, 21]:
            features[f'atr_{period}'] = tr.rolling(period).mean() / close

        # ===== MOMENTUM INDICATORS =====
        # RSI
        for period in [7, 14, 21]:
            delta = close.diff()
            gain = (delta.where(delta > 0, 0)).rolling(period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
            rs = gain / loss
            features[f'rsi_{period}'] = 100 - (100 / (1 + rs))

        # Stochastic
        for period in [14, 21]:
            lowest = low.rolling(period).min()
            highest = high.rolling(period).max()
            features[f'stoch_k_{period}'] = 100 * (close - lowest) / (highest - lowest)
            features[f'stoch_d_{period}'] = features[f'stoch_k_{period}'].rolling(3).mean()

        # MACD
        ema12 = close.ewm(span=12).mean()
        ema26 = close.ewm(span=26).mean()
        macd = ema12 - ema26
        signal = macd.ewm(span=9).mean()
        features['macd'] = macd / close
        features['macd_signal'] = signal / close
        features['macd_hist'] = (macd - signal) / close
        features['macd_crossover'] = (macd > signal).astype(int) - (macd < signal).astype(int)

        # ROC (Rate of Change)
        for period in [5, 10, 20]:
            features[f'roc_{period}'] = close.pct_change(period) * 100

        # Williams %R
        features['williams_r'] = -100 * (high.rolling(14).max() - close) / (high.rolling(14).max() - low.rolling(14).min())

        # CCI (Commodity Channel Index)
        tp = (high + low + close) / 3
        sma_tp = tp.rolling(20).mean()
        mad = tp.rolling(20).apply(lambda x: np.abs(x - x.mean()).mean())
        features['cci'] = (tp - sma_tp) / (0.015 * mad)

        # ===== VOLUME FEATURES =====
        features['volume_sma_ratio'] = volume / volume.rolling(20).mean()
        features['volume_change'] = volume.pct_change()

        # OBV (On Balance Volume)
        obv = (np.sign(close.diff()) * volume).cumsum()
        features['obv_slope'] = obv.pct_change(10)

        # Money Flow Index
        tp = (high + low + close) / 3
        mf = tp * volume
        pos_mf = mf.where(tp > tp.shift(), 0).rolling(14).sum()
        neg_mf = mf.where(tp < tp.shift(), 0).rolling(14).sum()
        features['mfi'] = 100 - (100 / (1 + pos_mf / neg_mf.replace(0, 1)))

        # VWAP deviation
        vwap = (volume * (high + low + close) / 3).cumsum() / volume.cumsum()
        features['vwap_deviation'] = close / vwap - 1

        # ===== BOLLINGER BANDS =====
        for period in [20]:
            sma = close.rolling(period).mean()
            std = close.rolling(period).std()
            upper = sma + 2 * std
            lower = sma - 2 * std
            features[f'bb_position_{period}'] = (close - lower) / (upper - lower)
            features[f'bb_width_{period}'] = (upper - lower) / sma

        # ===== TREND FEATURES =====
        # ADX (Average Directional Index)
        plus_dm = high.diff()
        minus_dm = -low.diff()
        plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
        minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)

        tr14 = tr.rolling(14).sum()
        plus_di = 100 * plus_dm.rolling(14).sum() / tr14
        minus_di = 100 * minus_dm.rolling(14).sum() / tr14
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di).replace(0, 1)
        features['adx'] = dx.rolling(14).mean()
        features['plus_di'] = plus_di
        features['minus_di'] = minus_di

        # Aroon
        features['aroon_up'] = 100 * high.rolling(25).apply(lambda x: x.argmax()) / 25
        features['aroon_down'] = 100 * low.rolling(25).apply(lambda x: x.argmin()) / 25
        features['aroon_oscillator'] = features['aroon_up'] - features['aroon_down']

        # ===== STATISTICAL FEATURES =====
        # Skewness and Kurtosis of returns
        returns = close.pct_change()
        features['return_skew_20d'] = returns.rolling(20).skew()
        features['return_kurt_20d'] = returns.rolling(20).kurt()

        # Z-score of price
        features['price_zscore'] = (close - close.rolling(50).mean()) / close.rolling(50).std()

        # ===== CANDLESTICK PATTERNS =====
        body = close - open_
        upper_shadow = high - pd.concat([close, open_], axis=1).max(axis=1)
        lower_shadow = pd.concat([close, open_], axis=1).min(axis=1) - low

        features['body_size'] = abs(body) / (high - low).replace(0, 1)
        features['upper_shadow_ratio'] = upper_shadow / (high - low).replace(0, 1)
        features['lower_shadow_ratio'] = lower_shadow / (high - low).replace(0, 1)
        features['is_bullish'] = (body > 0).astype(int)

        # Doji pattern
        features['is_doji'] = (abs(body) / (high - low).replace(0, 1) < 0.1).astype(int)

        # ===== LAG FEATURES =====
        for lag in [1, 2, 3, 5]:
            features[f'return_lag_{lag}'] = returns.shift(lag)
            features[f'volume_lag_{lag}'] = volume.pct_change().shift(lag)

        # ===== DAY OF WEEK / MONTH =====
        features['day_of_week'] = df.index.dayofweek
        features['month'] = df.index.month
        features['is_month_end'] = df.index.is_month_end.astype(int)
        features['is_month_start'] = df.index.is_month_start.astype(int)

        # ===== ROLLING CORRELATIONS =====
        features['price_volume_corr'] = close.rolling(20).corr(volume)

        # Store feature names
        self.feature_names = features.columns.tolist()

        return features


class EnhancedMLPredictor:
    """
    Enhanced ML predictor with multiple models and ensemble.
    """

    def __init__(self, symbol: str):
        self.symbol = symbol
        self.feature_engineer = EnhancedFeatureEngineer()
        self.scaler = StandardScaler()
        self.models = {}
        self.data = None
        self.features = None
        self.trained = False

    def fetch_and_prepare(self, period: str = "5y") -> pd.DataFrame:
        """Fetch data and prepare features."""
        if not HAS_YFINANCE:
            raise ImportError("yfinance not installed")

        df = yf.download(self.symbol, period=period, progress=False)
        if len(df) < 200:
            raise ValueError(f"Insufficient data for {self.symbol}")

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        self.data = df
        self.features = self.feature_engineer.create_features(df)

        # Create target (next day return direction)
        self.features['target'] = np.sign(df['Close'].pct_change().shift(-1))

        # Drop NaN
        self.features = self.features.dropna()

        return self.features

    def train(self, test_size: float = 0.2) -> Dict:
        """Train multiple models."""
        if self.features is None:
            self.fetch_and_prepare()

        # Prepare data
        X = self.features.drop(['target'], axis=1)
        y = self.features['target']

        # Time series split
        split_idx = int(len(X) * (1 - test_size))
        X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
        y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)

        # Train multiple models
        self.models = {
            'random_forest': RandomForestClassifier(
                n_estimators=200,
                max_depth=10,
                min_samples_leaf=20,
                class_weight='balanced',
                random_state=42
            ),
            'gradient_boosting': GradientBoostingClassifier(
                n_estimators=100,
                max_depth=5,
                learning_rate=0.1,
                random_state=42
            ),
            'adaboost': AdaBoostClassifier(
                n_estimators=100,
                learning_rate=0.5,
                random_state=42
            )
        }

        results = {}
        for name, model in self.models.items():
            model.fit(X_train_scaled, y_train)
            train_acc = model.score(X_train_scaled, y_train)
            test_acc = model.score(X_test_scaled, y_test)
            predictions = model.predict(X_test_scaled)

            results[name] = {
                'train_accuracy': float(train_acc),
                'test_accuracy': float(test_acc),
                'predictions': predictions.tolist()
            }

        # Ensemble (majority vote)
        ensemble_preds = np.sign(np.sum([
            self.models['random_forest'].predict(X_test_scaled),
            self.models['gradient_boosting'].predict(X_test_scaled),
            self.models['adaboost'].predict(X_test_scaled)
        ], axis=0))
        ensemble_acc = (ensemble_preds == y_test.values).mean()

        results['ensemble'] = {
            'test_accuracy': float(ensemble_acc),
            'predictions': ensemble_preds.tolist()
        }

        # Feature importance (from Random Forest)
        importance = pd.DataFrame({
            'feature': X.columns,
            'importance': self.models['random_forest'].feature_importances_
        }).sort_values('importance', ascending=False)

        self.trained = True

        return {
            'symbol': self.symbol,
            'model_results': results,
            'feature_importance': importance.head(20).to_dict('records'),
            'n_features': len(X.columns),
            'train_size': len(X_train),
            'test_size': len(X_test),
            'test_dates': {
                'start': str(X_test.index[0].date()),
                'end': str(X_test.index[-1].date())
            }
        }

    def backtest_with_metrics(self, initial_capital: float = 100000) -> Dict:
        """Backtest with hedge fund metrics."""
        if not self.trained:
            self.train()

        # Prepare data
        X = self.features.drop(['target'], axis=1)
        y = self.features['target']

        split_idx = int(len(X) * 0.8)
        X_test = X.iloc[split_idx:]
        y_test = y.iloc[split_idx:]
        test_dates = X_test.index

        # Scale and predict
        X_test_scaled = self.scaler.transform(X_test)

        # Get ensemble prediction
        predictions = np.sign(np.sum([
            self.models['random_forest'].predict(X_test_scaled),
            self.models['gradient_boosting'].predict(X_test_scaled),
            self.models['adaboost'].predict(X_test_scaled)
        ], axis=0))

        # Get actual returns
        aligned_data = self.data.loc[test_dates]
        actual_returns = aligned_data['Close'].pct_change().shift(-1).dropna()

        # Align predictions with returns
        min_len = min(len(predictions) - 1, len(actual_returns))
        predictions = predictions[:min_len]
        actual_returns = actual_returns.iloc[:min_len]

        # Strategy returns (long/short based on prediction)
        strategy_returns = predictions * actual_returns.values

        # Calculate hedge fund metrics
        strategy_series = pd.Series(strategy_returns, index=actual_returns.index)
        buy_hold_returns = actual_returns

        hfm_strategy = HedgeFundMetrics(strategy_series, buy_hold_returns)
        hfm_benchmark = HedgeFundMetrics(buy_hold_returns)

        strategy_metrics = hfm_strategy.calculate_all()
        benchmark_metrics = hfm_benchmark.calculate_all()

        # Monte Carlo simulation
        monte_carlo = self._monte_carlo_simulation(strategy_returns, n_simulations=1000)

        return {
            'symbol': self.symbol,
            'period': f"{test_dates[0].date()} to {test_dates[-1].date()}",
            'strategy_metrics': strategy_metrics,
            'benchmark_metrics': benchmark_metrics,
            'monte_carlo': monte_carlo,
            'comparison': {
                'strategy_total_return': strategy_metrics['return_metrics']['total_return_pct'],
                'benchmark_total_return': benchmark_metrics['return_metrics']['total_return_pct'],
                'strategy_sharpe': strategy_metrics['risk_adjusted_metrics']['sharpe_ratio'],
                'benchmark_sharpe': benchmark_metrics['risk_adjusted_metrics']['sharpe_ratio'],
                'outperformance': strategy_metrics['return_metrics']['total_return_pct'] - benchmark_metrics['return_metrics']['total_return_pct']
            }
        }

    def _monte_carlo_simulation(self, returns: np.ndarray, n_simulations: int = 1000) -> Dict:
        """Run Monte Carlo simulation."""
        simulation_results = []

        for _ in range(n_simulations):
            # Resample returns with replacement
            sampled = np.random.choice(returns, size=len(returns), replace=True)
            cumulative = np.cumprod(1 + sampled)
            final_return = (cumulative[-1] - 1) * 100
            simulation_results.append(final_return)

        results = np.array(simulation_results)

        return {
            'mean_return': float(np.mean(results)),
            'median_return': float(np.median(results)),
            'std_return': float(np.std(results)),
            'percentile_5': float(np.percentile(results, 5)),
            'percentile_25': float(np.percentile(results, 25)),
            'percentile_75': float(np.percentile(results, 75)),
            'percentile_95': float(np.percentile(results, 95)),
            'probability_of_profit': float((results > 0).mean() * 100),
            'probability_of_20pct_gain': float((results > 20).mean() * 100),
            'probability_of_20pct_loss': float((results < -20).mean() * 100),
        }

    def predict_next_day(self) -> Dict:
        """Predict next day's direction."""
        if not self.trained:
            self.train()

        # Get latest features
        X = self.features.drop(['target'], axis=1)
        latest = X.iloc[-1:].values
        latest_scaled = self.scaler.transform(latest)

        # Get predictions from all models
        predictions = {}
        for name, model in self.models.items():
            pred = model.predict(latest_scaled)[0]
            proba = model.predict_proba(latest_scaled)[0] if hasattr(model, 'predict_proba') else None
            predictions[name] = {
                'direction': 'UP' if pred > 0 else 'DOWN',
                'confidence': float(max(proba)) * 100 if proba is not None else 50
            }

        # Ensemble
        ensemble = np.sign(sum([
            1 if p['direction'] == 'UP' else -1
            for p in predictions.values()
        ]))

        return {
            'symbol': self.symbol,
            'date': str(self.data.index[-1].date()),
            'current_price': float(self.data['Close'].iloc[-1]),
            'model_predictions': predictions,
            'ensemble_prediction': 'UP' if ensemble > 0 else 'DOWN',
            'recommendation': self._get_recommendation(predictions)
        }

    def _get_recommendation(self, predictions: Dict) -> str:
        """Generate recommendation based on model consensus."""
        up_count = sum(1 for p in predictions.values() if p['direction'] == 'UP')
        avg_confidence = np.mean([p['confidence'] for p in predictions.values()])

        if up_count >= 2 and avg_confidence > 60:
            return "STRONG BUY - High model consensus with good confidence"
        elif up_count >= 2:
            return "BUY - Model consensus bullish"
        elif up_count <= 1 and avg_confidence > 60:
            return "SELL - Model consensus bearish with confidence"
        elif up_count <= 1:
            return "HOLD/SELL - Model consensus bearish"
        else:
            return "HOLD - Mixed signals"


def run_enhanced_analysis(symbol: str) -> Dict:
    """Convenience function to run full analysis."""
    predictor = EnhancedMLPredictor(symbol)
    predictor.train()

    return {
        'prediction': predictor.predict_next_day(),
        'backtest': predictor.backtest_with_metrics()
    }
