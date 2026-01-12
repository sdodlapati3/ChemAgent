"""Core ChemAgent components: parsing, planning, execution."""

from chemagent.core.executor import (
    ExecutionResult,
    ExecutionStatus,
    ProgressCallback,
    ProgressEvent,
    QueryExecutor,
    StepResult,
    ToolRegistry,
    get_tool_description,
)
from chemagent.core.intent_parser import (
    IntentParser,
    IntentType,
    ParsedIntent,
)
from chemagent.core.query_planner import (
    PlanStep,
    QueryPlan,
    QueryPlanner,
)
from chemagent.core.response_formatter import (
    ResponseFormatter,
    format_response,
)

# Context Manager for conversation memory and multi-agent orchestration
from chemagent.core.context_manager import (
    ContextManager,
    ConversationMemory,
    ConversationTurn,
    OrchestrationContext,
    AgentOutput,
    SubTask,
    get_context_manager,
    extract_results_summary,
)

# OptimalAgent (hybrid tiered architecture - requires litellm for LLM features)
try:
    from chemagent.core.optimal_agent import (
        OptimalAgent,
        AgentResponse,
        EntityExtractor,
        IntentClassifier,
        ToolPlanner,
        create_optimal_agent,
        LITELLM_AVAILABLE as AGENT_AVAILABLE,
    )
except ImportError:
    AGENT_AVAILABLE = False
    OptimalAgent = None
    AgentResponse = None
    EntityExtractor = None
    IntentClassifier = None
    ToolPlanner = None
    create_optimal_agent = None

# Verifier Gate for hallucination prevention
try:
    from chemagent.core.verifier import (
        VerifierGate,
        ClaimVerifier,
        ClaimExtractor,
        VerifierReport,
        VerificationResult,
        Claim,
        ClaimType,
        VerificationStatus,
        verify_response,
        create_verifier_gate,
    )
    VERIFIER_AVAILABLE = True
except ImportError:
    VERIFIER_AVAILABLE = False
    VerifierGate = None
    ClaimVerifier = None
    ClaimExtractor = None
    VerifierReport = None
    VerificationResult = None
    Claim = None
    ClaimType = None
    VerificationStatus = None
    verify_response = None
    create_verifier_gate = None

# Multi-Agent Orchestration System
try:
    from chemagent.core.multi_agent import (
        CoordinatorAgent,
        CompoundAgent,
        ActivityAgent,
        PropertyAgent,
        TargetAgent,
        BaseAgent,
        AgentRole,
        AgentTask,
        AgentResult,
        ModelConfig,
        create_multi_agent_system,
        LITELLM_AVAILABLE as MULTI_AGENT_AVAILABLE,
    )
except ImportError:
    MULTI_AGENT_AVAILABLE = False
    CoordinatorAgent = None
    CompoundAgent = None
    ActivityAgent = None
    PropertyAgent = None
    TargetAgent = None
    BaseAgent = None
    AgentRole = None
    AgentTask = None
    AgentResult = None
    ModelConfig = None
    create_multi_agent_system = None

__all__ = [
    # Core components
    "ExecutionResult",
    "ExecutionStatus",
    "IntentParser",
    "IntentType",
    "ParsedIntent",
    "PlanStep",
    "ProgressCallback",
    "ProgressEvent",
    "QueryExecutor",
    "QueryPlan",
    "QueryPlanner",
    "ResponseFormatter",
    "StepResult",
    "ToolRegistry",
    "format_response",
    "get_tool_description",
    # OptimalAgent (hybrid tiered architecture)
    "OptimalAgent",
    "AgentResponse",
    "EntityExtractor",
    "IntentClassifier",
    "ToolPlanner",
    "AGENT_AVAILABLE",
    "create_optimal_agent",
    # Verifier Gate
    "VerifierGate",
    "ClaimVerifier",
    "ClaimExtractor",
    "VerifierReport",
    "VerificationResult",
    "Claim",
    "ClaimType",
    "VerificationStatus",
    "VERIFIER_AVAILABLE",
    "verify_response",
    "create_verifier_gate",
    # Multi-Agent Orchestration
    "CoordinatorAgent",
    "CompoundAgent",
    "ActivityAgent",
    "PropertyAgent",
    "TargetAgent",
    "BaseAgent",
    "AgentRole",
    "AgentTask",
    "AgentResult",
    "ModelConfig",
    "MULTI_AGENT_AVAILABLE",
    "create_multi_agent_system",
]
