"""Core ChemAgent components: parsing, planning, execution."""

from chemagent.core.executor import (
    ExecutionResult,
    ExecutionStatus,
    QueryExecutor,
    StepResult,
    ToolRegistry,
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

# LLM router (optional - requires litellm)
try:
    from chemagent.core.llm_router import (
        HybridIntentParser,
        LLMRouter,
        LLMStats,
        quick_parse,
    )
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False
    HybridIntentParser = None
    LLMRouter = None
    LLMStats = None
    quick_parse = None

__all__ = [
    "ExecutionResult",
    "ExecutionStatus",
    "HybridIntentParser",
    "IntentParser",
    "IntentType",
    "LLMRouter",
    "LLMStats",
    "LLM_AVAILABLE",
    "ParsedIntent",
    "PlanStep",
    "QueryExecutor",
    "QueryPlan",
    "QueryPlanner",
    "ResponseFormatter",
    "StepResult",
    "ToolRegistry",
    "format_response",
    "quick_parse",
]
