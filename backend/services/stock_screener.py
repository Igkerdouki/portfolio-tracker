"""
Stock Screener & Recommender
Suggests high-yield stocks for short-term and long-term investments.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import warnings
warnings.filterwarnings('ignore')

try:
    import yfinance as yf
    HAS_YFINANCE = True
except ImportError:
    HAS_YFINANCE = False


class StockScreener:
    """
    Screens and ranks stocks based on multiple criteria.
    Provides recommendations for short-term trades and long-term investments.
    """

    # Major stock universes
    SP500_TOP = [
        "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK-B", "UNH", "JNJ",
        "V", "XOM", "JPM", "PG", "MA", "HD", "CVX", "LLY", "MRK", "ABBV",
        "PEP", "KO", "AVGO", "COST", "WMT", "MCD", "CSCO", "TMO", "ACN", "ABT",
        "CRM", "DHR", "NKE", "CMCSA", "VZ", "INTC", "AMD", "ADBE", "TXN", "NEE",
        "PM", "UNP", "RTX", "HON", "LOW", "IBM", "QCOM", "ORCL", "CAT", "GE"
    ]

    GROWTH_STOCKS = [
        "NVDA", "AMD", "TSLA", "META", "NFLX", "CRM", "NOW", "SHOP", "SQ", "PYPL",
        "ROKU", "ZM", "DDOG", "SNOW", "CRWD", "ZS", "NET", "MDB", "TEAM", "OKTA"
    ]

    DIVIDEND_STOCKS = [
        "JNJ", "PG", "KO", "PEP", "VZ", "T", "MO", "PM", "XOM", "CVX",
        "IBM", "MMM", "CAT", "EMR", "GPC", "SWK", "ED", "DUK", "SO", "AEP"
    ]

    VALUE_STOCKS = [
        "BRK-B", "JPM", "BAC", "WFC", "C", "GS", "MS", "UNH", "CVS", "CI",
        "GM", "F", "TGT", "WMT", "COST", "HD", "LOW", "DE", "CAT", "BA"
    ]

    TECH_STOCKS = [
        "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA", "AMD", "INTC", "AVGO",
        "QCOM", "TXN", "MU", "AMAT", "LRCX", "ADI", "MRVL", "ON", "NXPI", "MCHP"
    ]

    def __init__(self):
        self.cache = {}
        self.cache_timeout = timedelta(hours=1)

    def screen_stocks(
        self,
        universe: str = "sp500",
        strategy: str = "momentum",
        min_volume: int = 1000000,
        min_price: float = 5.0,
        max_price: float = 10000.0,
        limit: int = 20
    ) -> List[Dict]:
        """
        Screen stocks based on strategy.

        Args:
            universe: Stock universe ('sp500', 'growth', 'dividend', 'value', 'tech', 'all')
            strategy: Screening strategy ('momentum', 'value', 'growth', 'dividend', 'volatility', 'reversal')
            min_volume: Minimum average daily volume
            min_price: Minimum stock price
            max_price: Maximum stock price
            limit: Number of stocks to return

        Returns:
            List of stock recommendations with scores
        """
        if not HAS_YFINANCE:
            return [{"error": "yfinance not installed"}]

        # Get stock universe
        stocks = self._get_universe(universe)

        # Fetch data and calculate scores
        results = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(self._analyze_stock, symbol, strategy): symbol for symbol in stocks}

            for future in as_completed(futures):
                try:
                    result = future.result()
                    if result and result.get('score', 0) > 0:
                        # Apply filters
                        if (result.get('avg_volume', 0) >= min_volume and
                            min_price <= result.get('current_price', 0) <= max_price):
                            results.append(result)
                except Exception:
                    pass

        # Sort by score and return top picks
        results.sort(key=lambda x: x.get('score', 0), reverse=True)
        return results[:limit]

    def _get_universe(self, universe: str) -> List[str]:
        """Get list of stocks for the specified universe."""
        universes = {
            "sp500": self.SP500_TOP,
            "growth": self.GROWTH_STOCKS,
            "dividend": self.DIVIDEND_STOCKS,
            "value": self.VALUE_STOCKS,
            "tech": self.TECH_STOCKS,
            "all": list(set(self.SP500_TOP + self.GROWTH_STOCKS + self.DIVIDEND_STOCKS +
                           self.VALUE_STOCKS + self.TECH_STOCKS))
        }
        return universes.get(universe, self.SP500_TOP)

    def _analyze_stock(self, symbol: str, strategy: str) -> Optional[Dict]:
        """Analyze a single stock based on strategy."""
        try:
            # Fetch data
            df = yf.download(symbol, period="1y", progress=False)
            if len(df) < 50:
                return None

            # Handle MultiIndex columns
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            close = df['Close']
            volume = df['Volume']
            high = df['High']
            low = df['Low']

            # Basic metrics
            current_price = float(close.iloc[-1])
            avg_volume = float(volume.mean())

            # Calculate indicators
            returns = close.pct_change()
            volatility = float(returns.std() * np.sqrt(252) * 100)

            # Moving averages
            sma_20 = close.rolling(20).mean()
            sma_50 = close.rolling(50).mean()
            sma_200 = close.rolling(200).mean()

            # RSI
            rsi = self._calculate_rsi(close)

            # MACD
            ema_12 = close.ewm(span=12).mean()
            ema_26 = close.ewm(span=26).mean()
            macd = ema_12 - ema_26
            signal = macd.ewm(span=9).mean()
            macd_hist = macd - signal

            # Performance
            return_1w = float((close.iloc[-1] / close.iloc[-5] - 1) * 100) if len(close) > 5 else 0
            return_1m = float((close.iloc[-1] / close.iloc[-21] - 1) * 100) if len(close) > 21 else 0
            return_3m = float((close.iloc[-1] / close.iloc[-63] - 1) * 100) if len(close) > 63 else 0
            return_6m = float((close.iloc[-1] / close.iloc[-126] - 1) * 100) if len(close) > 126 else 0
            return_1y = float((close.iloc[-1] / close.iloc[0] - 1) * 100)

            # Calculate score based on strategy
            score = self._calculate_score(
                strategy=strategy,
                returns={
                    '1w': return_1w,
                    '1m': return_1m,
                    '3m': return_3m,
                    '6m': return_6m,
                    '1y': return_1y
                },
                rsi=float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50,
                macd_hist=float(macd_hist.iloc[-1]) if not pd.isna(macd_hist.iloc[-1]) else 0,
                volatility=volatility,
                price_vs_sma20=float(current_price / sma_20.iloc[-1]) if not pd.isna(sma_20.iloc[-1]) else 1,
                price_vs_sma50=float(current_price / sma_50.iloc[-1]) if not pd.isna(sma_50.iloc[-1]) else 1,
                price_vs_sma200=float(current_price / sma_200.iloc[-1]) if not pd.isna(sma_200.iloc[-1]) else 1,
            )

            # Trend determination
            trend = "BULLISH" if current_price > sma_50.iloc[-1] and sma_50.iloc[-1] > sma_200.iloc[-1] else \
                    "BEARISH" if current_price < sma_50.iloc[-1] and sma_50.iloc[-1] < sma_200.iloc[-1] else \
                    "NEUTRAL"

            # Signal strength
            signal_strength = "STRONG" if abs(score) > 80 else "MODERATE" if abs(score) > 50 else "WEAK"

            return {
                "symbol": symbol,
                "current_price": current_price,
                "score": score,
                "signal_strength": signal_strength,
                "trend": trend,
                "strategy": strategy,
                "metrics": {
                    "return_1w_pct": return_1w,
                    "return_1m_pct": return_1m,
                    "return_3m_pct": return_3m,
                    "return_6m_pct": return_6m,
                    "return_1y_pct": return_1y,
                    "rsi": float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50,
                    "volatility_pct": volatility,
                    "avg_volume": avg_volume,
                    "price_vs_sma20": float(current_price / sma_20.iloc[-1]) if not pd.isna(sma_20.iloc[-1]) else 1,
                    "price_vs_sma50": float(current_price / sma_50.iloc[-1]) if not pd.isna(sma_50.iloc[-1]) else 1,
                    "macd_signal": "BUY" if macd_hist.iloc[-1] > 0 else "SELL",
                },
                "recommendation": self._get_recommendation(score, strategy),
                "holding_period": self._get_holding_period(strategy),
            }

        except Exception as e:
            return None

    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI indicator."""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def _calculate_score(
        self,
        strategy: str,
        returns: Dict[str, float],
        rsi: float,
        macd_hist: float,
        volatility: float,
        price_vs_sma20: float,
        price_vs_sma50: float,
        price_vs_sma200: float
    ) -> float:
        """Calculate composite score based on strategy."""

        if strategy == "momentum":
            # Momentum: Recent returns + trend alignment
            score = (
                returns['1w'] * 0.15 +
                returns['1m'] * 0.25 +
                returns['3m'] * 0.30 +
                returns['6m'] * 0.20 +
                (price_vs_sma50 - 1) * 100 * 0.10
            )
            # RSI boost/penalty
            if 50 < rsi < 70:
                score *= 1.1
            elif rsi > 80:
                score *= 0.8

        elif strategy == "reversal":
            # Mean reversion: Oversold with positive momentum shift
            score = 0
            if rsi < 30:
                score += (30 - rsi) * 2
            if price_vs_sma20 < 0.95:
                score += (0.95 - price_vs_sma20) * 100
            if macd_hist > 0:
                score += 20
            if returns['1w'] > 0 and returns['1m'] < 0:
                score += 15

        elif strategy == "value":
            # Value: Price below averages with decent fundamentals
            score = 0
            if price_vs_sma200 < 1.0:
                score += (1 - price_vs_sma200) * 50
            if price_vs_sma50 < 1.0:
                score += (1 - price_vs_sma50) * 30
            if volatility < 30:
                score += (30 - volatility) * 0.5
            # But not falling knife
            if returns['1m'] > -10:
                score += 10

        elif strategy == "growth":
            # Growth: Strong consistent returns
            score = (
                returns['1y'] * 0.30 +
                returns['6m'] * 0.25 +
                returns['3m'] * 0.25 +
                returns['1m'] * 0.20
            )
            # Trend bonus
            if price_vs_sma50 > 1 and price_vs_sma200 > 1:
                score *= 1.2

        elif strategy == "volatility":
            # High volatility plays (for active traders)
            score = volatility * 0.5
            if abs(returns['1w']) > 5:
                score += abs(returns['1w'])
            if 30 < rsi < 70:  # Not extreme
                score *= 1.1

        elif strategy == "dividend":
            # Stability focused (placeholder - would need dividend data)
            score = 50 - volatility * 0.5  # Lower volatility better
            if price_vs_sma200 > 0.9:
                score += 20
            if returns['1y'] > 0:
                score += returns['1y'] * 0.3

        else:
            # Default balanced
            score = (returns['3m'] + returns['6m']) / 2

        return round(score, 2)

    def _get_recommendation(self, score: float, strategy: str) -> str:
        """Get human-readable recommendation."""
        if score >= 80:
            return "STRONG BUY - Excellent setup for this strategy"
        elif score >= 60:
            return "BUY - Good opportunity with favorable conditions"
        elif score >= 40:
            return "MODERATE BUY - Consider with position sizing"
        elif score >= 20:
            return "HOLD/WATCH - Wait for better entry or monitor"
        elif score >= 0:
            return "NEUTRAL - No clear edge currently"
        else:
            return "AVOID - Conditions not favorable"

    def _get_holding_period(self, strategy: str) -> str:
        """Get recommended holding period."""
        periods = {
            "momentum": "2-6 weeks",
            "reversal": "1-2 weeks",
            "value": "6-12 months",
            "growth": "1-3 years",
            "volatility": "1-5 days",
            "dividend": "1+ years"
        }
        return periods.get(strategy, "Variable")

    def get_short_term_picks(self, limit: int = 10) -> Dict:
        """Get best short-term trading opportunities."""
        momentum = self.screen_stocks(universe="all", strategy="momentum", limit=limit)
        reversal = self.screen_stocks(universe="all", strategy="reversal", limit=limit)

        return {
            "momentum_plays": momentum,
            "reversal_plays": reversal,
            "generated_at": datetime.now().isoformat(),
            "recommendation": "Short-term picks for 1-4 week holding periods"
        }

    def get_long_term_picks(self, limit: int = 10) -> Dict:
        """Get best long-term investment opportunities."""
        growth = self.screen_stocks(universe="growth", strategy="growth", limit=limit)
        value = self.screen_stocks(universe="value", strategy="value", limit=limit)
        dividend = self.screen_stocks(universe="dividend", strategy="dividend", limit=limit)

        return {
            "growth_stocks": growth,
            "value_stocks": value,
            "dividend_stocks": dividend,
            "generated_at": datetime.now().isoformat(),
            "recommendation": "Long-term picks for 6+ month holding periods"
        }

    def get_all_recommendations(self) -> Dict:
        """Get comprehensive recommendations."""
        return {
            "short_term": self.get_short_term_picks(10),
            "long_term": self.get_long_term_picks(10),
            "market_overview": self._get_market_overview(),
        }

    def _get_market_overview(self) -> Dict:
        """Quick market health check."""
        try:
            spy = yf.download("SPY", period="1mo", progress=False)
            if isinstance(spy.columns, pd.MultiIndex):
                spy.columns = spy.columns.get_level_values(0)

            spy_return = (spy['Close'].iloc[-1] / spy['Close'].iloc[0] - 1) * 100
            spy_trend = "BULLISH" if spy_return > 2 else "BEARISH" if spy_return < -2 else "NEUTRAL"

            vix = yf.download("^VIX", period="5d", progress=False)
            if isinstance(vix.columns, pd.MultiIndex):
                vix.columns = vix.columns.get_level_values(0)
            current_vix = float(vix['Close'].iloc[-1])

            return {
                "spy_return_1m": float(spy_return),
                "market_trend": spy_trend,
                "vix": current_vix,
                "volatility_regime": "HIGH" if current_vix > 25 else "NORMAL" if current_vix > 15 else "LOW",
                "trading_environment": "RISK-ON" if current_vix < 20 and spy_trend == "BULLISH" else "RISK-OFF"
            }
        except:
            return {"error": "Could not fetch market data"}


# Global instance
stock_screener = StockScreener()
