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

        # Clear old signals (keep only last 2 hours)
        now = datetime.now()
        self.signals_found = [
            s for s in self.signals_found
            if s.get("timestamp") and
            (now - datetime.fromisoformat(s["timestamp"])).total_seconds() < 7200
        ]

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
            sma200 = indicators.get("SMA200", 0)
            price = indicators.get("close", 0)
            volume = indicators.get("volume", 0)
            avg_volume = indicators.get("average_volume_10d_calc", 1)
            adx = indicators.get("ADX", 0)
            stoch_k = indicators.get("Stoch.K", 50)

            # Determine signal with more granular confidence
            signal = None
            confidence = 0
            reasons = []

            # RSI analysis (more granular)
            if rsi < 20:
                signal = "BUY"
                confidence += 0.35  # Very oversold
                reasons.append(f"RSI extremely oversold ({rsi:.1f})")
            elif rsi < self.criteria["rsi_oversold"]:
                signal = "BUY"
                confidence += 0.25
                reasons.append(f"RSI oversold ({rsi:.1f})")
            elif rsi > 80:
                signal = "SELL"
                confidence += 0.35  # Very overbought
                reasons.append(f"RSI extremely overbought ({rsi:.1f})")
            elif rsi > self.criteria["rsi_overbought"]:
                signal = "SELL"
                confidence += 0.25
                reasons.append(f"RSI overbought ({rsi:.1f})")

            # MACD analysis (with strength)
            macd_diff = abs(macd - macd_signal) if macd_signal else 0
            if macd > macd_signal and macd > 0:
                if signal != "SELL":
                    signal = "BUY"
                    # Stronger signal if MACD difference is significant
                    conf_add = 0.15 + min(0.15, macd_diff * 10)
                    confidence += conf_add
                    reasons.append(f"MACD bullish ({macd:.3f})")
            elif macd < macd_signal and macd < 0:
                if signal != "BUY":
                    signal = "SELL"
                    conf_add = 0.15 + min(0.15, macd_diff * 10)
                    confidence += conf_add
                    reasons.append(f"MACD bearish ({macd:.3f})")

            # Moving average analysis
            if sma20 > 0 and sma50 > 0:
                if sma20 > sma50 and price > sma20:
                    if signal != "SELL":
                        signal = "BUY"
                        # Stronger if price is well above MAs
                        pct_above = (price - sma20) / sma20 * 100
                        conf_add = 0.1 + min(0.1, pct_above / 5)
                        confidence += conf_add
                        reasons.append(f"Above SMA20/50 (+{pct_above:.1f}%)")
                elif sma20 < sma50 and price < sma20:
                    if signal != "BUY":
                        signal = "SELL"
                        pct_below = (sma20 - price) / sma20 * 100
                        conf_add = 0.1 + min(0.1, pct_below / 5)
                        confidence += conf_add
                        reasons.append(f"Below SMA20/50 (-{pct_below:.1f}%)")

            # Volume confirmation (more nuanced)
            if avg_volume > 0:
                vol_ratio = volume / avg_volume
                if vol_ratio > 2.0:
                    confidence += 0.15
                    reasons.append(f"Strong volume ({vol_ratio:.1f}x)")
                elif vol_ratio > self.criteria["min_volume_ratio"]:
                    confidence += 0.08
                    reasons.append(f"Above avg volume ({vol_ratio:.1f}x)")

            # ADX trend strength
            if adx > 25:
                confidence += 0.1
                reasons.append(f"Strong trend (ADX: {adx:.0f})")

            # TradingView recommendation with weight
            tv_rec = summary.get("RECOMMENDATION", "NEUTRAL")
            buy_count = summary.get("BUY", 0)
            sell_count = summary.get("SELL", 0)
            neutral_count = summary.get("NEUTRAL", 0)
            total_signals = buy_count + sell_count + neutral_count

            if tv_rec == "STRONG_BUY":
                confidence += 0.2
                reasons.append(f"TV: STRONG BUY ({buy_count}/{total_signals})")
            elif tv_rec == "BUY":
                confidence += 0.12
                reasons.append(f"TV: BUY ({buy_count}/{total_signals})")
            elif tv_rec == "STRONG_SELL":
                confidence += 0.2
                reasons.append(f"TV: STRONG SELL ({sell_count}/{total_signals})")
            elif tv_rec == "SELL":
                confidence += 0.12
                reasons.append(f"TV: SELL ({sell_count}/{total_signals})")

            if not signal:
                return None

            # Cap confidence at 0.95 (never 100% certain)
            final_confidence = min(confidence, 0.95)

            return {
                "symbol": symbol,
                "signal": signal,
                "action": signal,  # For frontend compatibility
                "confidence": final_confidence,
                "price": price,
                "rsi": rsi,
                "macd": macd,
                "adx": adx,
                "reasons": reasons,
                "tv_recommendation": tv_rec,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            return None

    async def _analyze_fallback(self, symbol: str) -> Optional[Dict]:
        """Fallback analysis using yfinance when TradingView is not available."""
        try:
            import yfinance as yf
            import numpy as np

            # Get recent data
            ticker = yf.Ticker(symbol)
            df = ticker.history(period="3mo")

            if len(df) < 20:
                return None

            close = df['Close']
            volume = df['Volume']
            price = close.iloc[-1]

            # Calculate indicators
            # RSI
            delta = close.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = (100 - (100 / (1 + rs))).iloc[-1]

            # MACD
            ema12 = close.ewm(span=12).mean()
            ema26 = close.ewm(span=26).mean()
            macd = (ema12 - ema26).iloc[-1]
            macd_signal_line = (ema12 - ema26).ewm(span=9).mean().iloc[-1]

            # Moving averages
            sma20 = close.rolling(20).mean().iloc[-1]
            sma50 = close.rolling(50).mean().iloc[-1] if len(close) >= 50 else sma20

            # Volume ratio
            avg_volume = volume.rolling(20).mean().iloc[-1]
            vol_ratio = volume.iloc[-1] / avg_volume if avg_volume > 0 else 1

            # Generate signal
            signal = None
            confidence = 0
            reasons = []

            # RSI analysis
            if rsi < 30:
                signal = "BUY"
                confidence += 0.25
                reasons.append(f"RSI oversold ({rsi:.1f})")
            elif rsi > 70:
                signal = "SELL"
                confidence += 0.25
                reasons.append(f"RSI overbought ({rsi:.1f})")

            # MACD
            if macd > macd_signal_line and macd > 0:
                if signal != "SELL":
                    signal = "BUY"
                    confidence += 0.2
                    reasons.append(f"MACD bullish ({macd:.3f})")
            elif macd < macd_signal_line and macd < 0:
                if signal != "BUY":
                    signal = "SELL"
                    confidence += 0.2
                    reasons.append(f"MACD bearish ({macd:.3f})")

            # Moving averages
            if price > sma20 > sma50:
                if signal != "SELL":
                    signal = "BUY"
                    confidence += 0.15
                    reasons.append("Above SMA20/50")
            elif price < sma20 < sma50:
                if signal != "BUY":
                    signal = "SELL"
                    confidence += 0.15
                    reasons.append("Below SMA20/50")

            # Volume
            if vol_ratio > 1.5:
                confidence += 0.1
                reasons.append(f"High volume ({vol_ratio:.1f}x)")

            if not signal:
                return None

            return {
                "symbol": symbol,
                "signal": signal,
                "action": signal,
                "confidence": min(confidence, 0.95),
                "price": float(price),
                "rsi": float(rsi),
                "macd": float(macd),
                "reasons": reasons,
                "tv_recommendation": "N/A (yfinance)",
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
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
