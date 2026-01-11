"""
Query execution engine.

Executes query plans by running steps in order, managing dependencies,
resolving variable references, and aggregating results.

Supports both serial and parallel execution modes for improved performance.
"""

import re
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from chemagent.core.query_planner import PlanStep, QueryPlan
from chemagent.core.parallel import ParallelExecutor, ExecutionMetrics

logger = logging.getLogger(__name__)


class ExecutionStatus(Enum):
    """Status of execution."""
    
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class StepResult:
    """
    Result of executing a single step.
    
    Attributes:
        step_id: ID of the step
        tool_name: Name of the tool executed
        status: Execution status
        output: Step output (if successful)
        error: Error message (if failed)
        start_time: When execution started
        end_time: When execution ended
        duration_ms: Execution duration in milliseconds
    """
    
    step_id: int
    tool_name: str
    status: ExecutionStatus
    output: Any = None
    error: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_ms: int = 0
    
    def __repr__(self) -> str:
        """String representation."""
        if self.status == ExecutionStatus.COMPLETED:
            return f"StepResult({self.step_id}, {self.status.value}, {self.duration_ms}ms)"
        elif self.status == ExecutionStatus.FAILED:
            return f"StepResult({self.step_id}, FAILED: {self.error})"
        else:
            return f"StepResult({self.step_id}, {self.status.value})"


@dataclass
class ExecutionResult:
    """
    Result of executing a complete query plan.
    
    Attributes:
        status: Overall execution status
        step_results: Results for each step
        final_output: Final result from last step
        error: Error message (if failed)
        total_duration_ms: Total execution time
        steps_completed: Number of completed steps
        steps_failed: Number of failed steps
        parallel_metrics: Parallel execution metrics (if enabled)
    """
    
    status: ExecutionStatus
    step_results: List[StepResult] = field(default_factory=list)
    final_output: Any = None
    error: Optional[str] = None
    total_duration_ms: int = 0
    steps_completed: int = 0
    steps_failed: int = 0
    parallel_metrics: Optional[Dict[str, Any]] = None
    
    def __repr__(self) -> str:
        """String representation."""
        if self.status == ExecutionStatus.COMPLETED:
            return f"ExecutionResult(✓ {self.steps_completed} steps, {self.total_duration_ms}ms)"
        elif self.status == ExecutionStatus.FAILED:
            return f"ExecutionResult(✗ {self.steps_failed} failed, {self.error})"
        else:
            return f"ExecutionResult({self.status.value})"


class ToolRegistry:
    """
    Registry of available tools that can be executed.
    
    Maps tool names to callable functions.
    Supports dependency injection for better testability.
    """
    
    def __init__(self, use_real_tools: bool = False, tool_loader: Optional[Callable] = None):
        """
        Initialize registry.
        
        Args:
            use_real_tools: If True, register real tool implementations.
                          If False, use placeholder tools for testing.
            tool_loader: Optional callable that registers tools (for dependency injection).
                        Function signature: tool_loader(registry: ToolRegistry) -> None
        """
        self._tools: Dict[str, Callable] = {}
        self._use_real_tools = use_real_tools
        
        # Use dependency injection if provided
        if tool_loader:
            tool_loader(self)
        elif use_real_tools:
            self._load_real_tools()
        else:
            self._register_placeholder_tools()
    
    def register(self, name: str, func: Callable) -> None:
        """
        Register a tool.
        
        Args:
            name: Tool name
            func: Callable function
        """
        self._tools[name] = func
    
    def get(self, name: str) -> Optional[Callable]:
        """
        Get a tool by name.
        
        Args:
            name: Tool name
            
        Returns:
            Tool function or None if not found
        """
        return self._tools.get(name)
    
    @property
    def tools(self) -> Dict[str, Callable]:
        """
        Get all registered tools.
        
        Returns:
            Dictionary of tool names to functions
        """
        return self._tools
    
    def has(self, name: str) -> bool:
        """
        Check if tool exists.
        
        Args:
            name: Tool name
            
        Returns:
            True if tool exists
        """
        return name in self._tools
    
    def list_tools(self) -> List[str]:
        """
        Get list of registered tool names.
        
        Returns:
            List of tool names
        """
        return list(self._tools.keys())
    
    def _load_real_tools(self) -> None:
        """
        Load real tool implementations with proper error handling.
        
        Falls back to placeholder tools if real tools cannot be loaded.
        """
        try:
            from chemagent.tools.tool_implementations import register_real_tools
            register_real_tools(self)
            logger.info("Loaded real tool implementations")
        except ImportError as e:
            logger.warning("Could not load real tools: %s", str(e))
            logger.info("Falling back to placeholder tools")
            self._register_placeholder_tools()
        except Exception as e:
            logger.error("Error loading real tools: %s", str(e), exc_info=True)
            logger.info("Falling back to placeholder tools")
            self._register_placeholder_tools()
    
    def _register_placeholder_tools(self) -> None:
        """Register placeholder tools for testing."""
        # ChEMBL tools
        self.register("chembl_search_by_name", self._placeholder_tool)
        self.register("chembl_get_compound", self._placeholder_tool)
        self.register("chembl_similarity_search", self._placeholder_tool)
        self.register("chembl_substructure_search", self._placeholder_tool)
        self.register("chembl_get_activities", self._placeholder_tool)
        
        # RDKit tools
        self.register("rdkit_standardize_smiles", self._placeholder_tool)
        self.register("rdkit_calc_properties", self._placeholder_tool)
        self.register("rdkit_calc_lipinski", self._placeholder_tool)
        self.register("rdkit_convert_format", self._placeholder_tool)
        self.register("rdkit_extract_scaffold", self._placeholder_tool)
        
        # UniProt tools
        self.register("uniprot_get_protein", self._placeholder_tool)
        self.register("uniprot_search", self._placeholder_tool)
        
        # Utility tools
        self.register("filter_by_properties", self._placeholder_tool)
    
    def _placeholder_tool(self, **kwargs) -> Dict[str, Any]:
        """
        Placeholder tool for testing.
        
        Returns dummy data with the same structure as real tools.
        """
        return {
            "status": "success",
            "data": kwargs,
            "message": "Placeholder result"
        }


class QueryExecutor:
    """
    Executes query plans step by step.
    
    Handles dependency resolution, variable substitution,
    error handling, and result aggregation.
    
    Example:
        >>> executor = QueryExecutor()
        >>> plan = planner.plan(intent)
        >>> result = executor.execute(plan)
        >>> result.status
        <ExecutionStatus.COMPLETED: 'completed'>
    """
    
    def __init__(
        self,
        tool_registry: Optional[ToolRegistry] = None,
        use_real_tools: bool = False,
        enable_parallel: bool = True,
        max_workers: int = 4
    ):
        """
        Initialize executor.
        
        Args:
            tool_registry: Registry of available tools. If None, creates default.
            use_real_tools: If True and no registry provided, use real tool implementations.
            enable_parallel: Enable parallel execution of independent steps (default: True)
            max_workers: Maximum number of parallel workers (default: 4)
        """
        if tool_registry is None:
            self.registry = ToolRegistry(use_real_tools=use_real_tools)
        else:
            self.registry = tool_registry
        self._execution_context: Dict[str, Any] = {}
        self.enable_parallel = enable_parallel
        self.parallel_executor = ParallelExecutor(max_workers=max_workers) if enable_parallel else None
        self.metrics = ExecutionMetrics()
    
    def execute(self, plan: QueryPlan) -> ExecutionResult:
        """
        Execute a query plan.
        
        Args:
            plan: Query plan to execute
            
        Returns:
            Execution result with outputs and status
            
        Example:
            >>> result = executor.execute(plan)
            >>> if result.status == ExecutionStatus.COMPLETED:
            ...     print(result.final_output)
        """
        self._execution_context = {}  # Reset context
        self.metrics = ExecutionMetrics()  # Reset metrics
        step_results = []
        start_time = datetime.now()
        
        try:
            # Get parallel execution groups
            groups = plan.get_parallel_groups()
            self.metrics.total_steps = len(plan.steps)
            self.metrics.parallel_groups = len(groups)
            
            # Execute each group
            for group in groups:
                group_start = datetime.now()
                
                if self.enable_parallel and len(group) > 1 and self.parallel_executor is not None:
                    # Execute group in parallel
                    self.metrics.steps_parallelized += len(group)
                    group_results = self.parallel_executor.execute_group_parallel(
                        group,
                        self._execute_step,
                        self._execution_context
                    )
                else:
                    # Execute serially
                    group_results = []
                    for step in group:
                        step_result = self._execute_step(step)
                        group_results.append(step_result)
                        
                        # Store output in context
                        if step_result.status == ExecutionStatus.COMPLETED:
                            self._execution_context[step.output_name] = step_result.output
                
                step_results.extend(group_results)
                
                group_end = datetime.now()
                group_time = int((group_end - group_start).total_seconds() * 1000)
                
                # Update metrics
                if len(group) > 1:
                    # Estimate serial time (sum of individual step times)
                    serial_time = sum(r.duration_ms for r in group_results)
                    self.metrics.serial_time_ms += serial_time
                    self.metrics.parallel_time_ms += group_time
                else:
                    # Single step - same for both
                    self.metrics.serial_time_ms += group_time
                    self.metrics.parallel_time_ms += group_time
                
                # Stop on failure
                failed_result = next((r for r in group_results if r.status == ExecutionStatus.FAILED), None)
                if failed_result:
                    end_time = datetime.now()
                    duration = int((end_time - start_time).total_seconds() * 1000)
                    
                    return ExecutionResult(
                        status=ExecutionStatus.FAILED,
                        step_results=step_results,
                        error=f"Step {failed_result.step_id} failed: {failed_result.error}",
                        total_duration_ms=duration,
                        steps_completed=sum(1 for r in step_results if r.status == ExecutionStatus.COMPLETED),
                        steps_failed=sum(1 for r in step_results if r.status == ExecutionStatus.FAILED),
                        parallel_metrics=self.metrics.to_dict() if self.enable_parallel else None
                    )
            
            # All steps completed successfully
            end_time = datetime.now()
            duration = int((end_time - start_time).total_seconds() * 1000)
            
            # Get final output from last step
            final_output = step_results[-1].output if step_results else None
            
            return ExecutionResult(
                status=ExecutionStatus.COMPLETED,
                step_results=step_results,
                final_output=final_output,
                total_duration_ms=duration,
                steps_completed=len(step_results),
                steps_failed=0,
                parallel_metrics=self.metrics.to_dict() if self.enable_parallel else None
            )
        
        except Exception as e:
            # Unexpected error
            end_time = datetime.now()
            duration = int((end_time - start_time).total_seconds() * 1000)
            
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                step_results=step_results,
                error=f"Execution error: {str(e)}",
                total_duration_ms=duration,
                steps_completed=sum(1 for r in step_results if r.status == ExecutionStatus.COMPLETED),
                steps_failed=len(step_results) - sum(1 for r in step_results if r.status == ExecutionStatus.COMPLETED)
            )
    
    def _execute_step(self, step: PlanStep) -> StepResult:
        """
        Execute a single step.
        
        Args:
            step: Step to execute
            
        Returns:
            Step result
        """
        start_time = datetime.now()
        
        try:
            # Resolve variable references in arguments
            resolved_args = self._resolve_variables(step.args)
            
            # Get tool
            tool = self.registry.get(step.tool_name)
            if not tool:
                return StepResult(
                    step_id=step.step_id,
                    tool_name=step.tool_name,
                    status=ExecutionStatus.FAILED,
                    error=f"Tool not found: {step.tool_name}",
                    start_time=start_time,
                    end_time=datetime.now()
                )
            
            # Execute tool
            output = tool(**resolved_args)
            
            end_time = datetime.now()
            duration = int((end_time - start_time).total_seconds() * 1000)
            
            return StepResult(
                step_id=step.step_id,
                tool_name=step.tool_name,
                status=ExecutionStatus.COMPLETED,
                output=output,
                start_time=start_time,
                end_time=end_time,
                duration_ms=duration
            )
        
        except Exception as e:
            end_time = datetime.now()
            duration = int((end_time - start_time).total_seconds() * 1000)
            
            return StepResult(
                step_id=step.step_id,
                tool_name=step.tool_name,
                status=ExecutionStatus.FAILED,
                error=str(e),
                start_time=start_time,
                end_time=end_time,
                duration_ms=duration
            )
    
    def _resolve_variables(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Resolve variable references in arguments.
        
        Variables are in the format: $output_name.field
        
        Args:
            args: Arguments with potential variable references
            
        Returns:
            Arguments with variables resolved
            
        Example:
            >>> args = {"smiles": "$compound_data.smiles"}
            >>> resolved = executor._resolve_variables(args)
            >>> resolved
            {"smiles": "CC(=O)O"}
        """
        resolved = {}
        
        for key, value in args.items():
            if isinstance(value, str) and value.startswith("$"):
                # Variable reference
                resolved[key] = self._resolve_variable(value)
            else:
                resolved[key] = value
        
        return resolved
    
    def _resolve_variable(self, var_ref: str) -> Any:
        """
        Resolve a variable reference.
        
        Args:
            var_ref: Variable reference (e.g., "$compound_data.smiles")
            
        Returns:
            Resolved value
            
        Raises:
            ValueError: If variable not found
        """
        # Parse variable reference
        match = re.match(r"\$([^.]+)(?:\.(.+))?", var_ref)
        if not match:
            raise ValueError(f"Invalid variable reference: {var_ref}")
        
        var_name = match.group(1)
        field_path = match.group(2)
        
        # Get base value from context
        if var_name not in self._execution_context:
            raise ValueError(f"Variable not found: {var_name}")
        
        value = self._execution_context[var_name]
        
        # Navigate field path if present
        if field_path:
            for field in field_path.split("."):
                if isinstance(value, dict):
                    if field not in value:
                        raise ValueError(f"Field not found: {field} in {var_name}")
                    value = value[field]
                elif hasattr(value, field):
                    value = getattr(value, field)
                else:
                    raise ValueError(f"Cannot access field: {field} in {var_name}")
        
        return value
    
    def get_context(self) -> Dict[str, Any]:
        """
        Get current execution context.
        
        Returns:
            Execution context with all stored outputs
        """
        return self._execution_context.copy()
    
    def clear_context(self) -> None:
        """Clear execution context."""
        self._execution_context = {}
