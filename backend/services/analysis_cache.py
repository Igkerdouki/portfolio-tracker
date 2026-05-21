"""Analysis caching service to reduce API calls."""

from datetime import datetime, timedelta
from typing import Dict, Optional
import threading


class AnalysisCache:
    """
    Caches stock analysis results to reduce Alpha Vantage API calls.

    Default TTL is 1 hour - analysis doesn't change that frequently.
    """

    def __init__(self, ttl_minutes: int = 60):
        self.cache: Dict[str, dict] = {}
        self.ttl = timedelta(minutes=ttl_minutes)
        self.lock = threading.Lock()
        self.hits = 0
        self.misses = 0

    def get(self, symbol: str) -> Optional[dict]:
        """Get cached analysis if available and not expired."""
        with self.lock:
            symbol = symbol.upper()
            if symbol in self.cache:
                entry = self.cache[symbol]
                if datetime.now() - entry["cached_at"] < self.ttl:
                    self.hits += 1
                    # Return a copy to prevent mutation
                    return {**entry["data"]}
                # Expired - remove it
                del self.cache[symbol]
            self.misses += 1
        return None

    def set(self, symbol: str, data: dict):
        """Cache analysis result."""
        with self.lock:
            symbol = symbol.upper()
            self.cache[symbol] = {
                "data": data,
                "cached_at": datetime.now()
            }

    def invalidate(self, symbol: str):
        """Remove a specific symbol from cache."""
        with self.lock:
            symbol = symbol.upper()
            if symbol in self.cache:
                del self.cache[symbol]

    def clear(self):
        """Clear all cached data."""
        with self.lock:
            self.cache.clear()
            self.hits = 0
            self.misses = 0

    def get_stats(self) -> dict:
        """Get cache statistics."""
        with self.lock:
            total = self.hits + self.misses
            hit_rate = (self.hits / total * 100) if total > 0 else 0

            return {
                "cached_symbols": list(self.cache.keys()),
                "cache_size": len(self.cache),
                "hits": self.hits,
                "misses": self.misses,
                "hit_rate": f"{hit_rate:.1f}%",
                "ttl_minutes": self.ttl.seconds // 60,
            }

    def cleanup_expired(self):
        """Remove expired entries."""
        with self.lock:
            now = datetime.now()
            expired = [
                symbol for symbol, entry in self.cache.items()
                if now - entry["cached_at"] >= self.ttl
            ]
            for symbol in expired:
                del self.cache[symbol]
            return len(expired)


# Global instance - 1 hour TTL (analysis data doesn't change rapidly)
analysis_cache = AnalysisCache(ttl_minutes=60)
