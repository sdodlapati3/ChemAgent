"""
Context Manager for ChemAgent.

Handles two types of context:
1. Conversation Memory - Session-scoped history for reference resolution
2. Orchestration Context - Task-scoped state for multi-agent coordination

Both can work independently or together for complex workflows.
"""

import json
import logging
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Set
from collections import deque
from datetime import datetime

logger = logging.getLogger(__name__)


# =============================================================================
# Conversation Memory (Session-scoped)
# =============================================================================

@dataclass
class ConversationTurn:
    """Single turn in a conversation."""
    turn_id: int
    query: str
    response: str
    intent: str
    entities: Dict[str, List[str]]  # compound_names, smiles, etc.
    tools_used: List[str]
    results_summary: Dict[str, Any]  # Key data points for reference
    timestamp: float = field(default_factory=time.time)
    
    def to_context_string(self, include_response: bool = True) -> str:
        """Convert turn to string for LLM context."""
        parts = [f"User: {self.query}"]
        if include_response:
            # Truncate long responses
            response = self.response[:500] + "..." if len(self.response) > 500 else self.response
            parts.append(f"Assistant: {response}")
        return "\n".join(parts)


@dataclass
class ConversationMemory:
    """
    Session-scoped conversation history.
    
    Enables:
    - Reference resolution ("that compound", "the second one")
    - Context-aware responses ("As I mentioned earlier...")
    - Entity tracking across turns
    """
    session_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    max_turns: int = 10  # Keep last N turns
    turns: List[ConversationTurn] = field(default_factory=list)
    
    # Entity tracking across conversation
    mentioned_compounds: List[str] = field(default_factory=list)
    mentioned_targets: List[str] = field(default_factory=list)
    last_results: Dict[str, Any] = field(default_factory=dict)
    
    def add_turn(
        self,
        query: str,
        response: str,
        intent: str = "",
        entities: Dict[str, List[str]] = None,
        tools_used: List[str] = None,
        results_summary: Dict[str, Any] = None
    ) -> ConversationTurn:
        """Add a conversation turn."""
        turn = ConversationTurn(
            turn_id=len(self.turns) + 1,
            query=query,
            response=response,
            intent=intent,
            entities=entities or {},
            tools_used=tools_used or [],
            results_summary=results_summary or {}
        )
        self.turns.append(turn)
        
        # Track entities mentioned
        if entities:
            for name in entities.get("compound_names", []):
                if name not in self.mentioned_compounds:
                    self.mentioned_compounds.append(name)
            for target in entities.get("uniprot_ids", []):
                if target not in self.mentioned_targets:
                    self.mentioned_targets.append(target)
        
        # Store last results for reference
        self.last_results = results_summary or {}
        
        # Trim to max turns
        if len(self.turns) > self.max_turns:
            self.turns = self.turns[-self.max_turns:]
        
        logger.info(f"Session {self.session_id}: Added turn {turn.turn_id}")
        return turn
    
    def get_context_for_llm(self, num_turns: int = 3) -> str:
        """Get recent conversation history for LLM context."""
        if not self.turns:
            return ""
        
        recent = self.turns[-num_turns:]
        context_parts = ["## Recent Conversation"]
        for turn in recent:
            context_parts.append(turn.to_context_string())
        
        return "\n\n".join(context_parts)
    
    def get_mentioned_entities(self) -> Dict[str, List[str]]:
        """Get all entities mentioned in conversation."""
        return {
            "compounds": self.mentioned_compounds[-10:],  # Last 10
            "targets": self.mentioned_targets[-10:]
        }
    
    def resolve_reference(self, query: str) -> Optional[str]:
        """
        Attempt to resolve references like "that compound", "the first one".
        Returns resolved entity or None.
        """
        query_lower = query.lower()
        
        # Check for pronoun references (including possessive "its")
        pronoun_refs = [
            "that compound", "this compound", "it", "that drug", "this drug",
            "its", "their", "the compound", "the drug", "this one", "that one"
        ]
        if any(ref in query_lower for ref in pronoun_refs):
            if self.mentioned_compounds:
                return self.mentioned_compounds[-1]
        
        # Check for ordinal references ("the first one", "the second compound")
        ordinals = {
            "first": 0, "1st": 0,
            "second": 1, "2nd": 1,
            "third": 2, "3rd": 2,
            "fourth": 3, "4th": 3,
            "fifth": 4, "5th": 4
        }
        
        for word, idx in ordinals.items():
            if word in query_lower:
                # Check if we have results with a list
                if "compounds" in self.last_results:
                    compounds = self.last_results["compounds"]
                    if isinstance(compounds, list) and len(compounds) > idx:
                        compound = compounds[idx]
                        # Extract name or ID
                        if isinstance(compound, dict):
                            return compound.get("name") or compound.get("chembl_id")
                        elif hasattr(compound, "name"):
                            return compound.name or getattr(compound, "chembl_id", None)
        
        return None
    
    def clear(self):
        """Clear conversation history."""
        self.turns.clear()
        self.mentioned_compounds.clear()
        self.mentioned_targets.clear()
        self.last_results.clear()
        logger.info(f"Session {self.session_id}: Cleared conversation memory")


# =============================================================================
# Orchestration Context (Task-scoped) - For Multi-Agent
# =============================================================================

@dataclass
class AgentOutput:
    """Output from a single agent in orchestration."""
    agent_id: str
    agent_type: str  # "chemist", "safety", "synthesis", etc.
    task: str
    result: Any
    confidence: float
    timestamp: float = field(default_factory=time.time)
    status: str = "completed"  # pending, running, completed, failed


@dataclass
class SubTask:
    """A sub-task in multi-agent orchestration."""
    task_id: str
    description: str
    assigned_agent: str
    dependencies: List[str] = field(default_factory=list)  # task_ids that must complete first
    status: str = "pending"  # pending, running, completed, failed
    result: Any = None


@dataclass
class OrchestrationContext:
    """
    Task-scoped context for multi-agent coordination.
    
    Enables:
    - Task decomposition and tracking
    - Cross-agent communication
    - Shared state and results aggregation
    - Dependency management
    """
    task_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    main_query: str = ""
    status: str = "initialized"  # initialized, planning, executing, aggregating, completed, failed
    
    # Task management
    sub_tasks: Dict[str, SubTask] = field(default_factory=dict)
    execution_order: List[str] = field(default_factory=list)
    
    # Agent outputs
    agent_outputs: Dict[str, AgentOutput] = field(default_factory=dict)
    
    # Shared state (accessible by all agents)
    shared_state: Dict[str, Any] = field(default_factory=dict)
    
    # Timing
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    
    def add_sub_task(
        self,
        description: str,
        assigned_agent: str,
        dependencies: List[str] = None
    ) -> SubTask:
        """Add a sub-task to the orchestration."""
        task_id = f"task_{len(self.sub_tasks) + 1}"
        task = SubTask(
            task_id=task_id,
            description=description,
            assigned_agent=assigned_agent,
            dependencies=dependencies or []
        )
        self.sub_tasks[task_id] = task
        logger.info(f"Orchestration {self.task_id}: Added sub-task {task_id} -> {assigned_agent}")
        return task
    
    def get_ready_tasks(self) -> List[SubTask]:
        """Get tasks whose dependencies are all completed."""
        ready = []
        for task in self.sub_tasks.values():
            if task.status != "pending":
                continue
            # Check if all dependencies completed
            deps_complete = all(
                self.sub_tasks.get(dep, SubTask("", "", "")).status == "completed"
                for dep in task.dependencies
            )
            if deps_complete:
                ready.append(task)
        return ready
    
    def record_agent_output(
        self,
        agent_id: str,
        agent_type: str,
        task: str,
        result: Any,
        confidence: float = 1.0
    ) -> AgentOutput:
        """Record output from an agent."""
        output = AgentOutput(
            agent_id=agent_id,
            agent_type=agent_type,
            task=task,
            result=result,
            confidence=confidence
        )
        self.agent_outputs[agent_id] = output
        
        # Update shared state with key results
        self.shared_state[f"{agent_type}_result"] = result
        
        logger.info(f"Orchestration {self.task_id}: Agent {agent_id} ({agent_type}) completed")
        return output
    
    def update_task_status(self, task_id: str, status: str, result: Any = None):
        """Update status of a sub-task."""
        if task_id in self.sub_tasks:
            self.sub_tasks[task_id].status = status
            if result is not None:
                self.sub_tasks[task_id].result = result
    
    def get_context_for_agent(self, agent_type: str) -> Dict[str, Any]:
        """Get relevant context for a specific agent type."""
        return {
            "task_id": self.task_id,
            "main_query": self.main_query,
            "shared_state": self.shared_state,
            "previous_outputs": {
                k: asdict(v) for k, v in self.agent_outputs.items()
            }
        }
    
    def is_complete(self) -> bool:
        """Check if all sub-tasks are completed."""
        return all(t.status in ("completed", "failed") for t in self.sub_tasks.values())
    
    def get_aggregated_results(self) -> Dict[str, Any]:
        """Aggregate results from all agents."""
        return {
            "task_id": self.task_id,
            "status": self.status,
            "sub_tasks": {k: asdict(v) for k, v in self.sub_tasks.items()},
            "agent_outputs": {k: asdict(v) for k, v in self.agent_outputs.items()},
            "shared_state": self.shared_state,
            "duration": (self.end_time or time.time()) - self.start_time
        }


# =============================================================================
# Unified Context Manager
# =============================================================================

class ContextManager:
    """
    Unified context manager for both conversation memory and orchestration.
    
    Usage:
        ctx = ContextManager()
        
        # Conversation memory (per session)
        session = ctx.get_or_create_session("user123")
        session.add_turn(query, response, ...)
        
        # Orchestration (per complex task)
        orch = ctx.create_orchestration("Find safe aspirin alternatives")
        orch.add_sub_task("Find similar compounds", "chemist_agent")
        orch.add_sub_task("Check safety", "safety_agent", dependencies=["task_1"])
    """
    
    def __init__(self, max_sessions: int = 100):
        self.max_sessions = max_sessions
        self.sessions: Dict[str, ConversationMemory] = {}
        self.orchestrations: Dict[str, OrchestrationContext] = {}
        self._session_access: Dict[str, float] = {}  # For LRU cleanup
    
    # ----- Session Management -----
    
    def get_or_create_session(self, session_id: str = None) -> ConversationMemory:
        """Get existing session or create new one."""
        if session_id is None:
            session_id = str(uuid.uuid4())[:8]
        
        if session_id not in self.sessions:
            # Cleanup old sessions if needed
            self._cleanup_sessions()
            self.sessions[session_id] = ConversationMemory(session_id=session_id)
            logger.info(f"Created new session: {session_id}")
        
        self._session_access[session_id] = time.time()
        return self.sessions[session_id]
    
    def get_session(self, session_id: str) -> Optional[ConversationMemory]:
        """Get existing session or None."""
        session = self.sessions.get(session_id)
        if session:
            self._session_access[session_id] = time.time()
        return session
    
    def _cleanup_sessions(self):
        """Remove oldest sessions if over limit (LRU)."""
        if len(self.sessions) >= self.max_sessions:
            # Sort by last access time
            sorted_sessions = sorted(
                self._session_access.items(),
                key=lambda x: x[1]
            )
            # Remove oldest 20%
            to_remove = len(self.sessions) // 5
            for session_id, _ in sorted_sessions[:to_remove]:
                del self.sessions[session_id]
                del self._session_access[session_id]
            logger.info(f"Cleaned up {to_remove} old sessions")
    
    # ----- Orchestration Management -----
    
    def create_orchestration(self, main_query: str) -> OrchestrationContext:
        """Create new orchestration context for a complex task."""
        orch = OrchestrationContext(main_query=main_query)
        self.orchestrations[orch.task_id] = orch
        logger.info(f"Created orchestration: {orch.task_id}")
        return orch
    
    def get_orchestration(self, task_id: str) -> Optional[OrchestrationContext]:
        """Get existing orchestration context."""
        return self.orchestrations.get(task_id)
    
    def cleanup_orchestration(self, task_id: str):
        """Remove completed orchestration."""
        if task_id in self.orchestrations:
            del self.orchestrations[task_id]
    
    # ----- Stats -----
    
    def get_stats(self) -> Dict[str, Any]:
        """Get context manager statistics."""
        return {
            "active_sessions": len(self.sessions),
            "active_orchestrations": len(self.orchestrations),
            "total_turns": sum(len(s.turns) for s in self.sessions.values())
        }


# =============================================================================
# Global Instance
# =============================================================================

# Singleton context manager
_context_manager: Optional[ContextManager] = None


def get_context_manager() -> ContextManager:
    """Get or create global context manager."""
    global _context_manager
    if _context_manager is None:
        _context_manager = ContextManager()
    return _context_manager


# =============================================================================
# Helper Functions
# =============================================================================

def extract_results_summary(results: Dict[str, Any]) -> Dict[str, Any]:
    """Extract key data points from tool results for context storage."""
    summary = {}
    
    for tool_name, result in results.items():
        if not isinstance(result, dict):
            continue
        
        data = result.get("data", {})
        if not isinstance(data, dict):
            continue
        
        # Extract compounds list
        if "compounds" in data:
            compounds = data["compounds"]
            if compounds:
                summary["compounds"] = []
                for c in compounds[:10]:  # Limit to 10
                    if hasattr(c, "chembl_id"):
                        summary["compounds"].append({
                            "chembl_id": c.chembl_id,
                            "name": getattr(c, "name", None) or getattr(c, "pref_name", None),
                            "smiles": getattr(c, "smiles", None)
                        })
                    elif isinstance(c, dict):
                        summary["compounds"].append({
                            "chembl_id": c.get("chembl_id"),
                            "name": c.get("name") or c.get("pref_name"),
                            "smiles": c.get("smiles")
                        })
        
        # Extract properties
        for prop in ["molecular_weight", "logp", "smiles", "formula"]:
            if prop in data:
                summary[prop] = data[prop]
    
    return summary
