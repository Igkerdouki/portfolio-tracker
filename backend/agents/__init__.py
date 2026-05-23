"""
Agentic Trading System

A multi-agent system for autonomous trading with:
- Market Scanner: Finds trading opportunities
- Execution Agent: Places and manages orders
- Journal Agent: Logs trades and learns from outcomes
- Orchestrator: Coordinates all agents

Usage:
    from agents import TradingSystem, ScannerAgent, ExecutionAgent, JournalAgent

    system = TradingSystem()
    system.add_agent(ScannerAgent())
    system.add_agent(ExecutionAgent())
    system.add_agent(JournalAgent())

    await system.start()
"""

from .base import BaseAgent, AgentRole, Message, MessageType, Memory
from .orchestrator import Orchestrator, TradingSystem
from .scanner import ScannerAgent
from .execution import ExecutionAgent
from .journal import JournalAgent

__all__ = [
    "BaseAgent",
    "AgentRole",
    "Message",
    "MessageType",
    "Memory",
    "Orchestrator",
    "TradingSystem",
    "ScannerAgent",
    "ExecutionAgent",
    "JournalAgent",
]
