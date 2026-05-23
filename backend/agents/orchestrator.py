"""
Orchestrator Agent
Central coordinator that manages all other agents.
Acts as the "CEO" - makes final decisions and routes messages.
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional
from collections import defaultdict
import json
import os

from .base import BaseAgent, AgentRole, Message, MessageType, Memory


class Orchestrator:
    """
    Central orchestrator that coordinates all agents.

    Responsibilities:
    - Route messages between agents
    - Make final trading decisions
    - Monitor agent health
    - Aggregate reports
    - Trigger learning cycles
    """

    def __init__(self):
        self.agents: Dict[AgentRole, BaseAgent] = {}
        self.message_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self.message_log: List[Dict] = []
        self.running = False
        self.memory = Memory("orchestrator")

        # Decision state
        self.pending_signals: List[Dict] = []
        self.active_positions: Dict[str, Dict] = {}
        self.daily_stats = defaultdict(lambda: {"signals": 0, "trades": 0, "pnl": 0})

        # Load persisted state
        self.state = self.memory.load_state() or {
            "total_trades": 0,
            "total_pnl": 0,
            "win_rate": 0,
            "active_since": datetime.now().isoformat(),
        }

    def register_agent(self, agent: BaseAgent):
        """Register an agent with the orchestrator."""
        self.agents[agent.role] = agent
        agent.orchestrator = self
        print(f"[Orchestrator] Registered agent: {agent.name}")

    def unregister_agent(self, role: AgentRole):
        """Unregister an agent."""
        if role in self.agents:
            del self.agents[role]

    async def route_message(self, message: Message):
        """Route a message to its recipient."""
        # Log the message
        self.message_log.append(message.to_dict())

        # Priority queue: (negative priority for max-heap behavior, message)
        await self.message_queue.put((-message.priority, message))

    async def process_messages(self):
        """Process all queued messages."""
        while not self.message_queue.empty():
            _, message = await self.message_queue.get()

            # Handle messages directed to orchestrator
            if message.recipient == AgentRole.ORCHESTRATOR:
                await self._handle_message(message)
            else:
                # Forward to appropriate agent
                if message.recipient in self.agents:
                    await self.agents[message.recipient].receive(message)
                else:
                    print(f"[Orchestrator] No agent for role: {message.recipient}")

    async def _handle_message(self, message: Message):
        """Handle messages sent to orchestrator."""

        if message.msg_type == MessageType.SIGNAL:
            # Trading signal from scanner/technical
            await self._process_signal(message)

        elif message.msg_type == MessageType.REPORT:
            # Status report from agent
            await self._process_report(message)

        elif message.msg_type == MessageType.ALERT:
            # Urgent alert
            await self._process_alert(message)

        elif message.msg_type == MessageType.LEARNING:
            # Learning data
            await self._process_learning(message)

    async def _process_signal(self, message: Message):
        """Process trading signal - make final decision."""
        signal = message.payload
        symbol = signal.get("symbol")
        action = signal.get("action")
        confidence = signal.get("confidence", 0.5)

        print(f"[Orchestrator] Signal received: {action} {symbol} (confidence: {confidence})")

        # Add to pending signals
        self.pending_signals.append({
            "timestamp": datetime.now().isoformat(),
            "signal": signal,
            "source": message.sender.value,
        })

        # Request risk assessment
        if AgentRole.RISK in self.agents:
            await self.agents[AgentRole.RISK].receive(Message(
                id=f"risk_check_{datetime.now().timestamp()}",
                sender=AgentRole.ORCHESTRATOR,
                recipient=AgentRole.RISK,
                msg_type=MessageType.REQUEST,
                payload={"action": "assess", "signal": signal},
                priority=8,
            ))

        # If confidence is high and we have execution agent, proceed
        if confidence >= 0.7 and AgentRole.EXECUTION in self.agents:
            await self._execute_signal(signal)

    async def _execute_signal(self, signal: Dict):
        """Send signal to execution agent."""
        await self.agents[AgentRole.EXECUTION].receive(Message(
            id=f"exec_{datetime.now().timestamp()}",
            sender=AgentRole.ORCHESTRATOR,
            recipient=AgentRole.EXECUTION,
            msg_type=MessageType.REQUEST,
            payload={"action": "execute", "signal": signal},
            priority=9,
        ))

    async def _process_report(self, message: Message):
        """Process status report from agent."""
        report = message.payload
        agent_name = message.sender.value

        # Log report
        print(f"[Orchestrator] Report from {agent_name}: {report.get('summary', 'No summary')}")

        # Update daily stats
        if "trades" in report:
            self.daily_stats[datetime.now().date().isoformat()]["trades"] += report["trades"]
        if "pnl" in report:
            self.daily_stats[datetime.now().date().isoformat()]["pnl"] += report["pnl"]

    async def _process_alert(self, message: Message):
        """Process urgent alert."""
        alert = message.payload
        print(f"[Orchestrator] ALERT from {message.sender.value}: {alert}")

        # If it's a risk alert, potentially halt trading
        if message.sender == AgentRole.RISK:
            if alert.get("level") == "critical":
                await self._halt_trading(alert.get("reason"))

    async def _process_learning(self, message: Message):
        """Process learning data from agents."""
        learning = message.payload

        # Store in orchestrator memory
        self.memory.add_pattern({
            "source": message.sender.value,
            "pattern": learning,
        })

        # Distribute to learning agent if present
        if AgentRole.LEARNING in self.agents:
            await self.agents[AgentRole.LEARNING].receive(message)

    async def _halt_trading(self, reason: str):
        """Emergency halt all trading."""
        print(f"[Orchestrator] HALTING TRADING: {reason}")

        # Notify all agents
        for role, agent in self.agents.items():
            await agent.receive(Message(
                id=f"halt_{datetime.now().timestamp()}",
                sender=AgentRole.ORCHESTRATOR,
                recipient=role,
                msg_type=MessageType.ALERT,
                payload={"action": "halt", "reason": reason},
                priority=10,
            ))

    async def run(self, interval_seconds: float = 0.5):
        """Main orchestrator loop."""
        self.running = True
        print("[Orchestrator] Started")

        while self.running:
            try:
                # Process message queue
                await self.process_messages()

                # Periodic health check
                if datetime.now().second % 30 == 0:
                    await self._health_check()

                await asyncio.sleep(interval_seconds)

            except Exception as e:
                print(f"[Orchestrator] Error: {e}")
                self.memory.record_mistake(
                    context={"state": "running"},
                    mistake=str(e),
                    correction="Orchestrator recovered"
                )
                await asyncio.sleep(1)

        print("[Orchestrator] Stopped")

    async def _health_check(self):
        """Check health of all agents."""
        for role, agent in self.agents.items():
            status = agent.get_status()
            if status["error_count"] > 10:
                print(f"[Orchestrator] Warning: {role.value} has {status['error_count']} errors")

    def stop(self):
        """Stop orchestrator and all agents."""
        self.running = False

        # Stop all agents
        for agent in self.agents.values():
            agent.stop()

        # Save state
        self.state["stopped_at"] = datetime.now().isoformat()
        self.memory.save_state(self.state)

    def get_status(self) -> Dict:
        """Get orchestrator and all agents status."""
        return {
            "orchestrator": {
                "running": self.running,
                "pending_signals": len(self.pending_signals),
                "message_queue_size": self.message_queue.qsize(),
                "total_messages": len(self.message_log),
            },
            "agents": {
                role.value: agent.get_status()
                for role, agent in self.agents.items()
            },
            "daily_stats": dict(self.daily_stats),
            "state": self.state,
        }

    def get_message_log(self, limit: int = 50) -> List[Dict]:
        """Get recent message log."""
        return self.message_log[-limit:]


class TradingSystem:
    """
    Complete trading system that manages the orchestrator and all agents.
    Entry point for starting/stopping the agentic trading environment.
    """

    def __init__(self):
        self.orchestrator = Orchestrator()
        self.tasks: List[asyncio.Task] = []

    def add_agent(self, agent: BaseAgent):
        """Add an agent to the system."""
        self.orchestrator.register_agent(agent)

    async def start(self):
        """Start the trading system."""
        print("=" * 50)
        print("AGENTIC TRADING SYSTEM STARTING")
        print("=" * 50)

        # Start orchestrator
        orchestrator_task = asyncio.create_task(self.orchestrator.run())
        self.tasks.append(orchestrator_task)

        # Start all agents
        for agent in self.orchestrator.agents.values():
            task = asyncio.create_task(agent.run())
            self.tasks.append(task)

        print(f"Started {len(self.orchestrator.agents)} agents")

        # Wait for all tasks
        await asyncio.gather(*self.tasks, return_exceptions=True)

    def stop(self):
        """Stop the trading system."""
        print("Stopping trading system...")
        self.orchestrator.stop()

        for task in self.tasks:
            task.cancel()

    def get_status(self) -> Dict:
        """Get system status."""
        return self.orchestrator.get_status()
