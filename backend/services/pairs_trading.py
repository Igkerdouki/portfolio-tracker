"""
Statistical Arbitrage Pairs Trading with Kalman Filter
Implements mean-reversion strategy for correlated stock pairs.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')

try:
    import yfinance as yf
    HAS_YFINANCE = True
except ImportError:
    HAS_YFINANCE = False


class KalmanFilter:
    """
    Kalman Filter for dynamic hedge ratio estimation.

    The state is the hedge ratio (beta) between two assets.
    It adapts over time as the relationship changes.
    """

    def __init__(self, delta: float = 1e-4, ve: float = 1e-3):
        """
        Args:
            delta: Transition covariance (how much state can change between steps)
            ve: Observation variance (measurement noise)
        """
        self.delta = delta
        self.ve = ve

        # State variables
        self.theta = 0.0  # Current hedge ratio estimate
        self.P = 1.0      # State covariance (uncertainty)
        self.R = ve       # Observation variance

    def update(self, x: float, y: float) -> Tuple[float, float]:
        """
        Update the Kalman filter with new observation.

        Args:
            x: Price of asset X (e.g., V)
            y: Price of asset Y (e.g., MA)

        Returns:
            Tuple of (hedge_ratio, spread)
        """
        # Prediction step
        self.P = self.P + self.delta

        # Kalman gain
        K = self.P * x / (x * self.P * x + self.R)

        # Calculate spread (prediction error)
        spread = y - self.theta * x

        # Update step
        self.theta = self.theta + K * spread
        self.P = (1 - K * x) * self.P

        return self.theta, spread

    def reset(self):
        """Reset filter state."""
        self.theta = 0.0
        self.P = 1.0


class PairsTrader:
    """
    Pairs trading system with Kalman filter hedge ratio estimation.
    """

    def __init__(
        self,
        symbol_x: str = "V",    # Stock X (e.g., Visa)
        symbol_y: str = "MA",   # Stock Y (e.g., Mastercard)
        lookback: int = 60,     # Z-score lookback window
        entry_z: float = 2.0,   # Entry threshold
        exit_z: float = 0.5,    # Exit threshold
        atr_period: int = 14,   # ATR period for position sizing
        stop_loss_z: float = 4.0,  # Stop loss threshold
    ):
        self.symbol_x = symbol_x
        self.symbol_y = symbol_y
        self.lookback = lookback
        self.entry_z = entry_z
        self.exit_z = exit_z
        self.atr_period = atr_period
        self.stop_loss_z = stop_loss_z

        self.kalman = KalmanFilter()
        self.data = None
        self.signals = None

    def fetch_data(self, period: str = "5y") -> pd.DataFrame:
        """
        Fetch OHLCV data for both stocks.
        """
        if not HAS_YFINANCE:
            raise ImportError("yfinance not installed")

        # Fetch data for each symbol separately (more reliable)
        df_x = yf.download(self.symbol_x, period=period, progress=False)
        df_y = yf.download(self.symbol_y, period=period, progress=False)

        if len(df_x) == 0:
            raise ValueError(f"No data found for {self.symbol_x}")
        if len(df_y) == 0:
            raise ValueError(f"No data found for {self.symbol_y}")

        # Handle multi-index columns from yfinance
        def flatten_columns(df, symbol):
            """Flatten multi-index columns to simple column names."""
            if isinstance(df.columns, pd.MultiIndex):
                # yfinance returns (Price, Ticker) format
                new_cols = {}
                for col in df.columns:
                    price_name = col[0]  # e.g., 'Close', 'High', etc.
                    new_cols[col] = price_name
                df = df.rename(columns=new_cols)
            return df

        df_x = flatten_columns(df_x, self.symbol_x)
        df_y = flatten_columns(df_y, self.symbol_y)

        # Get common dates
        common_dates = df_x.index.intersection(df_y.index)

        if len(common_dates) == 0:
            raise ValueError(f"No overlapping data for {self.symbol_x} and {self.symbol_y}")

        # Create combined dataframe
        df = pd.DataFrame(index=common_dates)

        for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
            if col in df_x.columns:
                df[f'{self.symbol_x}_{col}'] = df_x.loc[common_dates, col].values
            if col in df_y.columns:
                df[f'{self.symbol_y}_{col}'] = df_y.loc[common_dates, col].values

        df = df.dropna()

        if len(df) == 0:
            raise ValueError(f"No valid data after merging {self.symbol_x} and {self.symbol_y}")

        self.data = df
        return df

    def calculate_atr(self, high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
        """Calculate Average True Range."""
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(window=self.atr_period).mean()

    def generate_signals(self) -> pd.DataFrame:
        """
        Generate trading signals using Kalman filter and Z-score.
        """
        if self.data is None:
            self.fetch_data()

        df = self.data.copy()
        x_close = df[f'{self.symbol_x}_Close']
        y_close = df[f'{self.symbol_y}_Close']

        # Apply Kalman filter to estimate hedge ratio and spread
        hedge_ratios = []
        spreads = []

        self.kalman.reset()
        for x, y in zip(x_close, y_close):
            hr, spread = self.kalman.update(x, y)
            hedge_ratios.append(hr)
            spreads.append(spread)

        df['hedge_ratio'] = hedge_ratios
        df['spread'] = spreads

        # Calculate rolling Z-score
        df['spread_mean'] = df['spread'].rolling(window=self.lookback).mean()
        df['spread_std'] = df['spread'].rolling(window=self.lookback).std()
        df['z_score'] = (df['spread'] - df['spread_mean']) / df['spread_std']

        # Calculate ATR for position sizing (using stock X)
        df['atr_x'] = self.calculate_atr(
            df[f'{self.symbol_x}_High'],
            df[f'{self.symbol_x}_Low'],
            df[f'{self.symbol_x}_Close']
        )
        df['atr_y'] = self.calculate_atr(
            df[f'{self.symbol_y}_High'],
            df[f'{self.symbol_y}_Low'],
            df[f'{self.symbol_y}_Close']
        )

        # Average ATR for the pair
        df['pair_atr'] = (df['atr_x'] + df['atr_y'] * df['hedge_ratio'].abs()) / 2

        # Position sizing: inversely proportional to ATR
        # Normalize to target risk
        target_risk = 100  # Base position sizing unit
        df['position_size'] = target_risk / df['pair_atr']
        df['position_size'] = df['position_size'].clip(lower=0.1, upper=10)  # Limits

        # Generate signals
        position = 0
        entry_price_x = 0
        entry_price_y = 0

        signals = []
        for i in range(len(df)):
            z = df['z_score'].iloc[i]
            pos_size = df['position_size'].iloc[i]

            if pd.isna(z):
                signals.append({'signal': 0, 'position': 0, 'action': 'wait'})
                continue

            action = 'hold'

            # Entry logic
            if position == 0:
                if z > self.entry_z:
                    # Spread too high: short X, long Y (short the spread)
                    position = -1
                    entry_price_x = df[f'{self.symbol_x}_Close'].iloc[i]
                    entry_price_y = df[f'{self.symbol_y}_Close'].iloc[i]
                    action = 'short_spread'
                elif z < -self.entry_z:
                    # Spread too low: long X, short Y (long the spread)
                    position = 1
                    entry_price_x = df[f'{self.symbol_x}_Close'].iloc[i]
                    entry_price_y = df[f'{self.symbol_y}_Close'].iloc[i]
                    action = 'long_spread'

            # Exit logic
            elif position != 0:
                # Stop loss
                if abs(z) > self.stop_loss_z:
                    action = 'stop_loss'
                    position = 0
                # Take profit (mean reversion)
                elif abs(z) < self.exit_z:
                    action = 'exit'
                    position = 0

            signals.append({
                'signal': 1 if action in ['long_spread', 'short_spread'] else (-1 if action in ['exit', 'stop_loss'] else 0),
                'position': position * pos_size,
                'action': action
            })

        signals_df = pd.DataFrame(signals, index=df.index)
        df = pd.concat([df, signals_df], axis=1)

        self.signals = df
        return df

    def backtest(self, initial_capital: float = 100000) -> Dict:
        """
        Backtest the pairs trading strategy.
        """
        if self.signals is None:
            self.generate_signals()

        df = self.signals.copy()

        # Drop rows with NaN in z_score (which has the lookback period NaN)
        df = df.dropna(subset=['z_score'])

        if len(df) < 10:
            return {"error": f"Not enough data after filtering. Got {len(df)} rows."}

        x_close = df[f'{self.symbol_x}_Close']
        y_close = df[f'{self.symbol_y}_Close']
        hedge_ratio = df['hedge_ratio']
        position = df['position']

        # Calculate daily returns
        x_return = x_close.pct_change()
        y_return = y_close.pct_change()

        # Strategy return: position * (x_return - hedge_ratio * y_return)
        # For long spread: profit from X up, Y down
        # For short spread: profit from X down, Y up
        spread_return = x_return - hedge_ratio * y_return
        strategy_return = position.shift(1) * spread_return

        # Remove NaN
        strategy_return = strategy_return.dropna()

        if len(strategy_return) < 10:
            return {"error": "Not enough valid returns to calculate metrics"}

        # Equity curve
        equity = initial_capital * (1 + strategy_return).cumprod()

        # Calculate metrics
        total_return = (equity.iloc[-1] / initial_capital - 1) * 100
        n_days = len(equity)
        annual_return = ((equity.iloc[-1] / initial_capital) ** (252 / max(n_days, 1)) - 1) * 100
        sharpe = np.sqrt(252) * strategy_return.mean() / strategy_return.std() if strategy_return.std() > 0 else 0

        # Max drawdown
        peak = equity.cummax()
        drawdown = (equity - peak) / peak
        max_drawdown = drawdown.min() * 100

        # Win rate
        trades = df[df['action'].isin(['long_spread', 'short_spread', 'exit', 'stop_loss'])]
        n_trades = len(trades[trades['action'].isin(['long_spread', 'short_spread'])])

        winning_days = (strategy_return > 0).sum()
        total_days = len(strategy_return)
        win_rate = winning_days / total_days * 100 if total_days > 0 else 0

        # Compare to buy and hold (just holding X)
        buy_hold_return = (x_close.iloc[-1] / x_close.iloc[0] - 1) * 100

        # Correlation check
        correlation = x_close.corr(y_close)

        return {
            "pair": f"{self.symbol_x}/{self.symbol_y}",
            "period": f"{df.index[0].date()} to {df.index[-1].date()}",
            "data_points": len(df),
            "correlation": float(correlation),
            "strategy_metrics": {
                "total_return_pct": float(total_return),
                "annual_return_pct": float(annual_return),
                "sharpe_ratio": float(sharpe),
                "max_drawdown_pct": float(max_drawdown),
                "win_rate_pct": float(win_rate),
                "n_trades": int(n_trades),
                "final_equity": float(equity.iloc[-1])
            },
            "benchmark": {
                "buy_hold_return_pct": float(buy_hold_return),
                "alpha": float(total_return - buy_hold_return)
            },
            "parameters": {
                "lookback": self.lookback,
                "entry_z": self.entry_z,
                "exit_z": self.exit_z,
                "atr_period": self.atr_period,
                "stop_loss_z": self.stop_loss_z
            },
            "current_state": {
                "hedge_ratio": float(df['hedge_ratio'].iloc[-1]),
                "z_score": float(df['z_score'].iloc[-1]),
                "spread": float(df['spread'].iloc[-1]),
                "current_position": float(df['position'].iloc[-1]),
                "signal": self._interpret_z_score(df['z_score'].iloc[-1])
            },
            "equity_curve": equity.tolist()[-252:],  # Last year
            "z_score_history": df['z_score'].tolist()[-252:]
        }

    def _interpret_z_score(self, z: float) -> str:
        """Interpret current Z-score for signal."""
        if z > self.entry_z:
            return f"SHORT SPREAD (Z={z:.2f} > {self.entry_z})"
        elif z < -self.entry_z:
            return f"LONG SPREAD (Z={z:.2f} < -{self.entry_z})"
        elif abs(z) < self.exit_z:
            return f"NEUTRAL (Z={z:.2f} near 0)"
        else:
            return f"NO SIGNAL (Z={z:.2f})"

    def get_current_signal(self) -> Dict:
        """Get current trading signal."""
        if self.signals is None:
            self.generate_signals()

        df = self.signals
        latest = df.iloc[-1]

        return {
            "pair": f"{self.symbol_x}/{self.symbol_y}",
            "date": str(df.index[-1].date()),
            "prices": {
                self.symbol_x: float(latest[f'{self.symbol_x}_Close']),
                self.symbol_y: float(latest[f'{self.symbol_y}_Close']),
            },
            "hedge_ratio": float(latest['hedge_ratio']),
            "spread": float(latest['spread']),
            "z_score": float(latest['z_score']),
            "position_size": float(latest['position_size']),
            "signal": self._interpret_z_score(latest['z_score']),
            "action": latest['action']
        }


class PairsScanner:
    """
    Scan for tradeable pairs across multiple stocks.
    """

    def __init__(self):
        self.pairs_cache: Dict[str, PairsTrader] = {}

    def scan_pair(self, symbol_x: str, symbol_y: str, period: str = "2y") -> Dict:
        """
        Scan a pair for trading opportunity.
        """
        cache_key = f"{symbol_x}_{symbol_y}"

        if cache_key not in self.pairs_cache:
            trader = PairsTrader(symbol_x=symbol_x, symbol_y=symbol_y)
            trader.fetch_data(period)
            self.pairs_cache[cache_key] = trader
        else:
            trader = self.pairs_cache[cache_key]

        trader.generate_signals()
        return trader.get_current_signal()

    def scan_multiple(self, pairs: List[Tuple[str, str]]) -> List[Dict]:
        """
        Scan multiple pairs.
        """
        results = []
        for x, y in pairs:
            try:
                signal = self.scan_pair(x, y)
                results.append(signal)
            except Exception as e:
                results.append({
                    "pair": f"{x}/{y}",
                    "error": str(e)
                })
        return results


# Predefined pairs
COMMON_PAIRS = [
    ("V", "MA"),       # Visa / Mastercard
    ("KO", "PEP"),     # Coca-Cola / Pepsi
    ("XOM", "CVX"),    # Exxon / Chevron
    ("JPM", "BAC"),    # JPMorgan / Bank of America
    ("MSFT", "AAPL"),  # Microsoft / Apple
    ("HD", "LOW"),     # Home Depot / Lowe's
    ("GS", "MS"),      # Goldman Sachs / Morgan Stanley
    ("DIS", "CMCSA"),  # Disney / Comcast
]

# Global instances
pairs_scanner = PairsScanner()
