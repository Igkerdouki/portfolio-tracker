"""
Journal Agent
Logs all trading activity and learns from outcomes.
Creates markdown reports for human review.
"""

import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from .base import BaseAgent, AgentRole, Message, MessageType


class JournalAgent(BaseAgent):
    """
    Trading journal that logs activity and learns from outcomes.

    Capabilities:
    - Log all trades and signals
    - Track performance metrics
    - Generate daily/weekly reports
    - Identify patterns in mistakes
    - Send learnings to other agents
    """

    def __init__(self, orchestrator=None):
        super().__init__(AgentRole.JOURNAL, orchestrator)

        self.journal_dir = os.path.join(os.path.dirname(__file__), "..", "..", "memory", "journal")
        os.makedirs(self.journal_dir, exist_ok=True)

        # Trading log
        self.trades: List[Dict] = self.state.get("trades", [])
        self.signals: List[Dict] = self.state.get("signals", [])

        # Performance tracking
        self.performance = self.state.get("performance", {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "total_pnl": 0,
            "best_trade": None,
            "worst_trade": None,
        })

        # Pattern detection
        self.patterns = self.state.get("patterns", {
            "best_time_to_trade": [],
            "worst_time_to_trade": [],
            "winning_setups": [],
            "losing_setups": [],
        })

    async def process(self) -> Optional[Message]:
        """Periodic analysis and reporting."""
        now = datetime.now()

        # Generate daily report at end of trading day (4 PM)
        if now.hour == 16 and now.minute == 0:
            await self._generate_daily_report()

        # Analyze patterns weekly
        if now.weekday() == 4 and now.hour == 17:  # Friday 5 PM
            patterns = await self._analyze_patterns()

            if patterns:
                # Send learnings to orchestrator for distribution
                return Message(
                    id=f"learning_{now.timestamp()}",
                    sender=self.role,
                    recipient=AgentRole.ORCHESTRATOR,
                    msg_type=MessageType.LEARNING,
                    payload={"patterns": patterns, "week_ending": now.isoformat()},
                )

        return None

    async def handle_message(self, message: Message) -> Optional[Message]:
        """Handle incoming messages."""

        if message.msg_type == MessageType.REPORT:
            report_type = message.payload.get("type")

            if report_type == "execution":
                await self._log_trade(message.payload.get("order", {}))

            elif report_type == "signal":
                await self._log_signal(message.payload)

        elif message.msg_type == MessageType.REQUEST:
            action = message.payload.get("action")

            if action == "get_report":
                period = message.payload.get("period", "daily")
                report = await self._get_report(period)

                return Message(
                    id=f"report_{datetime.now().timestamp()}",
                    sender=self.role,
                    recipient=message.sender,
                    msg_type=MessageType.RESPONSE,
                    payload={"report": report},
                )

            elif action == "get_performance":
                return Message(
                    id=f"perf_{datetime.now().timestamp()}",
                    sender=self.role,
                    recipient=message.sender,
                    msg_type=MessageType.RESPONSE,
                    payload={"performance": self.performance},
                )

        return None

    async def _log_trade(self, trade: Dict):
        """Log a trade."""
        trade["logged_at"] = datetime.now().isoformat()
        self.trades.append(trade)

        # Update performance
        self.performance["total_trades"] += 1

        pnl = trade.get("pnl", 0)
        self.performance["total_pnl"] += pnl

        if pnl > 0:
            self.performance["winning_trades"] += 1
            if not self.performance["best_trade"] or pnl > self.performance["best_trade"]["pnl"]:
                self.performance["best_trade"] = trade
        elif pnl < 0:
            self.performance["losing_trades"] += 1
            if not self.performance["worst_trade"] or pnl < self.performance["worst_trade"]["pnl"]:
                self.performance["worst_trade"] = trade

        # Save state
        self.state["trades"] = self.trades[-1000:]  # Keep last 1000
        self.state["performance"] = self.performance
        self.memory.save_state(self.state)

        # Write to markdown
        await self._write_trade_md(trade)

    async def _log_signal(self, signal: Dict):
        """Log a signal."""
        signal["logged_at"] = datetime.now().isoformat()
        self.signals.append(signal)
        self.state["signals"] = self.signals[-500:]
        self.memory.save_state(self.state)

    async def _write_trade_md(self, trade: Dict):
        """Write trade to markdown file."""
        date_str = datetime.now().strftime("%Y-%m-%d")
        filename = os.path.join(self.journal_dir, f"trades_{date_str}.md")

        with open(filename, 'a') as f:
            f.write(f"\n## Trade - {trade.get('symbol')} {trade.get('action')}\n")
            f.write(f"**Time:** {trade.get('fill_time', 'N/A')}\n")
            f.write(f"**Price:** ${trade.get('fill_price', 0):.2f}\n")
            f.write(f"**Quantity:** {trade.get('quantity', 0)}\n")
            f.write(f"**P&L:** ${trade.get('pnl', 0):.2f}\n")
            f.write(f"**Confidence:** {trade.get('signal_confidence', 0):.1%}\n")
            f.write("---\n")

    async def _generate_daily_report(self):
        """Generate end-of-day report."""
        today = datetime.now().date()
        today_trades = [t for t in self.trades if t.get("logged_at", "").startswith(str(today))]

        if not today_trades:
            return

        total_pnl = sum(t.get("pnl", 0) for t in today_trades)
        winners = len([t for t in today_trades if t.get("pnl", 0) > 0])
        losers = len([t for t in today_trades if t.get("pnl", 0) < 0])

        report = f"""# Daily Trading Report - {today}

## Summary
- **Total Trades:** {len(today_trades)}
- **Winners:** {winners}
- **Losers:** {losers}
- **Win Rate:** {winners/max(1, len(today_trades)):.1%}
- **Total P&L:** ${total_pnl:.2f}

## Trades
"""
        for trade in today_trades:
            emoji = "✅" if trade.get("pnl", 0) > 0 else "❌"
            report += f"- {emoji} {trade.get('symbol')} {trade.get('action')}: ${trade.get('pnl', 0):.2f}\n"

        # Write report
        filename = os.path.join(self.journal_dir, f"report_{today}.md")
        with open(filename, 'w') as f:
            f.write(report)

        # Log learnings from losses
        for trade in today_trades:
            if trade.get("pnl", 0) < 0:
                self.memory.record_mistake(
                    context={"trade": trade},
                    mistake=f"Lost ${abs(trade.get('pnl', 0)):.2f} on {trade.get('symbol')}",
                    correction="Review setup and market conditions"
                )

    async def _analyze_patterns(self) -> Dict:
        """Analyze trading patterns from history."""
        if len(self.trades) < 10:
            return {}

        patterns = {
            "winning_hours": {},
            "losing_hours": {},
            "winning_symbols": {},
            "losing_symbols": {},
        }

        for trade in self.trades:
            try:
                hour = datetime.fromisoformat(trade.get("fill_time", "")).hour
                symbol = trade.get("symbol")
                pnl = trade.get("pnl", 0)

                if pnl > 0:
                    patterns["winning_hours"][hour] = patterns["winning_hours"].get(hour, 0) + 1
                    patterns["winning_symbols"][symbol] = patterns["winning_symbols"].get(symbol, 0) + 1
                else:
                    patterns["losing_hours"][hour] = patterns["losing_hours"].get(hour, 0) + 1
                    patterns["losing_symbols"][symbol] = patterns["losing_symbols"].get(symbol, 0) + 1
            except:
                pass

        # Find best/worst hours
        if patterns["winning_hours"]:
            best_hour = max(patterns["winning_hours"], key=patterns["winning_hours"].get)
            patterns["best_trading_hour"] = best_hour

        if patterns["losing_hours"]:
            worst_hour = max(patterns["losing_hours"], key=patterns["losing_hours"].get)
            patterns["worst_trading_hour"] = worst_hour

        return patterns

    async def _get_report(self, period: str) -> str:
        """Get performance report for period."""
        total = self.performance["total_trades"]
        wins = self.performance["winning_trades"]
        losses = self.performance["losing_trades"]

        return f"""
# Performance Report

## Overall Statistics
- Total Trades: {total}
- Winning Trades: {wins}
- Losing Trades: {losses}
- Win Rate: {wins/max(1,total):.1%}
- Total P&L: ${self.performance['total_pnl']:.2f}

## Best Trade
{self.performance.get('best_trade', 'N/A')}

## Worst Trade
{self.performance.get('worst_trade', 'N/A')}
"""

    def get_status(self) -> Dict:
        status = super().get_status()
        status.update({
            "total_trades_logged": len(self.trades),
            "signals_logged": len(self.signals),
            "performance": self.performance,
        })
        return status
