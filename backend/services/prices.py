import yfinance as yf
from datetime import datetime, timedelta
from typing import Dict, Optional
import threading


class PriceCache:
    def __init__(self, ttl_seconds: int = 60):
        self.cache: Dict[str, dict] = {}
        self.ttl = timedelta(seconds=ttl_seconds)
        self.lock = threading.Lock()

    def get(self, symbol: str) -> Optional[dict]:
        with self.lock:
            if symbol in self.cache:
                entry = self.cache[symbol]
                if datetime.now() - entry["timestamp"] < self.ttl:
                    return entry["data"]
                del self.cache[symbol]
        return None

    def set(self, symbol: str, data: dict):
        with self.lock:
            self.cache[symbol] = {
                "data": data,
                "timestamp": datetime.now()
            }


price_cache = PriceCache(ttl_seconds=60)


def get_current_price(symbol: str) -> Optional[dict]:
    """Fetch current price for a symbol with caching."""
    cached = price_cache.get(symbol)
    if cached:
        return cached

    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info

        # Try different price fields as Yahoo Finance can be inconsistent
        price = info.get("regularMarketPrice") or info.get("currentPrice") or info.get("previousClose")

        if price is None:
            # Try getting from history as fallback
            hist = ticker.history(period="1d")
            if not hist.empty:
                price = hist["Close"].iloc[-1]

        if price is None:
            return None

        previous_close = info.get("previousClose", price)
        change = price - previous_close if previous_close else 0
        change_percent = (change / previous_close * 100) if previous_close else 0

        result = {
            "symbol": symbol.upper(),
            "price": round(price, 2),
            "currency": info.get("currency", "USD"),
            "change": round(change, 2),
            "change_percent": round(change_percent, 2)
        }

        price_cache.set(symbol, result)
        return result

    except Exception as e:
        print(f"Error fetching price for {symbol}: {e}")
        return None


def get_prices_batch(symbols: list[str]) -> Dict[str, dict]:
    """Fetch prices for multiple symbols."""
    results = {}
    for symbol in symbols:
        price_data = get_current_price(symbol)
        if price_data:
            results[symbol.upper()] = price_data
    return results


def get_historical_prices(symbol: str, period: str = "1mo") -> list[dict]:
    """Fetch historical prices for a symbol."""
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period)

        return [
            {
                "date": date.strftime("%Y-%m-%d"),
                "close": round(row["Close"], 2),
                "volume": int(row["Volume"])
            }
            for date, row in hist.iterrows()
        ]
    except Exception as e:
        print(f"Error fetching history for {symbol}: {e}")
        return []
