"""
Data Collector Agent
Collects financial data from Alpha Vantage API for stock analysis.
"""

import os
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
import time
from dotenv import load_dotenv

load_dotenv()

ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")
ALPHA_VANTAGE_BASE_URL = "https://www.alphavantage.co/query"

DATA_FILE = os.path.join(os.path.dirname(__file__), '..', '..', 'collected_data.json')


class DataCollector:
    """
    Collects financial data from Alpha Vantage:
    - OVERVIEW: Company fundamentals
    - TIME_SERIES_DAILY: Historical prices for technicals
    - NEWS_SENTIMENT: News and sentiment
    """

    def __init__(self):
        self.data = self._load_data()
        self.request_count = 0
        self.last_request_time = None

    def _load_data(self) -> Dict:
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {
            'stocks': {},
            'last_collection': None,
        }

    def _save_data(self):
        try:
            with open(DATA_FILE, 'w') as f:
                json.dump(self.data, f, indent=2, default=str)
        except:
            pass

    def _rate_limit(self):
        """Respect Alpha Vantage rate limits (5 requests/minute)."""
        if self.last_request_time:
            elapsed = (datetime.now() - self.last_request_time).total_seconds()
            if elapsed < 12:  # Wait 12 seconds between requests to be safe
                time.sleep(12 - elapsed)
        self.last_request_time = datetime.now()
        self.request_count += 1

    def _api_request(self, params: Dict) -> Optional[Dict]:
        """Make a rate-limited request to Alpha Vantage."""
        self._rate_limit()
        params["apikey"] = ALPHA_VANTAGE_API_KEY

        try:
            response = requests.get(ALPHA_VANTAGE_BASE_URL, params=params, timeout=15)
            data = response.json()

            if "Error Message" in data:
                print(f"Alpha Vantage error: {data['Error Message']}")
                return None
            if "Note" in data:
                print(f"Alpha Vantage rate limit hit: {data['Note']}")
                return None

            return data
        except Exception as e:
            print(f"API request error: {e}")
            return None

    def collect_stock_data(self, symbol: str) -> Dict:
        """Collect comprehensive data for a single stock."""
        print(f"Collecting data for {symbol}...")

        data = {
            'symbol': symbol.upper(),
            'collected_at': datetime.now().isoformat(),
            'fundamentals': {},
            'technical': {},
            'news': [],
            'sentiment': {},
        }

        # 1. Get fundamentals from OVERVIEW
        overview = self._get_overview(symbol)
        if overview:
            data['fundamentals'] = overview

        # 2. Get technical indicators from daily prices
        technicals = self._get_technicals(symbol)
        if technicals:
            data['technical'] = technicals

        # 3. Get news and sentiment
        news_data = self._get_news_sentiment(symbol)
        if news_data:
            data['news'] = news_data.get('articles', [])
            data['sentiment'] = news_data.get('sentiment', {})

        # Cache the data
        self.data['stocks'][symbol.upper()] = data
        self.data['last_collection'] = datetime.now().isoformat()
        self._save_data()

        return data

    def _get_overview(self, symbol: str) -> Dict:
        """Get company fundamentals from OVERVIEW endpoint."""
        data = self._api_request({
            "function": "OVERVIEW",
            "symbol": symbol
        })

        if not data or "Symbol" not in data:
            return {}

        # Extract key metrics
        return {
            'name': data.get('Name'),
            'sector': data.get('Sector'),
            'industry': data.get('Industry'),
            'market_cap': self._safe_float(data.get('MarketCapitalization')),
            'pe_ratio': self._safe_float(data.get('PERatio')),
            'forward_pe': self._safe_float(data.get('ForwardPE')),
            'peg_ratio': self._safe_float(data.get('PEGRatio')),
            'price_to_book': self._safe_float(data.get('PriceToBookRatio')),
            'price_to_sales': self._safe_float(data.get('PriceToSalesRatioTTM')),
            'ev_to_revenue': self._safe_float(data.get('EVToRevenue')),
            'ev_to_ebitda': self._safe_float(data.get('EVToEBITDA')),
            'profit_margin': self._safe_float(data.get('ProfitMargin')),
            'operating_margin': self._safe_float(data.get('OperatingMarginTTM')),
            'roe': self._safe_float(data.get('ReturnOnEquityTTM')),
            'roa': self._safe_float(data.get('ReturnOnAssetsTTM')),
            'revenue': self._safe_float(data.get('RevenueTTM')),
            'revenue_per_share': self._safe_float(data.get('RevenuePerShareTTM')),
            'quarterly_revenue_growth': self._safe_float(data.get('QuarterlyRevenueGrowthYOY')),
            'quarterly_earnings_growth': self._safe_float(data.get('QuarterlyEarningsGrowthYOY')),
            'eps': self._safe_float(data.get('EPS')),
            'eps_growth': self._safe_float(data.get('QuarterlyEarningsGrowthYOY')),
            'dividend_yield': self._safe_float(data.get('DividendYield')),
            'dividend_per_share': self._safe_float(data.get('DividendPerShare')),
            'payout_ratio': self._safe_float(data.get('PayoutRatio')),
            'book_value': self._safe_float(data.get('BookValue')),
            'debt_to_equity': self._safe_float(data.get('DebtToEquityRatio')) if data.get('DebtToEquityRatio') else None,
            'current_ratio': self._safe_float(data.get('CurrentRatio')),
            'beta': self._safe_float(data.get('Beta')),
            '52w_high': self._safe_float(data.get('52WeekHigh')),
            '52w_low': self._safe_float(data.get('52WeekLow')),
            '50d_ma': self._safe_float(data.get('50DayMovingAverage')),
            '200d_ma': self._safe_float(data.get('200DayMovingAverage')),
            'analyst_target': self._safe_float(data.get('AnalystTargetPrice')),
            'analyst_rating': data.get('AnalystRatingStrongBuy'),
            'shares_outstanding': self._safe_float(data.get('SharesOutstanding')),
            'shares_short': self._safe_float(data.get('SharesShort')),
            'short_ratio': self._safe_float(data.get('ShortRatio')),
            'current_price': self._safe_float(data.get('50DayMovingAverage')),  # Approximation
        }

    def _get_technicals(self, symbol: str) -> Dict:
        """Calculate technical indicators from daily price data."""
        data = self._api_request({
            "function": "TIME_SERIES_DAILY",
            "symbol": symbol,
            "outputsize": "compact"  # Last 100 days
        })

        if not data or "Time Series (Daily)" not in data:
            return {}

        time_series = data["Time Series (Daily)"]

        # Convert to list of prices (newest first)
        prices = []
        for date_str in sorted(time_series.keys(), reverse=True):
            prices.append({
                'date': date_str,
                'close': float(time_series[date_str]['4. close']),
                'high': float(time_series[date_str]['2. high']),
                'low': float(time_series[date_str]['3. low']),
                'volume': int(float(time_series[date_str]['5. volume']))
            })

        if len(prices) < 14:
            return {}

        closes = [p['close'] for p in prices]

        # Calculate indicators
        technicals = {
            'current_price': closes[0],
            'price_change_1d': self._pct_change(closes[0], closes[1]) if len(closes) > 1 else 0,
            'price_change_5d': self._pct_change(closes[0], closes[4]) if len(closes) > 4 else 0,
            'price_change_20d': self._pct_change(closes[0], closes[19]) if len(closes) > 19 else 0,
        }

        # RSI (14-day)
        technicals['rsi'] = self._calculate_rsi(closes[:14])

        # Moving averages
        if len(closes) >= 50:
            technicals['sma_50'] = sum(closes[:50]) / 50
            technicals['price_vs_sma50'] = (closes[0] / technicals['sma_50'] - 1) * 100

        if len(closes) >= 20:
            technicals['sma_20'] = sum(closes[:20]) / 20

        # MACD (12, 26, 9)
        if len(closes) >= 26:
            ema12 = self._calculate_ema(closes[:12], 12)
            ema26 = self._calculate_ema(closes[:26], 26)
            technicals['macd'] = ema12 - ema26
            technicals['macd_signal'] = 'bullish' if technicals['macd'] > 0 else 'bearish'

        # Volatility (20-day)
        if len(closes) >= 20:
            returns = [(closes[i] / closes[i+1] - 1) for i in range(19)]
            avg_return = sum(returns) / len(returns)
            variance = sum((r - avg_return) ** 2 for r in returns) / len(returns)
            technicals['volatility_20d'] = (variance ** 0.5) * 100

        # 52-week position
        if len(closes) >= 52:
            high_52w = max(closes[:252]) if len(closes) >= 252 else max(closes)
            low_52w = min(closes[:252]) if len(closes) >= 252 else min(closes)
            technicals['52w_high'] = high_52w
            technicals['52w_low'] = low_52w
            technicals['price_vs_52w_high'] = (closes[0] / high_52w - 1) * 100
            technicals['price_vs_52w_low'] = (closes[0] / low_52w - 1) * 100

        return technicals

    def _get_news_sentiment(self, symbol: str) -> Dict:
        """Get news and sentiment from NEWS_SENTIMENT endpoint."""
        data = self._api_request({
            "function": "NEWS_SENTIMENT",
            "tickers": symbol,
            "limit": 10
        })

        if not data or "feed" not in data:
            return {}

        articles = []
        sentiment_scores = []

        for item in data.get("feed", [])[:10]:
            # Find sentiment for this specific ticker
            ticker_sentiment = None
            for ts in item.get("ticker_sentiment", []):
                if ts.get("ticker") == symbol.upper():
                    ticker_sentiment = ts
                    break

            sentiment_score = float(ticker_sentiment.get("ticker_sentiment_score", 0)) if ticker_sentiment else 0
            sentiment_scores.append(sentiment_score)

            articles.append({
                'title': item.get('title', ''),
                'source': item.get('source', ''),
                'url': item.get('url', ''),
                'published': item.get('time_published', ''),
                'sentiment_score': sentiment_score,
                'sentiment_label': ticker_sentiment.get("ticker_sentiment_label", "Neutral") if ticker_sentiment else "Neutral"
            })

        # Calculate overall sentiment
        avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0

        return {
            'articles': articles,
            'sentiment': {
                'average_score': round(avg_sentiment, 3),
                'label': 'Bullish' if avg_sentiment > 0.1 else ('Bearish' if avg_sentiment < -0.1 else 'Neutral'),
                'article_count': len(articles),
                'bullish_count': sum(1 for s in sentiment_scores if s > 0.1),
                'bearish_count': sum(1 for s in sentiment_scores if s < -0.1),
                'neutral_count': sum(1 for s in sentiment_scores if -0.1 <= s <= 0.1),
            }
        }

    def _safe_float(self, value) -> Optional[float]:
        """Safely convert to float."""
        if value is None or value == 'None' or value == '-':
            return None
        try:
            return float(value)
        except:
            return None

    def _pct_change(self, current: float, previous: float) -> float:
        """Calculate percentage change."""
        if previous == 0:
            return 0
        return round((current / previous - 1) * 100, 2)

    def _calculate_rsi(self, prices: List[float]) -> float:
        """Calculate RSI from prices (newest first)."""
        if len(prices) < 14:
            return 50  # Default neutral

        gains = []
        losses = []

        for i in range(len(prices) - 1):
            change = prices[i] - prices[i + 1]  # Newest first, so this is correct
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))

        avg_gain = sum(gains) / len(gains) if gains else 0
        avg_loss = sum(losses) / len(losses) if losses else 0

        if avg_loss == 0:
            return 100

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return round(rsi, 2)

    def _calculate_ema(self, prices: List[float], period: int) -> float:
        """Calculate EMA."""
        if len(prices) < period:
            return prices[0] if prices else 0

        multiplier = 2 / (period + 1)
        ema = sum(prices[-period:]) / period  # Start with SMA

        for price in reversed(prices[:-period]):
            ema = (price * multiplier) + (ema * (1 - multiplier))

        return ema

    def collect_all(self, symbols: List[str]) -> Dict:
        """Collect data for all symbols."""
        results = {
            'symbols_processed': 0,
            'data_points_collected': 0,
            'errors': [],
        }

        for symbol in symbols:
            try:
                data = self.collect_stock_data(symbol)
                if 'error' not in data:
                    results['symbols_processed'] += 1
                    results['data_points_collected'] += len(data.get('fundamentals', {}))
                else:
                    results['errors'].append(f"{symbol}: {data.get('error')}")
            except Exception as e:
                results['errors'].append(f"{symbol}: {str(e)}")

        return results

    def get_stock_data(self, symbol: str) -> Optional[Dict]:
        """Get cached data for a symbol."""
        return self.data.get('stocks', {}).get(symbol.upper())

    def get_all_data(self) -> Dict:
        """Get all cached data."""
        return self.data

    def get_signals(self, symbol: str) -> Dict:
        """Generate trading signals based on collected data."""
        stock_data = self.get_stock_data(symbol)
        if not stock_data:
            return {'error': f'No data collected for {symbol}'}

        tech = stock_data.get('technical', {})
        fund = stock_data.get('fundamentals', {})
        sent = stock_data.get('sentiment', {})

        signals = {
            'symbol': symbol.upper(),
            'signals': [],
            'overall': 'NEUTRAL',
            'score': 0,
        }

        score = 0

        # RSI signals
        rsi = tech.get('rsi')
        if rsi:
            if rsi < 30:
                signals['signals'].append({'indicator': 'RSI', 'signal': 'OVERSOLD', 'value': rsi})
                score += 2
            elif rsi > 70:
                signals['signals'].append({'indicator': 'RSI', 'signal': 'OVERBOUGHT', 'value': rsi})
                score -= 2
            else:
                signals['signals'].append({'indicator': 'RSI', 'signal': 'NEUTRAL', 'value': rsi})

        # MACD signals
        macd = tech.get('macd_signal')
        if macd:
            if macd == 'bullish':
                signals['signals'].append({'indicator': 'MACD', 'signal': 'BULLISH'})
                score += 1
            else:
                signals['signals'].append({'indicator': 'MACD', 'signal': 'BEARISH'})
                score -= 1

        # Moving average signals
        price_vs_50 = tech.get('price_vs_sma50')
        if price_vs_50 is not None:
            if price_vs_50 > 5:
                signals['signals'].append({'indicator': '50 SMA', 'signal': 'ABOVE', 'value': f'{price_vs_50:.1f}%'})
                score += 1
            elif price_vs_50 < -5:
                signals['signals'].append({'indicator': '50 SMA', 'signal': 'BELOW', 'value': f'{price_vs_50:.1f}%'})
                score -= 1

        # Valuation signals
        pe = fund.get('pe_ratio')
        if pe:
            if pe < 15:
                signals['signals'].append({'indicator': 'P/E', 'signal': 'UNDERVALUED', 'value': pe})
                score += 1
            elif pe > 30:
                signals['signals'].append({'indicator': 'P/E', 'signal': 'EXPENSIVE', 'value': pe})
                score -= 1

        # Sentiment signals
        sent_score = sent.get('average_score', 0)
        if sent_score > 0.1:
            signals['signals'].append({'indicator': 'Sentiment', 'signal': 'BULLISH', 'value': sent_score})
            score += 1
        elif sent_score < -0.1:
            signals['signals'].append({'indicator': 'Sentiment', 'signal': 'BEARISH', 'value': sent_score})
            score -= 1

        signals['score'] = score
        if score >= 3:
            signals['overall'] = 'STRONG BUY'
        elif score >= 1:
            signals['overall'] = 'BUY'
        elif score <= -3:
            signals['overall'] = 'STRONG SELL'
        elif score <= -1:
            signals['overall'] = 'SELL'
        else:
            signals['overall'] = 'NEUTRAL'

        return signals

    def get_collection_stats(self) -> Dict:
        """Get data collection statistics."""
        stocks = self.data.get('stocks', {})
        return {
            'total_symbols': len(stocks),
            'symbols': list(stocks.keys()),
            'last_collection': self.data.get('last_collection'),
            'api_requests_this_session': self.request_count,
        }


# Global instance
data_collector = DataCollector()
