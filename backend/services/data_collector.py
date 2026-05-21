"""
Data Collector Agent
Scrapes the internet for financial data, news, and sentiment to improve predictions.
Sources: Yahoo Finance, Financial news, SEC filings, earnings data
"""

import yfinance as yf
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

DATA_FILE = os.path.join(os.path.dirname(__file__), '..', '..', 'collected_data.json')
LEARNING_FILE = os.path.join(os.path.dirname(__file__), '..', '..', 'LEARNING_LOG.md')

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
}


class DataCollector:
    """
    Collects financial data from multiple sources:
    - Yahoo Finance (fundamentals, news, recommendations)
    - Earnings calendars
    - Insider trading
    - Technical indicators
    """

    def __init__(self):
        self.data = self._load_data()

    def _load_data(self) -> Dict:
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {
            'stocks': {},
            'news': [],
            'insider_trades': [],
            'earnings': [],
            'sentiment_scores': {},
            'collection_history': [],
            'last_collection': None,
        }

    def _save_data(self):
        with open(DATA_FILE, 'w') as f:
            json.dump(self.data, f, indent=2, default=str)

    def _log(self, message: str):
        with open(LEARNING_FILE, 'a') as f:
            f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M')} - {message}\n")

    def collect_all(self, symbols: List[str]) -> Dict:
        """Collect all available data for given symbols."""
        self._log(f"Starting data collection for {len(symbols)} symbols")

        results = {
            'symbols_processed': 0,
            'data_points_collected': 0,
            'errors': [],
        }

        # Collect data for each symbol in parallel
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {
                executor.submit(self.collect_stock_data, symbol): symbol
                for symbol in symbols
            }

            for future in as_completed(futures):
                symbol = futures[future]
                try:
                    data = future.result()
                    if data and 'error' not in data:
                        self.data['stocks'][symbol] = data
                        results['symbols_processed'] += 1
                        results['data_points_collected'] += self._count_data_points(data)
                except Exception as e:
                    results['errors'].append(f"{symbol}: {str(e)}")

        self.data['last_collection'] = datetime.now().isoformat()
        self.data['collection_history'].append({
            'timestamp': datetime.now().isoformat(),
            'symbols': len(symbols),
            'data_points': results['data_points_collected'],
        })

        # Keep only last 50 collection records
        self.data['collection_history'] = self.data['collection_history'][-50:]

        self._save_data()
        self._log(f"Collection complete: {results['symbols_processed']} symbols, {results['data_points_collected']} data points")

        return results

    def collect_stock_data(self, symbol: str) -> Dict:
        """Collect comprehensive data for a single stock."""
        ticker = yf.Ticker(symbol)

        data = {
            'symbol': symbol.upper(),
            'collected_at': datetime.now().isoformat(),
            'fundamentals': {},
            'recommendations': [],
            'news': [],
            'institutional_holders': [],
            'insider_transactions': [],
            'earnings_history': [],
            'technical': {},
            'sentiment': {},
        }

        try:
            # Basic info and fundamentals
            info = ticker.info
            data['fundamentals'] = self._extract_fundamentals(info)

            # Analyst recommendations
            try:
                recs = ticker.recommendations
                if recs is not None and not recs.empty:
                    recent_recs = recs.tail(10).to_dict('records')
                    data['recommendations'] = [
                        {k: str(v) for k, v in rec.items()}
                        for rec in recent_recs
                    ]
            except:
                pass

            # News
            try:
                news = ticker.news
                if news:
                    data['news'] = [
                        {
                            'title': n.get('title', ''),
                            'publisher': n.get('publisher', ''),
                            'link': n.get('link', ''),
                            'published': n.get('providerPublishTime', 0),
                        }
                        for n in news[:10]
                    ]
            except:
                pass

            # Institutional holders
            try:
                holders = ticker.institutional_holders
                if holders is not None and not holders.empty:
                    data['institutional_holders'] = holders.head(10).to_dict('records')
            except:
                pass

            # Insider transactions
            try:
                insider = ticker.insider_transactions
                if insider is not None and not insider.empty:
                    data['insider_transactions'] = insider.head(20).to_dict('records')
            except:
                pass

            # Earnings history
            try:
                earnings = ticker.earnings_history
                if earnings is not None and not earnings.empty:
                    data['earnings_history'] = earnings.to_dict('records')
            except:
                pass

            # Technical data
            data['technical'] = self._calculate_technicals(ticker)

            # Sentiment analysis from news
            data['sentiment'] = self._analyze_sentiment(data['news'])

            return data

        except Exception as e:
            return {'symbol': symbol, 'error': str(e)}

    def _extract_fundamentals(self, info: Dict) -> Dict:
        """Extract key fundamental metrics."""
        metrics = [
            'marketCap', 'enterpriseValue', 'trailingPE', 'forwardPE',
            'pegRatio', 'priceToBook', 'priceToSalesTrailing12Months',
            'enterpriseToRevenue', 'enterpriseToEbitda',
            'profitMargins', 'grossMargins', 'operatingMargins', 'ebitdaMargins',
            'returnOnAssets', 'returnOnEquity',
            'revenueGrowth', 'earningsGrowth', 'revenuePerShare', 'earningsQuarterlyGrowth',
            'totalRevenue', 'grossProfits', 'ebitda', 'netIncomeToCommon',
            'totalCash', 'totalDebt', 'debtToEquity', 'currentRatio', 'quickRatio',
            'freeCashflow', 'operatingCashflow',
            'beta', 'fiftyTwoWeekHigh', 'fiftyTwoWeekLow',
            'fiftyDayAverage', 'twoHundredDayAverage',
            'dividendRate', 'dividendYield', 'payoutRatio',
            'targetMeanPrice', 'targetHighPrice', 'targetLowPrice',
            'recommendationKey', 'recommendationMean', 'numberOfAnalystOpinions',
            'shortRatio', 'shortPercentOfFloat',
            'heldPercentInsiders', 'heldPercentInstitutions',
        ]

        return {m: info.get(m) for m in metrics if info.get(m) is not None}

    def _calculate_technicals(self, ticker) -> Dict:
        """Calculate technical indicators."""
        technicals = {}

        try:
            # Get historical data
            hist = ticker.history(period="6mo")
            if hist.empty:
                return technicals

            close = hist['Close']
            volume = hist['Volume']

            # Moving averages
            technicals['sma_20'] = round(close.tail(20).mean(), 2)
            technicals['sma_50'] = round(close.tail(50).mean(), 2)
            technicals['sma_200'] = round(close.mean(), 2) if len(close) >= 200 else None

            # EMA
            technicals['ema_12'] = round(close.ewm(span=12).mean().iloc[-1], 2)
            technicals['ema_26'] = round(close.ewm(span=26).mean().iloc[-1], 2)

            # MACD
            macd = close.ewm(span=12).mean() - close.ewm(span=26).mean()
            signal = macd.ewm(span=9).mean()
            technicals['macd'] = round(macd.iloc[-1], 2)
            technicals['macd_signal'] = round(signal.iloc[-1], 2)
            technicals['macd_histogram'] = round(macd.iloc[-1] - signal.iloc[-1], 2)

            # RSI
            delta = close.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            technicals['rsi_14'] = round(rsi.iloc[-1], 2) if not rsi.empty else None

            # Bollinger Bands
            sma20 = close.rolling(window=20).mean()
            std20 = close.rolling(window=20).std()
            technicals['bb_upper'] = round((sma20 + (std20 * 2)).iloc[-1], 2)
            technicals['bb_middle'] = round(sma20.iloc[-1], 2)
            technicals['bb_lower'] = round((sma20 - (std20 * 2)).iloc[-1], 2)

            # Volume analysis
            technicals['volume_avg_20'] = int(volume.tail(20).mean())
            technicals['volume_ratio'] = round(volume.iloc[-1] / volume.tail(20).mean(), 2)

            # Price momentum
            technicals['price_change_1m'] = round((close.iloc[-1] / close.iloc[-22] - 1) * 100, 2) if len(close) >= 22 else None
            technicals['price_change_3m'] = round((close.iloc[-1] / close.iloc[-66] - 1) * 100, 2) if len(close) >= 66 else None

            # Trend signals
            current_price = close.iloc[-1]
            technicals['above_sma_20'] = current_price > technicals.get('sma_20', 0)
            technicals['above_sma_50'] = current_price > technicals.get('sma_50', 0)
            technicals['golden_cross'] = technicals.get('sma_50', 0) > technicals.get('sma_200', 0) if technicals.get('sma_200') else None
            technicals['macd_bullish'] = technicals.get('macd', 0) > technicals.get('macd_signal', 0)
            technicals['rsi_oversold'] = technicals.get('rsi_14', 50) < 30
            technicals['rsi_overbought'] = technicals.get('rsi_14', 50) > 70

        except Exception as e:
            technicals['error'] = str(e)

        return technicals

    def _analyze_sentiment(self, news: List[Dict]) -> Dict:
        """Simple sentiment analysis from news headlines."""
        if not news:
            return {'score': 0, 'positive': 0, 'negative': 0, 'neutral': 0}

        # Simple keyword-based sentiment
        positive_words = [
            'surge', 'soar', 'jump', 'gain', 'rise', 'climb', 'rally', 'up',
            'growth', 'profit', 'beat', 'exceed', 'strong', 'bullish', 'buy',
            'upgrade', 'record', 'high', 'boost', 'optimistic', 'positive'
        ]
        negative_words = [
            'fall', 'drop', 'plunge', 'decline', 'sink', 'crash', 'down',
            'loss', 'miss', 'weak', 'bearish', 'sell', 'downgrade', 'low',
            'cut', 'concern', 'risk', 'warning', 'pessimistic', 'negative'
        ]

        positive = 0
        negative = 0
        neutral = 0

        for article in news:
            title = article.get('title', '').lower()

            pos_count = sum(1 for w in positive_words if w in title)
            neg_count = sum(1 for w in negative_words if w in title)

            if pos_count > neg_count:
                positive += 1
            elif neg_count > pos_count:
                negative += 1
            else:
                neutral += 1

        total = positive + negative + neutral
        score = ((positive - negative) / total * 100) if total > 0 else 0

        return {
            'score': round(score, 2),
            'positive': positive,
            'negative': negative,
            'neutral': neutral,
            'total_articles': total,
        }

    def _count_data_points(self, data: Dict) -> int:
        """Count total data points collected."""
        count = 0
        count += len(data.get('fundamentals', {}))
        count += len(data.get('recommendations', []))
        count += len(data.get('news', []))
        count += len(data.get('institutional_holders', []))
        count += len(data.get('insider_transactions', []))
        count += len(data.get('earnings_history', []))
        count += len(data.get('technical', {}))
        return count

    def get_stock_data(self, symbol: str) -> Optional[Dict]:
        """Get cached data for a symbol."""
        return self.data['stocks'].get(symbol.upper())

    def get_all_data(self) -> Dict:
        """Get all collected data."""
        return self.data

    def get_collection_stats(self) -> Dict:
        """Get collection statistics."""
        return {
            'total_symbols': len(self.data['stocks']),
            'last_collection': self.data['last_collection'],
            'collection_history': self.data['collection_history'][-10:],
            'total_data_points': sum(
                self._count_data_points(d)
                for d in self.data['stocks'].values()
                if isinstance(d, dict) and 'error' not in d
            ),
        }

    def get_signals(self, symbol: str) -> Dict:
        """Get trading signals for a symbol based on collected data."""
        data = self.data['stocks'].get(symbol.upper())
        if not data:
            return {'error': 'No data collected for this symbol'}

        signals = {
            'symbol': symbol.upper(),
            'timestamp': datetime.now().isoformat(),
            'bullish_signals': [],
            'bearish_signals': [],
            'neutral_signals': [],
            'overall': 'NEUTRAL',
        }

        tech = data.get('technical', {})
        fund = data.get('fundamentals', {})
        sent = data.get('sentiment', {})

        # Technical signals
        if tech.get('above_sma_50'):
            signals['bullish_signals'].append('Price above 50-day SMA')
        else:
            signals['bearish_signals'].append('Price below 50-day SMA')

        if tech.get('golden_cross'):
            signals['bullish_signals'].append('Golden cross (50MA > 200MA)')
        elif tech.get('golden_cross') is False:
            signals['bearish_signals'].append('Death cross (50MA < 200MA)')

        if tech.get('macd_bullish'):
            signals['bullish_signals'].append('MACD bullish crossover')
        else:
            signals['bearish_signals'].append('MACD bearish')

        if tech.get('rsi_oversold'):
            signals['bullish_signals'].append('RSI oversold (potential bounce)')
        elif tech.get('rsi_overbought'):
            signals['bearish_signals'].append('RSI overbought (potential pullback)')
        else:
            signals['neutral_signals'].append('RSI neutral')

        # Fundamental signals
        pe = fund.get('trailingPE')
        if pe:
            if pe < 15:
                signals['bullish_signals'].append(f'Low P/E ratio ({pe:.1f})')
            elif pe > 30:
                signals['bearish_signals'].append(f'High P/E ratio ({pe:.1f})')

        roe = fund.get('returnOnEquity')
        if roe and roe > 0.15:
            signals['bullish_signals'].append(f'Strong ROE ({roe*100:.1f}%)')
        elif roe and roe < 0.05:
            signals['bearish_signals'].append(f'Weak ROE ({roe*100:.1f}%)')

        rev_growth = fund.get('revenueGrowth')
        if rev_growth and rev_growth > 0.10:
            signals['bullish_signals'].append(f'Strong revenue growth ({rev_growth*100:.1f}%)')
        elif rev_growth and rev_growth < 0:
            signals['bearish_signals'].append(f'Revenue declining ({rev_growth*100:.1f}%)')

        # Sentiment signals
        sent_score = sent.get('score', 0)
        if sent_score > 30:
            signals['bullish_signals'].append(f'Positive news sentiment ({sent_score:.0f})')
        elif sent_score < -30:
            signals['bearish_signals'].append(f'Negative news sentiment ({sent_score:.0f})')

        # Analyst signals
        rec = fund.get('recommendationKey')
        if rec:
            if 'buy' in rec.lower():
                signals['bullish_signals'].append(f'Analyst rating: {rec}')
            elif 'sell' in rec.lower():
                signals['bearish_signals'].append(f'Analyst rating: {rec}')

        # Calculate overall signal
        bull_count = len(signals['bullish_signals'])
        bear_count = len(signals['bearish_signals'])

        if bull_count >= bear_count + 3:
            signals['overall'] = 'STRONG BUY'
        elif bull_count >= bear_count + 1:
            signals['overall'] = 'BUY'
        elif bear_count >= bull_count + 3:
            signals['overall'] = 'STRONG SELL'
        elif bear_count >= bull_count + 1:
            signals['overall'] = 'SELL'
        else:
            signals['overall'] = 'HOLD'

        signals['bull_count'] = bull_count
        signals['bear_count'] = bear_count

        return signals


# Global instance
data_collector = DataCollector()
