"""
Agentic Trading System API endpoints.
Control and monitor the multi-agent trading system.
"""

from fastapi import APIRouter, HTTPException
from typing import List, Optional
import asyncio
import threading

from agents import (
    TradingSystem, ScannerAgent, ExecutionAgent, JournalAgent,
    AgentRole
)
from services.ibkr import ibkr_service

router = APIRouter(prefix="/agents", tags=["agents"])

# Global trading system instance
_trading_system: Optional[TradingSystem] = None
_system_thread: Optional[threading.Thread] = None


def get_system() -> TradingSystem:
    """Get or create the trading system."""
    global _trading_system

    if _trading_system is None:
        _trading_system = TradingSystem()

        # Add agents
        _trading_system.add_agent(ScannerAgent())
        _trading_system.add_agent(ExecutionAgent(ibkr_service=ibkr_service))
        _trading_system.add_agent(JournalAgent())

    return _trading_system


@router.post("/start")
def start_system():
    """Start the agentic trading system."""
    global _system_thread

    system = get_system()

    if system.orchestrator.running:
        return {"status": "already_running"}

    def run_system():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(system.start())

    _system_thread = threading.Thread(target=run_system, daemon=True)
    _system_thread.start()

    return {
        "status": "started",
        "agents": list(system.orchestrator.agents.keys()),
    }


@router.post("/stop")
def stop_system():
    """Stop the agentic trading system."""
    system = get_system()

    if not system.orchestrator.running:
        return {"status": "not_running"}

    system.stop()
    return {"status": "stopped"}


@router.get("/status")
def get_status():
    """Get status of all agents."""
    system = get_system()
    return system.get_status()


@router.get("/messages")
def get_messages(limit: int = 50):
    """Get recent inter-agent messages."""
    system = get_system()
    return {"messages": system.orchestrator.get_message_log(limit)}


@router.post("/scanner/watchlist")
def update_watchlist(symbols: List[str], action: str = "add"):
    """Update scanner watchlist."""
    system = get_system()

    scanner = system.orchestrator.agents.get(AgentRole.SCANNER)
    if not scanner:
        raise HTTPException(status_code=404, detail="Scanner agent not found")

    if action == "add":
        scanner.watchlist.extend(symbols)
        scanner.watchlist = list(set(scanner.watchlist))
    elif action == "remove":
        scanner.watchlist = [s for s in scanner.watchlist if s not in symbols]
    elif action == "set":
        scanner.watchlist = symbols

    scanner.state["watchlist"] = scanner.watchlist
    scanner.memory.save_state(scanner.state)

    return {"watchlist": scanner.watchlist}


@router.get("/scanner/watchlist")
def get_watchlist():
    """Get scanner watchlist."""
    system = get_system()

    scanner = system.orchestrator.agents.get(AgentRole.SCANNER)
    if not scanner:
        raise HTTPException(status_code=404, detail="Scanner agent not found")

    return {"watchlist": scanner.watchlist}


@router.get("/scanner/signals")
def get_signals():
    """Get recent signals from scanner."""
    system = get_system()

    scanner = system.orchestrator.agents.get(AgentRole.SCANNER)
    if not scanner:
        raise HTTPException(status_code=404, detail="Scanner agent not found")

    return {"signals": scanner.signals_found[-20:]}


@router.post("/scanner/scan-now")
def trigger_scan():
    """Trigger immediate market scan."""
    system = get_system()

    scanner = system.orchestrator.agents.get(AgentRole.SCANNER)
    if not scanner:
        raise HTTPException(status_code=404, detail="Scanner agent not found")

    scanner.last_scan = None  # Force immediate scan
    return {"status": "scan_triggered"}


@router.get("/execution/pending")
def get_pending_orders():
    """Get pending orders."""
    system = get_system()

    execution = system.orchestrator.agents.get(AgentRole.EXECUTION)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution agent not found")

    return {"pending": execution.pending_orders}


@router.get("/execution/history")
def get_execution_history():
    """Get executed orders history."""
    system = get_system()

    execution = system.orchestrator.agents.get(AgentRole.EXECUTION)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution agent not found")

    return {
        "executed": execution.executed_orders[-50:],
        "failed": execution.failed_orders[-20:],
    }


@router.get("/journal/performance")
def get_performance():
    """Get trading performance from journal."""
    system = get_system()

    journal = system.orchestrator.agents.get(AgentRole.JOURNAL)
    if not journal:
        raise HTTPException(status_code=404, detail="Journal agent not found")

    return {"performance": journal.performance}


@router.get("/journal/trades")
def get_trades(limit: int = 50):
    """Get recent trades from journal."""
    system = get_system()

    journal = system.orchestrator.agents.get(AgentRole.JOURNAL)
    if not journal:
        raise HTTPException(status_code=404, detail="Journal agent not found")

    return {"trades": journal.trades[-limit:]}


@router.get("/memory/{agent_name}")
def get_agent_memory(agent_name: str):
    """Get agent's learnings and mistakes."""
    system = get_system()

    # Find agent by name
    agent = None
    for a in system.orchestrator.agents.values():
        if a.name == agent_name:
            agent = a
            break

    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_name} not found")

    return {
        "learnings": agent.memory.learnings,
        "recent_mistakes": agent.memory.learnings.get("mistakes", [])[-10:],
        "patterns": agent.memory.learnings.get("patterns", [])[-10:],
    }
