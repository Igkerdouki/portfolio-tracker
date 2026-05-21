import os
import requests
from datetime import datetime, timedelta
from typing import Dict, Optional
import threading
from dotenv import load_dotenv

load_dotenv()

ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")
ALPHA_VANTAGE_BASE_URL = "https://www.alphavantage.co/query"


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
    """Fetch current price for a symbol using Alpha Vantage."""
    cached = price_cache.get(symbol)
    if cached:
        return cached

    try:
        # Use GLOBAL_QUOTE for current price
        params = {
            "function": "GLOBAL_QUOTE",
            "symbol": symbol,
            "apikey": ALPHA_VANTAGE_API_KEY
        }

        response = requests.get(ALPHA_VANTAGE_BASE_URL, params=params, timeout=10)
        data = response.json()

        # Check for API errors
        if "Error Message" in data:
            print(f"Alpha Vantage error for {symbol}: {data['Error Message']}")
            return None

        if "Note" in data:  # Rate limit message
            print(f"Alpha Vantage rate limit: {data['Note']}")
            return None

        quote = data.get("Global Quote", {})
        if not quote:
            print(f"No quote data for {symbol}")
            return None

        price = float(quote.get("05. price", 0))
        previous_close = float(quote.get("08. previous close", price))
        change = float(quote.get("09. change", 0))
        change_percent = quote.get("10. change percent", "0%").replace("%", "")

        if price == 0:
            return None

        result = {
            "symbol": symbol.upper(),
            "price": round(price, 2),
            "currency": "USD",  # Alpha Vantage returns USD prices
            "change": round(change, 2),
            "change_percent": round(float(change_percent), 2)
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
    """Fetch historical prices for a symbol using Alpha Vantage."""
    try:
        # Map period to outputsize
        outputsize = "compact"  # Last 100 data points
        if period in ["3mo", "6mo", "1y"]:
            outputsize = "full"

        params = {
            "function": "TIME_SERIES_DAILY",
            "symbol": symbol,
            "outputsize": outputsize,
            "apikey": ALPHA_VANTAGE_API_KEY
        }

        response = requests.get(ALPHA_VANTAGE_BASE_URL, params=params, timeout=10)
        data = response.json()

        if "Error Message" in data or "Note" in data:
            return []

        time_series = data.get("Time Series (Daily)", {})

        # Convert to list format
        results = []
        for date_str, values in sorted(time_series.items(), reverse=True)[:30]:  # Last 30 days
            results.append({
                "date": date_str,
                "close": round(float(values["4. close"]), 2),
                "volume": int(float(values["5. volume"]))
            })

        return list(reversed(results))  # Oldest first

    except Exception as e:
        print(f"Error fetching history for {symbol}: {e}")
        return []
