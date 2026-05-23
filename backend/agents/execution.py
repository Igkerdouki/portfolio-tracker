"""
Execution Agent
Handles order execution via brokers (IBKR, etc.)
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional

from .base import BaseAgent, AgentRole, Message, MessageType


class ExecutionAgent(BaseAgent):
    """
    Execution agent that places and manages orders.

    Capabilities:
    - Execute trades via IBKR
    - Manage order lifecycle
    - Track fills and slippage
    - Report execution quality
    """

    def __init__(self, orchestrator=None, ibkr_service=None):
        super().__init__(AgentRole.EXECUTION, orchestrator)

        self.ibkr = ibkr_service
        self.pending_orders: List[Dict] = []
        self.executed_orders: List[Dict] = []
        self.failed_orders: List[Dict] = []

        # Execution settings
        self.settings = self.state.get("settings", {
            "max_position_size": 1000,  # USD
            "max_daily_trades": 10,
            "slippage_tolerance": 0.01,  # 1%
            "require_confirmation": True,
        })

        self.daily_trades = 0
        self.daily_volume = 0

    async def process(self) -> Optional[Message]:
        """Check pending orders and report status."""

        # Reset daily counters at midnight
        if datetime.now().hour == 0 and datetime.now().minute == 0:
            self.daily_trades = 0
            self.daily_volume = 0

        # Check if we have pending orders to process
        if self.pending_orders:
            order = self.pending_orders[0]

            if self._can_execute():
                result = await self._execute_order(order)
                self.pending_orders.pop(0)

                if result.get("success"):
                    self.executed_orders.append(result)
                    self.successful_actions += 1

                    # Report to journal
                    return Message(
                        id=f"exec_report_{datetime.now().timestamp()}",
                        sender=self.role,
                        recipient=AgentRole.JOURNAL,
                        msg_type=MessageType.REPORT,
                        payload={"type": "execution", "order": result},
                    )
                else:
                    self.failed_orders.append(result)
                    self.memory.record_mistake(
                        context={"order": order},
                        mistake=result.get("error", "Unknown error"),
                        correction="Order failed, logged for review"
                    )

        return None

    def _can_execute(self) -> bool:
        """Check if we can execute more trades."""
        if self.daily_trades >= self.settings["max_daily_trades"]:
            return False

        if not self.ibkr or not self.ibkr.is_connected():
            return False

        return True

    async def _execute_order(self, order: Dict) -> Dict:
        """Execute a single order."""
        symbol = order.get("symbol")
        action = order.get("action")  # BUY or SELL
        quantity = order.get("quantity", 1)
        order_type = order.get("order_type", "MARKET")

        self.actions_taken += 1

        result = {
            "symbol": symbol,
            "action": action,
            "quantity": quantity,
            "order_type": order_type,
            "requested_at": datetime.now().isoformat(),
            "success": False,
        }

        try:
            if not self.ibkr:
                result["error"] = "No broker connection"
                return result

            # Place order via IBKR
            # This is a placeholder - actual implementation depends on ib_insync
            if order_type == "MARKET":
                # Market order
                pass
            elif order_type == "LIMIT":
                limit_price = order.get("limit_price")
                pass

            # Simulate execution for now
            result["success"] = True
            result["fill_price"] = order.get("price", 0)
            result["fill_time"] = datetime.now().isoformat()
            result["commission"] = 1.00  # Placeholder

            self.daily_trades += 1
            self.daily_volume += quantity * result.get("fill_price", 0)

        except Exception as e:
            result["error"] = str(e)

        return result

    async def handle_message(self, message: Message) -> Optional[Message]:
        """Handle incoming messages."""

        if message.msg_type == MessageType.REQUEST:
            action = message.payload.get("action")

            if action == "execute":
                signal = message.payload.get("signal", {})

                # Create order from signal
                order = {
                    "symbol": signal.get("symbol"),
                    "action": signal.get("signal"),  # BUY/SELL
                    "quantity": self._calculate_position_size(signal),
                    "order_type": "MARKET",
                    "price": signal.get("price"),
                    "signal_confidence": signal.get("confidence"),
                    "created_at": datetime.now().isoformat(),
                }

                # Add to pending queue
                self.pending_orders.append(order)

                return Message(
                    id=f"exec_ack_{datetime.now().timestamp()}",
                    sender=self.role,
                    recipient=message.sender,
                    msg_type=MessageType.RESPONSE,
                    payload={"acknowledged": True, "order_queued": order},
                )

            elif action == "cancel":
                order_id = message.payload.get("order_id")
                # Cancel logic here
                pass

            elif action == "status":
                return Message(
                    id=f"status_{datetime.now().timestamp()}",
                    sender=self.role,
                    recipient=message.sender,
                    msg_type=MessageType.RESPONSE,
                    payload=self.get_status(),
                )

        elif message.msg_type == MessageType.ALERT:
            if message.payload.get("action") == "halt":
                # Cancel all pending orders
                self.pending_orders.clear()
                self.running = False

        return None

    def _calculate_position_size(self, signal: Dict) -> int:
        """Calculate position size based on signal and settings."""
        max_size = self.settings["max_position_size"]
        price = signal.get("price", 100)
        confidence = signal.get("confidence", 0.5)

        # Scale by confidence
        position_value = max_size * confidence
        shares = int(position_value / price)

        return max(1, shares)

    def get_status(self) -> Dict:
        status = super().get_status()
        status.update({
            "pending_orders": len(self.pending_orders),
            "executed_today": self.daily_trades,
            "daily_volume": self.daily_volume,
            "max_daily_trades": self.settings["max_daily_trades"],
            "broker_connected": self.ibkr.is_connected() if self.ibkr else False,
        })
        return status
