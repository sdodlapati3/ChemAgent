"""
Parallel execution support for QueryExecutor.

Provides concurrent execution of independent query plan steps
using ThreadPoolExecutor for I/O-bound operations.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed, Future
from typing import List, Dict, Any, Optional, TYPE_CHECKING
import time
from datetime import datetime

from chemagent.core.query_planner import QueryPlan, PlanStep

if TYPE_CHECKING:
    from chemagent.core.executor import ExecutionStatus, StepResult


class ParallelExecutor:
    """
    Parallel execution engine for query plans.
    
    Executes independent steps concurrently using a thread pool,
    providing significant speedup for multi-step queries with
    independent operations.
    """
    
    def __init__(self, max_workers: int = 4):
        """
        Initialize parallel executor.
        
        Args:
            max_workers: Maximum number of concurrent workers (default: 4)
        """
        self.max_workers = max_workers
    
    def execute_group_parallel(
        self,
        steps: List[PlanStep],
        executor_func,
        context: Dict[str, Any]
    ) -> List["StepResult"]:
        """
        Execute a group of independent steps in parallel.
        
        Args:
            steps: List of steps to execute (should have no dependencies on each other)
            executor_func: Function to execute a single step (from QueryExecutor)
            context: Shared execution context
            
        Returns:
            List of step results in original order
        """
        # Import here to avoid circular dependency
        from chemagent.core.executor import ExecutionStatus, StepResult
        
        if len(steps) == 1:
            # Single step - no need for parallelism
            return [executor_func(steps[0])]
        
        results = {}
        
        with ThreadPoolExecutor(max_workers=min(self.max_workers, len(steps))) as pool:
            # Submit all steps
            future_to_step = {
                pool.submit(executor_func, step): step
                for step in steps
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_step):
                step = future_to_step[future]
                try:
                    result = future.result()
                    results[step.step_id] = result
                    
                    # Update context immediately for dependent steps
                    if result.status == ExecutionStatus.COMPLETED:
                        context[step.output_name] = result.output
                        
                except Exception as e:
                    # Create error result
                    results[step.step_id] = StepResult(
                        step_id=step.step_id,
                        tool_name=step.tool_name,
                        status=ExecutionStatus.FAILED,
                        error=f"Parallel execution error: {str(e)}",
                        duration_ms=0
                    )
        
        # Return results in original step order
        return [results[step.step_id] for step in steps]
    
    def get_speedup_estimate(self, groups: List[List[PlanStep]]) -> float:
        """
        Estimate speedup from parallel execution.
        
        Args:
            groups: Parallel execution groups
            
        Returns:
            Estimated speedup factor (e.g., 2.5x)
        """
        if not groups:
            return 1.0
        
        # Count total steps
        total_steps = sum(len(group) for group in groups)
        
        # Count groups with multiple steps (benefit from parallelism)
        parallel_groups = sum(1 for group in groups if len(group) > 1)
        parallel_steps = sum(len(group) for group in groups if len(group) > 1)
        
        if parallel_steps == 0:
            return 1.0
        
        # Estimate speedup: serial steps + parallel groups
        # (assuming perfect parallelism within groups)
        serial_steps = total_steps - parallel_steps
        estimated_time = serial_steps + parallel_groups
        
        speedup = total_steps / estimated_time if estimated_time > 0 else 1.0
        return round(speedup, 2)


class ExecutionMetrics:
    """
    Track execution metrics for performance analysis.
    """
    
    def __init__(self):
        self.serial_time_ms = 0
        self.parallel_time_ms = 0
        self.steps_parallelized = 0
        self.total_steps = 0
        self.parallel_groups = 0
    
    @property
    def speedup(self) -> float:
        """Calculate actual speedup achieved"""
        if self.serial_time_ms == 0:
            return 1.0
        return self.serial_time_ms / self.parallel_time_ms if self.parallel_time_ms > 0 else 1.0
    
    @property
    def parallelization_ratio(self) -> float:
        """Ratio of steps that were parallelized"""
        if self.total_steps == 0:
            return 0.0
        return self.steps_parallelized / self.total_steps
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary"""
        return {
            "serial_time_ms": self.serial_time_ms,
            "parallel_time_ms": self.parallel_time_ms,
            "speedup": f"{self.speedup:.2f}x",
            "steps_parallelized": self.steps_parallelized,
            "total_steps": self.total_steps,
            "parallel_groups": self.parallel_groups,
            "parallelization_ratio": f"{self.parallelization_ratio:.1%}"
        }
    
    def __str__(self) -> str:
        """String representation"""
        if self.parallel_time_ms == 0:
            return "No parallel execution"
        
        return (
            f"Parallel execution: {self.speedup:.2f}x speedup "
            f"({self.parallel_time_ms}ms vs {self.serial_time_ms}ms), "
            f"{self.steps_parallelized}/{self.total_steps} steps parallelized"
        )
