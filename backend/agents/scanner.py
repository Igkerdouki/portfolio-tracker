"""
Market Scanner Agent
Scans markets for trading opportunities based on technical setups.
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional
import os

from .base import BaseAgent, AgentRole, Message, MessageType

# Try to import tradingview-ta for live scanning
try:
    from tradingview_ta import TA_Handler, Interval
    HAS_TRADINGVIEW = True
except ImportError:
    HAS_TRADINGVIEW = False


class ScannerAgent(BaseAgent):
    """
    Market scanner that finds trading opportunities.

    Capabilities:
    - Scan watchlist for setups
    - Use TradingView technical analysis
    - Rank opportunities by strength
    - Report to orchestrator
    """

    def __init__(self, orchestrator=None):
        super().__init__(AgentRole.SCANNER, orchestrator)

        # Default watchlist - can be expanded
        self.watchlist = self.state.get("watchlist", [
            "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA",
            "META", "TSLA", "AMD", "NFLX", "SPY"
        ])

        # Scan configuration
        self.scan_interval = self.state.get("scan_interval", 60)  # seconds
        self.last_scan = None
        self.signals_found = []

        # Technical criteria for signals
        self.criteria = {
            "rsi_oversold": 30,
            "rsi_overbought": 70,
            "macd_threshold": 0,
            "min_volume_ratio": 1.2,  # vs average
        }

    async def process(self) -> Optional[Message]:
        """Main scanning logic."""
        now = datetime.now()

        # Check if it's time to scan
        if self.last_scan:
            elapsed = (now - self.last_scan).total_seconds()
            if elapsed < self.scan_interval:
                return None

        self.last_scan = now
        self.actions_taken += 1

        # Perform scan
        signals = await self._scan_markets()

        if signals:
            self.successful_actions += 1
            self.signals_found.extend(signals)

            # Send signals to orchestrator
            return Message(
                id=f"scan_{now.timestamp()}",
                sender=self.role,
                recipient=AgentRole.ORCHESTRATOR,
                msg_type=MessageType.SIGNAL,
                payload={
                    "signals": signals,
                    "scan_time": now.isoformat(),
                    "watchlist_size": len(self.watchlist),
                },
                priority=7,
            )

        return None

    async def _scan_markets(self) -> List[Dict]:
        """Scan all watchlist symbols for opportunities."""
        signals = []

        for symbol in self.watchlist:
            try:
                analysis = await self._analyze_symbol(symbol)
                if analysis and analysis.get("signal"):
                    signals.append(analysis)
            except Exception as e:
                self.memory.record_mistake(
                    context={"symbol": symbol, "action": "scan"},
                    mistake=str(e),
                    correction="Skipped symbol"
                )

        # Sort by confidence
        signals.sort(key=lambda x: x.get("confidence", 0), reverse=True)

        return signals[:5]  # Top 5 signals

    async def _analyze_symbol(self, symbol: str) -> Optional[Dict]:
        """Analyze a single symbol using TradingView or fallback."""

        if HAS_TRADINGVIEW:
            return await self._analyze_with_tradingview(symbol)
        else:
            return await self._analyze_fallback(symbol)

    async def _analyze_with_tradingview(self, symbol: str) -> Optional[Dict]:
        """Use TradingView technical analysis."""
        try:
            handler = TA_Handler(
                symbol=symbol,
                exchange="NASDAQ",
                screener="america",
                interval=Interval.INTERVAL_1_HOUR,
            )

            analysis = handler.get_analysis()

            # Extract key indicators
            indicators = analysis.indicators
            summary = analysis.summary

            rsi = indicators.get("RSI", 50)
            macd = indicators.get("MACD.macd", 0)
            macd_signal = indicators.get("MACD.signal", 0)
            sma20 = indicators.get("SMA20", 0)
            sma50 = indicators.get("SMA50", 0)
            price = indicators.get("close", 0)
            volume = indicators.get("volume", 0)
            avg_volume = indicators.get("average_volume_10d_calc", 1)

            # Determine signal
            signal = None
            confidence = 0
            reasons = []

            # RSI oversold
            if rsi < self.criteria["rsi_oversold"]:
                signal = "BUY"
                confidence += 0.3
                reasons.append(f"RSI oversold ({rsi:.1f})")

            # RSI overbought
            elif rsi > self.criteria["rsi_overbought"]:
                signal = "SELL"
                confidence += 0.3
                reasons.append(f"RSI overbought ({rsi:.1f})")

            # MACD crossover
            if macd > macd_signal and macd > 0:
                if signal != "SELL":
                    signal = "BUY"
                    confidence += 0.2
                    reasons.append("MACD bullish crossover")
            elif macd < macd_signal and macd < 0:
                if signal != "BUY":
                    signal = "SELL"
                    confidence += 0.2
                    reasons.append("MACD bearish crossover")

            # Golden/Death cross
            if sma20 > sma50 and price > sma20:
                if signal != "SELL":
                    signal = "BUY"
                    confidence += 0.2
                    reasons.append("Price above SMA20 > SMA50")
            elif sma20 < sma50 and price < sma20:
                if signal != "BUY":
                    signal = "SELL"
                    confidence += 0.2
                    reasons.append("Price below SMA20 < SMA50")

            # Volume confirmation
            if avg_volume > 0 and volume / avg_volume > self.criteria["min_volume_ratio"]:
                confidence += 0.1
                reasons.append("High volume confirmation")

            # TradingView recommendation
            tv_rec = summary.get("RECOMMENDATION", "NEUTRAL")
            if tv_rec in ["STRONG_BUY", "BUY"]:
                confidence += 0.2
                reasons.append(f"TradingView: {tv_rec}")
            elif tv_rec in ["STRONG_SELL", "SELL"]:
                confidence += 0.2
                reasons.append(f"TradingView: {tv_rec}")

            if not signal:
                return None

            return {
                "symbol": symbol,
                "signal": signal,
                "confidence": min(confidence, 1.0),
                "price": price,
                "rsi": rsi,
                "macd": macd,
                "reasons": reasons,
                "tv_recommendation": tv_rec,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            return None

    async def _analyze_fallback(self, symbol: str) -> Optional[Dict]:
        """Fallback analysis when TradingView is not available."""
        # This would use Alpha Vantage or other data source
        # For now, return None
        return None

    async def handle_message(self, message: Message) -> Optional[Message]:
        """Handle incoming messages."""

        if message.msg_type == MessageType.REQUEST:
            action = message.payload.get("action")

            if action == "add_watchlist":
                symbols = message.payload.get("symbols", [])
                self.watchlist.extend(symbols)
                self.watchlist = list(set(self.watchlist))
                self.state["watchlist"] = self.watchlist
                self.memory.save_state(self.state)

                return Message(
                    id=f"resp_{datetime.now().timestamp()}",
                    sender=self.role,
                    recipient=message.sender,
                    msg_type=MessageType.RESPONSE,
                    payload={"success": True, "watchlist": self.watchlist},
                )

            elif action == "remove_watchlist":
                symbols = message.payload.get("symbols", [])
                self.watchlist = [s for s in self.watchlist if s not in symbols]
                self.state["watchlist"] = self.watchlist
                self.memory.save_state(self.state)

                return Message(
                    id=f"resp_{datetime.now().timestamp()}",
                    sender=self.role,
                    recipient=message.sender,
                    msg_type=MessageType.RESPONSE,
                    payload={"success": True, "watchlist": self.watchlist},
                )

            elif action == "scan_now":
                # Force immediate scan
                self.last_scan = None

        elif message.msg_type == MessageType.ALERT:
            if message.payload.get("action") == "halt":
                self.running = False

        return None

    def get_status(self) -> Dict:
        status = super().get_status()
        status.update({
            "watchlist": self.watchlist,
            "watchlist_size": len(self.watchlist),
            "last_scan": self.last_scan.isoformat() if self.last_scan else None,
            "signals_found_today": len(self.signals_found),
            "scan_interval": self.scan_interval,
        })
        return status
