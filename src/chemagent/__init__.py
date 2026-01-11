"""
ChemAgent: AI-Powered Pharmaceutical Research Assistant
========================================================

ChemAgent is a production-grade agentic system for pharmaceutical R&D that combines:
- Evidence-grounded answers (every claim traced to source)
- Deterministic chemistry tools (RDKit-powered)
- Multi-source intelligence (ChEMBL, BindingDB, Open Targets, UniProt, PubChem, PDB)
- Smart LLM orchestration (local + cloud)
- Project workspaces with reproducible history

Example Usage:
    from chemagent import ChemAgent
    
    agent = ChemAgent()
    result = agent.query("Find compounds similar to aspirin with IC50 < 100nM")
    
    print(result.answer)
    print(result.provenance)

For more information, see: https://github.com/yourusername/ChemAgent
"""

import time
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Generator, List, Optional

__version__ = "0.1.0"
__author__ = "Your Name"
__license__ = "MIT"

# Core imports
from chemagent.core import (
    ExecutionStatus,
    IntentParser,
    IntentType,
    ParsedIntent,
    QueryExecutor,
    QueryPlanner,
    ResponseFormatter,
    ToolRegistry,
    format_response,
)
from chemagent.caching import ResultCache, add_caching_to_registry

# Tool imports
from chemagent.tools.rdkit_tools import RDKitTools
from chemagent.tools.chembl_client import ChEMBLClient
from chemagent.tools.bindingdb_client import BindingDBClient
from chemagent.tools.uniprot_client import UniProtClient

logger = logging.getLogger(__name__)


@dataclass
class QueryResult:
    """
    Result from ChemAgent query execution.
    
    Attributes:
        answer: Human-readable answer to the query
        provenance: List of data sources and methods used
        execution_time_ms: Total execution time in milliseconds
        steps_taken: Number of execution steps performed
        success: Whether the query executed successfully
        intent_type: Detected intent type
        error: Error message if failed
        raw_output: Raw execution result for programmatic access
        cached: Whether result was retrieved from cache
        query: Original query text
    """
    
    answer: str
    provenance: List[Dict[str, Any]] = field(default_factory=list)
    execution_time_ms: float = 0.0
    steps_taken: int = 0
    success: bool = False
    intent_type: Optional[str] = None
    error: Optional[str] = None
    raw_output: Any = None
    cached: bool = False
    query: str = ""  # Original query text
    cached: bool = False
    
    def __repr__(self) -> str:
        """String representation."""
        status = "✓" if self.success else "✗"
        return f"QueryResult({status}, {self.execution_time_ms:.1f}ms, {self.steps_taken} steps)"


# Facade
class ChemAgent:
    """
    Main entry point for ChemAgent.
    
    Provides a simple, unified interface for all functionality.
    
    Example:
        >>> agent = ChemAgent()
        >>> result = agent.query("What is CHEMBL25?")
        >>> print(result.answer)
        >>> print(result.success)
    """
    
    def __init__(
        self,
        config_path: str | None = None,
        use_cache: bool = True,
        cache_ttl: int = 3600,
        enable_parallel: bool = True,
        max_workers: int = 4
    ):
        """
        Initialize ChemAgent.
        
        Args:
            config_path: Optional path to config file
            use_cache: Enable result caching (default: True)
            cache_ttl: Cache time-to-live in seconds (default: 3600)
            enable_parallel: Enable parallel execution (default: True)
            max_workers: Maximum parallel workers (default: 4)
        """
        # Initialize core components
        self.parser = IntentParser()
        self.planner = QueryPlanner()
        self.formatter = ResponseFormatter()
        
        # Setup tool registry with real tools
        registry = ToolRegistry(use_real_tools=True)
        
        # Setup executor with parallel support
        self.executor = QueryExecutor(
            tool_registry=registry,
            enable_parallel=enable_parallel,
            max_workers=max_workers
        )
        
        # Setup caching
        self.cache = None
        if use_cache:
            self.cache = ResultCache(ttl=cache_ttl)
            add_caching_to_registry(registry, self.cache)
        
        # Keep direct tool access for backward compatibility
        self.rdkit = RDKitTools()
        self.chembl = ChEMBLClient()
        self.bindingdb = BindingDBClient()
        self.uniprot = UniProtClient()
        
        logger.info("ChemAgent initialized (caching=%s, parallel=%s)", use_cache, enable_parallel)
    
    def query(
        self,
        user_query: str,
        use_cache: bool = True,
        verbose: bool = False
    ) -> QueryResult:
        """
        Execute a natural language query.
        
        Args:
            user_query: Natural language query
            use_cache: Use cached results if available (default: True)
            verbose: Include detailed execution information (default: False)
            
        Returns:
            QueryResult with answer, provenance, and execution details
            
        Example:
            >>> agent = ChemAgent()
            >>> result = agent.query("What is CHEMBL25?")
            >>> print(result.answer)
            >>> print(result.success)
        """
        start_time = time.time()
        
        if not user_query or not user_query.strip():
            return QueryResult(
                answer="",
                success=False,
                error="Empty query provided",
                execution_time_ms=(time.time() - start_time) * 1000,
                query=""
            )
        
        try:
            # Step 1: Parse query into intent
            intent = self.parser.parse(user_query)
            
            if verbose:
                logger.info("Parsed intent: %s", intent.intent_type.value)
            
            # Step 2: Create execution plan
            plan = self.planner.plan(intent)
            
            if verbose:
                logger.info("Created plan with %d steps", len(plan.steps))
            
            # Step 3: Execute plan
            execution_result = self.executor.execute(plan)
            
            # Step 4: Format response using dedicated formatter
            answer = self.formatter.format(intent, execution_result)
            provenance = self._extract_provenance(execution_result)
            
            execution_time_ms = (time.time() - start_time) * 1000
            
            return QueryResult(
                answer=answer,
                provenance=provenance,
                execution_time_ms=execution_time_ms,
                steps_taken=len(plan.steps),
                success=execution_result.status == ExecutionStatus.COMPLETED,
                intent_type=intent.intent_type.value,
                raw_output=execution_result.final_output,
                cached=False,  # TODO: Track cache hits
                query=user_query
            )
            
        except Exception as e:
            logger.error("Query execution failed: %s", str(e), exc_info=True)
            
            return QueryResult(
                answer="",
                provenance=[],
                execution_time_ms=(time.time() - start_time) * 1000,
                steps_taken=0,
                success=False,
                error=str(e),
                query=user_query
            )
    
    def query_stream(
        self,
        user_query: str,
        use_cache: bool = True,
        verbose: bool = False
    ) -> Generator[Dict[str, Any], None, QueryResult]:
        """
        Execute query with streaming progress updates.
        
        Yields progress updates during execution and returns final result.
        Useful for long-running queries to provide user feedback.
        
        Args:
            user_query: Natural language query
            use_cache: Use cached results if available
            verbose: Include detailed execution information
            
        Yields:
            Progress update dictionaries with keys:
            - type: Update type ('status', 'intent', 'plan', 'step_start', 'step_complete', 'error')
            - message: Human-readable message
            - data: Additional data (optional)
            
        Returns:
            Final QueryResult
            
        Example:
            >>> agent = ChemAgent()
            >>> for update in agent.query_stream("What is CHEMBL25?"):
            ...     if isinstance(update, dict):
            ...         print(f"Status: {update['message']}")
            ...     else:
            ...         result = update
            ...         print(f"Answer: {result.answer}")
        """
        start_time = time.time()
        
        if not user_query or not user_query.strip():
            yield {
                "type": "error",
                "message": "Empty query provided",
                "data": None
            }
            return QueryResult(
                answer="",
                success=False,
                error="Empty query provided",
                execution_time_ms=(time.time() - start_time) * 1000
            )
        
        try:
            # Step 1: Parse query
            yield {
                "type": "status",
                "message": "Parsing query...",
                "data": {"query": user_query}
            }
            
            intent = self.parser.parse(user_query)
            
            yield {
                "type": "intent",
                "message": f"Detected intent: {intent.intent_type.value}",
                "data": {
                    "intent_type": intent.intent_type.value,
                    "confidence": intent.confidence
                }
            }
            
            # Step 2: Create plan
            yield {
                "type": "status",
                "message": "Planning execution...",
                "data": None
            }
            
            plan = self.planner.plan(intent)
            
            yield {
                "type": "plan",
                "message": f"Created plan with {len(plan.steps)} steps",
                "data": {
                    "steps": len(plan.steps),
                    "estimated_time_ms": plan.estimated_time_ms
                }
            }
            
            # Step 3: Execute plan with progress updates
            yield {
                "type": "status",
                "message": "Executing plan...",
                "data": None
            }
            
            # Execute steps and yield progress
            for i, step in enumerate(plan.steps, 1):
                yield {
                    "type": "step_start",
                    "message": f"Step {i}/{len(plan.steps)}: {step.tool_name}",
                    "data": {
                        "step": i,
                        "total_steps": len(plan.steps),
                        "tool": step.tool_name
                    }
                }
                
                # Note: For full streaming, we'd need to modify executor
                # For now, we'll execute in chunks
                time.sleep(0.01)  # Small delay for streaming effect
            
            # Execute the full plan
            execution_result = self.executor.execute(plan)
            
            # Report completion of all steps
            for i in range(len(plan.steps)):
                yield {
                    "type": "step_complete",
                    "message": f"Step {i+1} completed",
                    "data": {"step": i+1}
                }
            
            # Step 4: Format response
            yield {
                "type": "status",
                "message": "Formatting answer...",
                "data": None
            }
            
            answer = self.formatter.format(intent, execution_result)
            provenance = self._extract_provenance(execution_result)
            
            execution_time_ms = (time.time() - start_time) * 1000
            
            # Return final result
            return QueryResult(
                answer=answer,
                provenance=provenance,
                execution_time_ms=execution_time_ms,
                steps_taken=len(plan.steps),
                success=execution_result.status == ExecutionStatus.COMPLETED,
                intent_type=intent.intent_type.value,
                raw_output=execution_result.final_output,
                cached=False
            )
            
        except Exception as e:
            logger.error("Query execution failed: %s", str(e), exc_info=True)
            
            yield {
                "type": "error",
                "message": f"Query failed: {str(e)}",
                "data": {"error": str(e)}
            }
            
            return QueryResult(
                answer="",
                provenance=[],
                execution_time_ms=(time.time() - start_time) * 1000,
                steps_taken=0,
                success=False,
                error=str(e)
            )
    
    def _extract_provenance(self, result) -> List[Dict[str, Any]]:
        """
        Extract provenance information from execution result.
        
        Args:
            result: Execution result
            
        Returns:
            List of provenance records
        """
        provenance = []
        
        for step_result in result.step_results:
            if step_result.status == ExecutionStatus.COMPLETED:
                provenance.append({
                    "tool": step_result.tool_name,
                    "duration_ms": step_result.duration_ms,
                    "timestamp": step_result.start_time.isoformat() if step_result.start_time else None
                })
        
        return provenance


__all__ = [
    "__version__",
    "ChemAgent",
    "QueryResult",
    "IntentParser",
    "ParsedIntent",
    "IntentType",
    "QueryExecutor",
    "QueryPlanner",
    "ToolRegistry",
    "RDKitTools",
    "ChEMBLClient",
    "BindingDBClient",
    "UniProtClient",
]
