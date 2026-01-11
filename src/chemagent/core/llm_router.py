"""
LLM Router for intelligent intent parsing.

Uses litellm for unified access to multiple LLM providers with automatic
fallback, retry, and cost tracking. Only called for queries where pattern
matching confidence is low (< 0.8).

Architecture:
    Pattern Matching (96.2%, <10ms)
           ↓ (confidence < 0.8)
    LLM Router (3.8%, ~200ms)
        ├─> Groq/Llama 3 8B (primary, free, fast)
        ├─> Gemini Flash 8B (fallback, free)
        └─> Together AI (tertiary, $25 credit)

Usage:
    >>> router = LLMRouter()
    >>> intent = router.parse_intent("Find aspirin-like compounds with good bioavailability")
    >>> intent.intent_type
    <IntentType.SIMILARITY_SEARCH: 'similarity_search'>
    >>> router.get_stats()
    {'total_queries': 1, 'total_cost': 0.0, 'avg_latency_ms': 187}

Free Tier Capacity:
    - Groq: 14,400 requests/day (our usage: ~18/day = 0.1%)
    - Gemini: 1,500 requests/day (fallback only)
    - Together: $25 credit = 1.25M queries
"""

import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .intent_parser import IntentType, ParsedIntent

logger = logging.getLogger(__name__)

# Check if litellm is available
try:
    import litellm
    from litellm import completion
    LITELLM_AVAILABLE = True
except ImportError:
    LITELLM_AVAILABLE = False
    logger.warning(
        "litellm not installed. LLM-based intent parsing disabled. "
        "Install with: pip install litellm"
    )


# System prompt for chemistry intent parsing
INTENT_PARSING_PROMPT = """You are a chemistry query parser for ChemAgent, a cheminformatics tool.

Parse the user's natural language query into a structured JSON format with:
1. intent_type: The type of chemistry query
2. entities: Extracted parameters (compounds, SMILES, targets, thresholds, etc.)
3. confidence: Your confidence in the parsing (0.0-1.0)

## Available Intent Types:

- similarity_search: Find compounds similar to a given structure
- substructure_search: Find compounds containing a substructure
- compound_lookup: Look up information about a compound
- target_lookup: Look up information about a biological target
- property_calculation: Calculate molecular properties (LogP, MW, TPSA, etc.)
- lipinski_check: Check Lipinski's Rule of Five compliance
- activity_lookup: Look up biological activity data (IC50, Ki, EC50)
- target_prediction: Predict targets for a compound
- structure_conversion: Convert between chemical formats
- scaffold_analysis: Analyze molecular scaffolds
- comparison: Compare properties of multiple compounds
- unknown: Cannot determine intent

## Entity Types:

- compound: Compound name (aspirin, ibuprofen, atorvastatin)
- smiles: SMILES string (CC(=O)Oc1ccccc1C(=O)O)
- chembl_id: ChEMBL ID (CHEMBL25, CHEMBL192)
- target: Target protein name (COX-2, HMG-CoA reductase, EGFR)
- target_chembl_id: Target ChEMBL ID (CHEMBL220)
- threshold: Similarity threshold (0.7, 0.8)
- property: Property name (logp, molecular_weight, tpsa)
- ic50_max: Maximum IC50 value
- compounds: List of compounds for comparison

## Examples:

Query: "Find compounds similar to aspirin with 70% similarity"
Output: {"intent_type": "similarity_search", "entities": {"compound": "aspirin", "threshold": 0.7}, "confidence": 0.95}

Query: "What's the IC50 of lipitor against HMG-CoA reductase?"
Output: {"intent_type": "activity_lookup", "entities": {"compound": "lipitor", "target": "HMG-CoA reductase"}, "confidence": 0.95}

Query: "Calculate Lipinski properties for CC(=O)Oc1ccccc1C(=O)O"
Output: {"intent_type": "lipinski_check", "entities": {"smiles": "CC(=O)Oc1ccccc1C(=O)O"}, "confidence": 0.9}

Query: "Compare molecular weight of aspirin vs ibuprofen vs naproxen"
Output: {"intent_type": "comparison", "entities": {"compounds": ["aspirin", "ibuprofen", "naproxen"], "property": "molecular_weight"}, "confidence": 0.9}

Query: "Find drugs targeting EGFR with IC50 below 100 nM"
Output: {"intent_type": "activity_lookup", "entities": {"target": "EGFR", "ic50_max": 100}, "confidence": 0.9}

## Rules:
1. Extract ALL relevant entities from the query
2. Use lowercase for intent_type
3. Return ONLY valid JSON, no markdown or explanation
4. If unsure, use "unknown" intent with lower confidence

Now parse the following query and return ONLY the JSON:"""


@dataclass
class LLMStats:
    """Statistics for LLM usage tracking."""
    total_queries: int = 0
    successful_queries: int = 0
    failed_queries: int = 0
    total_cost: float = 0.0
    total_latency_ms: float = 0.0
    provider_usage: Dict[str, int] = field(default_factory=dict)
    
    @property
    def avg_latency_ms(self) -> float:
        """Average latency in milliseconds."""
        if self.total_queries == 0:
            return 0.0
        return self.total_latency_ms / self.total_queries
    
    @property
    def success_rate(self) -> float:
        """Success rate as percentage."""
        if self.total_queries == 0:
            return 0.0
        return (self.successful_queries / self.total_queries) * 100
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_queries": self.total_queries,
            "successful_queries": self.successful_queries,
            "failed_queries": self.failed_queries,
            "success_rate": f"{self.success_rate:.1f}%",
            "total_cost": f"${self.total_cost:.6f}",
            "avg_latency_ms": f"{self.avg_latency_ms:.1f}ms",
            "provider_usage": self.provider_usage
        }


class LLMRouter:
    """
    Intelligent LLM router with automatic fallback and cost tracking.
    
    Uses litellm for unified access to multiple free-tier LLM providers.
    Only invoked when pattern matching confidence < threshold.
    
    Provider Priority:
        1. Groq (Llama 3 8B) - fastest, 14,400 RPD free
        2. Gemini Flash 8B - reliable, 1,500 RPD free
        3. Together AI - $25 free credit
    
    Attributes:
        primary_model: Primary LLM model (default: groq/llama3-8b-8192)
        fallback_models: List of fallback models
        confidence_threshold: Minimum pattern confidence to skip LLM
        stats: Usage statistics
    
    Example:
        >>> router = LLMRouter()
        >>> intent = router.parse_intent("Find aspirin analogs with IC50 < 100nM")
        >>> intent.intent_type
        <IntentType.SIMILARITY_SEARCH: 'similarity_search'>
    """
    
    # Default models (all have free tiers)
    DEFAULT_PRIMARY = "groq/llama3-8b-8192"
    DEFAULT_FALLBACKS = [
        "gemini/gemini-1.5-flash-8b",
        "together_ai/meta-llama/Llama-3-8B-Instruct-Turbo"
    ]
    
    def __init__(
        self,
        primary_model: Optional[str] = None,
        fallback_models: Optional[List[str]] = None,
        confidence_threshold: float = 0.8,
        enable_cost_tracking: bool = True,
        timeout: float = 30.0,
        max_retries: int = 2
    ):
        """
        Initialize LLM router.
        
        Args:
            primary_model: Primary LLM model identifier
            fallback_models: List of fallback model identifiers
            confidence_threshold: Skip LLM if pattern confidence >= this
            enable_cost_tracking: Track costs per request
            timeout: Request timeout in seconds
            max_retries: Number of retries per provider
        """
        self.primary_model = primary_model or self.DEFAULT_PRIMARY
        self.fallback_models = fallback_models or self.DEFAULT_FALLBACKS
        self.confidence_threshold = confidence_threshold
        self.enable_cost_tracking = enable_cost_tracking
        self.timeout = timeout
        self.max_retries = max_retries
        self.stats = LLMStats()
        
        # Configure litellm
        if LITELLM_AVAILABLE:
            litellm.set_verbose = False
            # Suppress litellm logs
            logging.getLogger("LiteLLM").setLevel(logging.WARNING)
    
    @property
    def is_available(self) -> bool:
        """Check if LLM routing is available."""
        if not LITELLM_AVAILABLE:
            return False
        # Check for at least one API key
        return any([
            os.environ.get("GROQ_API_KEY"),
            os.environ.get("GEMINI_API_KEY"),
            os.environ.get("GOOGLE_API_KEY"),
            os.environ.get("TOGETHER_API_KEY"),
            os.environ.get("OPENAI_API_KEY")
        ])
    
    def parse_intent(self, query: str) -> ParsedIntent:
        """
        Parse query using LLM.
        
        Args:
            query: Natural language chemistry query
            
        Returns:
            ParsedIntent with extracted type and entities
            
        Raises:
            RuntimeError: If LLM parsing fails and no fallback available
        """
        if not LITELLM_AVAILABLE:
            logger.warning("litellm not available, returning UNKNOWN intent")
            return ParsedIntent(
                intent_type=IntentType.UNKNOWN,
                entities={},
                original_query=query,
                confidence=0.0
            )
        
        start_time = time.time()
        self.stats.total_queries += 1
        
        try:
            # Call LLM with automatic fallback
            response = completion(
                model=self.primary_model,
                messages=[
                    {"role": "system", "content": INTENT_PARSING_PROMPT},
                    {"role": "user", "content": query}
                ],
                fallbacks=self.fallback_models,
                num_retries=self.max_retries,
                timeout=self.timeout,
                temperature=0.0,  # Deterministic for parsing
                max_tokens=300,
                response_format={"type": "json_object"} if "groq" in self.primary_model else None
            )
            
            # Track latency
            latency_ms = (time.time() - start_time) * 1000
            self.stats.total_latency_ms += latency_ms
            
            # Track provider usage
            model_used = response.model or self.primary_model
            provider = model_used.split("/")[0] if "/" in model_used else model_used
            self.stats.provider_usage[provider] = self.stats.provider_usage.get(provider, 0) + 1
            
            # Track cost
            if self.enable_cost_tracking:
                try:
                    cost = litellm.completion_cost(response)
                    self.stats.total_cost += cost
                except Exception:
                    pass  # Cost tracking optional
            
            # Parse response
            content = response.choices[0].message.content
            intent = self._parse_llm_response(content, query)
            
            self.stats.successful_queries += 1
            logger.debug(
                f"LLM parsed intent: {intent.intent_type.value} "
                f"(provider={provider}, latency={latency_ms:.0f}ms)"
            )
            
            return intent
            
        except Exception as e:
            self.stats.failed_queries += 1
            latency_ms = (time.time() - start_time) * 1000
            self.stats.total_latency_ms += latency_ms
            
            logger.error(f"LLM parsing failed: {e}")
            
            # Return UNKNOWN intent on failure
            return ParsedIntent(
                intent_type=IntentType.UNKNOWN,
                entities={},
                original_query=query,
                confidence=0.0
            )
    
    def _parse_llm_response(self, content: str, original_query: str) -> ParsedIntent:
        """
        Parse LLM JSON response into ParsedIntent.
        
        Args:
            content: Raw LLM response content
            original_query: Original user query
            
        Returns:
            ParsedIntent parsed from LLM response
        """
        try:
            # Clean response (remove markdown if present)
            content = content.strip()
            if content.startswith("```"):
                # Extract JSON from markdown code block
                lines = content.split("\n")
                content = "\n".join(
                    line for line in lines 
                    if not line.startswith("```")
                )
            
            data = json.loads(content)
            
            # Parse intent type
            intent_str = data.get("intent_type", "unknown").upper()
            try:
                intent_type = IntentType[intent_str]
            except KeyError:
                # Try to match by value
                intent_type = IntentType.UNKNOWN
                for it in IntentType:
                    if it.value == data.get("intent_type", "").lower():
                        intent_type = it
                        break
            
            # Extract entities
            entities = data.get("entities", {})
            
            # Extract confidence
            confidence = float(data.get("confidence", 0.8))
            
            return ParsedIntent(
                intent_type=intent_type,
                entities=entities,
                original_query=original_query,
                confidence=confidence
            )
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM JSON response: {e}")
            logger.debug(f"Raw response: {content}")
            
            return ParsedIntent(
                intent_type=IntentType.UNKNOWN,
                entities={},
                original_query=original_query,
                confidence=0.0
            )
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get usage statistics.
        
        Returns:
            Dictionary with query counts, costs, latency, provider usage
        """
        return self.stats.to_dict()
    
    def reset_stats(self):
        """Reset usage statistics."""
        self.stats = LLMStats()
    
    def __repr__(self) -> str:
        """String representation."""
        return (
            f"LLMRouter(primary={self.primary_model}, "
            f"fallbacks={len(self.fallback_models)}, "
            f"available={self.is_available})"
        )


class HybridIntentParser:
    """
    Hybrid intent parser combining pattern matching with LLM fallback.
    
    Strategy:
        1. Try pattern matching first (96.2% success, <10ms)
        2. If confidence < threshold, use LLM (3.8%, ~200ms)
        3. Return best result
    
    This maintains speed for common queries while handling edge cases.
    
    Example:
        >>> from chemagent.core.intent_parser import IntentParser
        >>> parser = HybridIntentParser(IntentParser(), LLMRouter())
        >>> 
        >>> # Simple query - handled by pattern matching
        >>> intent = parser.parse("Calculate LogP of aspirin")
        >>> intent.confidence
        1.0
        >>> 
        >>> # Complex query - falls back to LLM
        >>> intent = parser.parse("Find kinase inhibitors similar to imatinib with nanomolar potency")
        >>> intent.confidence
        0.9
    """
    
    def __init__(
        self,
        pattern_parser,
        llm_router: Optional[LLMRouter] = None,
        confidence_threshold: float = 0.8,
        enable_llm: bool = True
    ):
        """
        Initialize hybrid parser.
        
        Args:
            pattern_parser: Pattern-based IntentParser instance
            llm_router: LLMRouter instance (created if None)
            confidence_threshold: Use LLM if pattern confidence < this
            enable_llm: Whether to enable LLM fallback
        """
        self.pattern_parser = pattern_parser
        self.llm_router = llm_router or LLMRouter()
        self.confidence_threshold = confidence_threshold
        self.enable_llm = enable_llm
        
        # Statistics
        self.stats = {
            "total_queries": 0,
            "pattern_match": 0,
            "llm_fallback": 0,
            "unknown": 0
        }
    
    def parse(self, query: str) -> ParsedIntent:
        """
        Parse query with pattern matching + LLM fallback.
        
        Args:
            query: Natural language chemistry query
            
        Returns:
            ParsedIntent from pattern matching or LLM
        """
        self.stats["total_queries"] += 1
        
        # Step 1: Try pattern matching (FAST PATH)
        pattern_result = self.pattern_parser.parse(query)
        
        # If high confidence or UNKNOWN (might be unsupported), use pattern result
        if pattern_result.confidence >= self.confidence_threshold:
            self.stats["pattern_match"] += 1
            return pattern_result
        
        # Step 2: LLM fallback (SLOW PATH for edge cases)
        if self.enable_llm and self.llm_router.is_available:
            llm_result = self.llm_router.parse_intent(query)
            
            # Use LLM result if it's better
            if llm_result.intent_type != IntentType.UNKNOWN:
                self.stats["llm_fallback"] += 1
                return llm_result
        
        # Step 3: Fall back to pattern result (even if low confidence)
        if pattern_result.intent_type != IntentType.UNKNOWN:
            self.stats["pattern_match"] += 1
            return pattern_result
        
        # Nothing worked
        self.stats["unknown"] += 1
        return pattern_result
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get parsing statistics.
        
        Returns:
            Dictionary with query routing statistics
        """
        total = self.stats["total_queries"]
        if total == 0:
            return self.stats
        
        return {
            **self.stats,
            "pattern_match_pct": f"{self.stats['pattern_match'] / total * 100:.1f}%",
            "llm_fallback_pct": f"{self.stats['llm_fallback'] / total * 100:.1f}%",
            "unknown_pct": f"{self.stats['unknown'] / total * 100:.1f}%",
            "llm_stats": self.llm_router.get_stats() if self.llm_router else None
        }


# Convenience function for quick testing
def quick_parse(query: str, use_llm: bool = True) -> ParsedIntent:
    """
    Quick parse a query (for testing/demo).
    
    Args:
        query: Chemistry query to parse
        use_llm: Whether to enable LLM fallback
        
    Returns:
        ParsedIntent with type and entities
        
    Example:
        >>> result = quick_parse("Find compounds similar to aspirin")
        >>> result.intent_type
        <IntentType.SIMILARITY_SEARCH: 'similarity_search'>
    """
    from .intent_parser import IntentParser
    
    pattern_parser = IntentParser()
    
    if use_llm:
        hybrid = HybridIntentParser(pattern_parser)
        return hybrid.parse(query)
    else:
        return pattern_parser.parse(query)


if __name__ == "__main__":
    # Demo usage
    import sys
    
    print("=" * 60)
    print("LLM Router Demo")
    print("=" * 60)
    
    # Check availability
    router = LLMRouter()
    print(f"\nRouter: {router}")
    print(f"LLM Available: {router.is_available}")
    
    if not router.is_available:
        print("\n⚠️  No API keys found. Set one of:")
        print("   export GROQ_API_KEY='your-key'")
        print("   export GEMINI_API_KEY='your-key'")
        print("   export TOGETHER_API_KEY='your-key'")
        sys.exit(1)
    
    # Test queries
    test_queries = [
        "Find compounds similar to aspirin with 70% similarity",
        "What is the IC50 of imatinib against ABL kinase?",
        "Calculate Lipinski properties for CC(=O)Oc1ccccc1C(=O)O",
        "Compare molecular weight of aspirin vs ibuprofen",
        "Find EGFR inhibitors with nanomolar potency and good oral bioavailability"
    ]
    
    print("\n" + "-" * 60)
    print("Testing LLM Intent Parsing")
    print("-" * 60)
    
    for query in test_queries:
        print(f"\nQuery: {query}")
        result = router.parse_intent(query)
        print(f"  Intent: {result.intent_type.value}")
        print(f"  Entities: {result.entities}")
        print(f"  Confidence: {result.confidence}")
    
    print("\n" + "-" * 60)
    print("Statistics")
    print("-" * 60)
    for key, value in router.get_stats().items():
        print(f"  {key}: {value}")
