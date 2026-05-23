"""
Base Agent Class
All trading agents inherit from this base class.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
import json
import os
import asyncio
from dataclasses import dataclass, field


class AgentRole(Enum):
    ORCHESTRATOR = "orchestrator"
    SCANNER = "scanner"
    TECHNICAL = "technical"
    RISK = "risk"
    EXECUTION = "execution"
    JOURNAL = "journal"
    LEARNING = "learning"


class MessageType(Enum):
    SIGNAL = "signal"           # Trading signal
    REPORT = "report"           # Status report
    REQUEST = "request"         # Request for action
    RESPONSE = "response"       # Response to request
    ALERT = "alert"             # Urgent notification
    LEARNING = "learning"       # Learning/improvement data


@dataclass
class Message:
    """Inter-agent communication message."""
    id: str
    sender: AgentRole
    recipient: AgentRole
    msg_type: MessageType
    payload: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    priority: int = 5  # 1-10, higher = more urgent

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "sender": self.sender.value,
            "recipient": self.recipient.value,
            "type": self.msg_type.value,
            "payload": self.payload,
            "timestamp": self.timestamp.isoformat(),
            "priority": self.priority,
        }


class Memory:
    """
    Agent memory system - persists learnings and mistakes.
    Creates markdown files for human review and JSON for agent use.
    """

    def __init__(self, agent_name: str, memory_dir: str = "memory"):
        self.agent_name = agent_name
        self.memory_dir = os.path.join(os.path.dirname(__file__), "..", "..", memory_dir)
        os.makedirs(self.memory_dir, exist_ok=True)

        self.mistakes_file = os.path.join(self.memory_dir, f"{agent_name}_mistakes.md")
        self.learnings_file = os.path.join(self.memory_dir, f"{agent_name}_learnings.json")
        self.state_file = os.path.join(self.memory_dir, f"{agent_name}_state.json")

        self.learnings = self._load_learnings()

    def _load_learnings(self) -> Dict:
        if os.path.exists(self.learnings_file):
            try:
                with open(self.learnings_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {"patterns": [], "mistakes": [], "successes": [], "weights": {}}

    def _save_learnings(self):
        with open(self.learnings_file, 'w') as f:
            json.dump(self.learnings, f, indent=2, default=str)

    def record_mistake(self, context: Dict, mistake: str, correction: str):
        """Record a mistake for learning."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "context": context,
            "mistake": mistake,
            "correction": correction,
        }
        self.learnings["mistakes"].append(entry)
        self._save_learnings()

        # Also write to markdown for human review
        with open(self.mistakes_file, 'a') as f:
            f.write(f"\n## Mistake - {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
            f.write(f"**Context:** {json.dumps(context, indent=2)}\n")
            f.write(f"**Mistake:** {mistake}\n")
            f.write(f"**Correction:** {correction}\n")
            f.write("---\n")

    def record_success(self, context: Dict, action: str, outcome: Dict):
        """Record a successful action for reinforcement."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "context": context,
            "action": action,
            "outcome": outcome,
        }
        self.learnings["successes"].append(entry)
        self._save_learnings()

    def add_pattern(self, pattern: Dict):
        """Add a learned pattern."""
        self.learnings["patterns"].append({
            "timestamp": datetime.now().isoformat(),
            **pattern
        })
        self._save_learnings()

    def get_relevant_learnings(self, context: Dict) -> List[Dict]:
        """Retrieve learnings relevant to current context."""
        # Simple keyword matching - could be enhanced with embeddings
        relevant = []
        context_str = json.dumps(context).lower()

        for mistake in self.learnings["mistakes"]:
            if any(word in context_str for word in str(mistake.get("context", "")).lower().split()):
                relevant.append({"type": "mistake", **mistake})

        for success in self.learnings["successes"]:
            if any(word in context_str for word in str(success.get("context", "")).lower().split()):
                relevant.append({"type": "success", **success})

        return relevant[-10:]  # Last 10 relevant learnings

    def save_state(self, state: Dict):
        """Persist agent state."""
        with open(self.state_file, 'w') as f:
            json.dump(state, f, indent=2, default=str)

    def load_state(self) -> Dict:
        """Load persisted agent state."""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {}


class BaseAgent(ABC):
    """
    Base class for all trading agents.

    Each agent:
    - Has a specific role
    - Can send/receive messages
    - Has memory for learning
    - Runs autonomously in a loop
    - Reports to the orchestrator
    """

    def __init__(self, role: AgentRole, orchestrator=None):
        self.role = role
        self.name = role.value
        self.orchestrator = orchestrator
        self.memory = Memory(self.name)
        self.running = False
        self.inbox: asyncio.Queue = asyncio.Queue()
        self.state = self.memory.load_state()

        # Performance tracking
        self.actions_taken = 0
        self.successful_actions = 0
        self.errors = []

    @abstractmethod
    async def process(self) -> Optional[Message]:
        """
        Main processing logic - implemented by each agent.
        Returns a message to send if any.
        """
        pass

    @abstractmethod
    async def handle_message(self, message: Message) -> Optional[Message]:
        """Handle incoming message from another agent."""
        pass

    async def send(self, recipient: AgentRole, msg_type: MessageType, payload: Dict, priority: int = 5):
        """Send a message to another agent via orchestrator."""
        message = Message(
            id=f"{self.name}_{datetime.now().timestamp()}",
            sender=self.role,
            recipient=recipient,
            msg_type=msg_type,
            payload=payload,
            priority=priority,
        )

        if self.orchestrator:
            await self.orchestrator.route_message(message)

        return message

    async def receive(self, message: Message):
        """Receive a message into inbox."""
        await self.inbox.put(message)

    async def run(self, interval_seconds: float = 1.0):
        """Main agent loop."""
        self.running = True
        print(f"[{self.name}] Agent started")

        while self.running:
            try:
                # Process any incoming messages
                while not self.inbox.empty():
                    message = await self.inbox.get()
                    response = await self.handle_message(message)
                    if response and self.orchestrator:
                        await self.orchestrator.route_message(response)

                # Run main processing
                result = await self.process()
                if result and self.orchestrator:
                    await self.orchestrator.route_message(result)

                await asyncio.sleep(interval_seconds)

            except Exception as e:
                self.errors.append({
                    "timestamp": datetime.now().isoformat(),
                    "error": str(e)
                })
                self.memory.record_mistake(
                    context={"state": self.state},
                    mistake=str(e),
                    correction="Agent recovered and continued"
                )
                await asyncio.sleep(interval_seconds)

        print(f"[{self.name}] Agent stopped")

    def stop(self):
        """Stop the agent."""
        self.running = False
        self.memory.save_state(self.state)

    def get_status(self) -> Dict:
        """Get agent status."""
        return {
            "name": self.name,
            "role": self.role.value,
            "running": self.running,
            "actions_taken": self.actions_taken,
            "successful_actions": self.successful_actions,
            "success_rate": self.successful_actions / max(1, self.actions_taken),
            "error_count": len(self.errors),
            "recent_errors": self.errors[-5:],
        }
