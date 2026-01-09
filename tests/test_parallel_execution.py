"""
Comprehensive tests for parallel execution functionality.

Tests parallel execution engine, metrics tracking, and integration
across different query types and execution patterns.
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock

from chemagent.core.parallel import ParallelExecutor, ExecutionMetrics
from chemagent.core.executor import QueryExecutor, ExecutionStatus, StepResult, ToolRegistry
from chemagent.core.query_planner import QueryPlan, PlanStep
from chemagent.core.intent_parser import IntentType, ParsedIntent


class TestParallelExecutor:
    """Test ParallelExecutor functionality"""
    
    def test_single_step_no_parallelism(self):
        """Single step should not use parallelism"""
        executor = ParallelExecutor(max_workers=4)
        
        step = PlanStep(
            step_id=0,
            tool_name="test_tool",
            args={},
            output_name="result"
        )
        
        def mock_executor(step):
            return StepResult(
                step_id=0,
                tool_name="test_tool",
                status=ExecutionStatus.COMPLETED,
                output={"value": 42},
                duration_ms=10
            )
        
        results = executor.execute_group_parallel([step], mock_executor, {})
        
        assert len(results) == 1
        assert results[0].status == ExecutionStatus.COMPLETED
        assert results[0].output["value"] == 42
    
    def test_multiple_steps_parallel(self):
        """Multiple independent steps should execute in parallel"""
        executor = ParallelExecutor(max_workers=4)
        
        steps = [
            PlanStep(
                step_id=i,
                tool_name=f"tool_{i}",
                args={},
                output_name=f"result_{i}"
            )
            for i in range(3)
        ]
        
        call_times = []
        
        def mock_executor(step):
            call_times.append(time.time())
            time.sleep(0.1)  # Simulate I/O
            return StepResult(
                step_id=step.step_id,
                tool_name=step.tool_name,
                status=ExecutionStatus.COMPLETED,
                output={"value": step.step_id},
                duration_ms=100
            )
        
        start = time.time()
        results = executor.execute_group_parallel(steps, mock_executor, {})
        duration = time.time() - start
        
        # Should complete in ~0.1s (parallel) not ~0.3s (serial)
        assert duration < 0.2, f"Expected parallel execution, took {duration}s"
        assert len(results) == 3
        assert all(r.status == ExecutionStatus.COMPLETED for r in results)
    
    def test_parallel_context_updates(self):
        """Context should be updated immediately for each completed step"""
        executor = ParallelExecutor(max_workers=4)
        context = {}
        
        steps = [
            PlanStep(
                step_id=i,
                tool_name=f"tool_{i}",
                args={},
                output_name=f"result_{i}"
            )
            for i in range(3)
        ]
        
        def mock_executor(step):
            return StepResult(
                step_id=step.step_id,
                tool_name=step.tool_name,
                status=ExecutionStatus.COMPLETED,
                output={"value": step.step_id},
                duration_ms=10
            )
        
        results = executor.execute_group_parallel(steps, mock_executor, context)
        
        # All results should be in context
        assert "result_0" in context
        assert "result_1" in context
        assert "result_2" in context
    
    def test_error_handling_in_parallel(self):
        """Errors in one step shouldn't crash other parallel steps"""
        executor = ParallelExecutor(max_workers=4)
        
        steps = [
            PlanStep(
                step_id=i,
                tool_name=f"tool_{i}",
                args={},
                output_name=f"result_{i}"
            )
            for i in range(3)
        ]
        
        def mock_executor(step):
            if step.step_id == 1:
                return StepResult(
                    step_id=step.step_id,
                    tool_name=step.tool_name,
                    status=ExecutionStatus.FAILED,
                    output=None,
                    error="Simulated error",
                    duration_ms=10
                )
            return StepResult(
                step_id=step.step_id,
                tool_name=step.tool_name,
                status=ExecutionStatus.COMPLETED,
                output={"value": step.step_id},
                duration_ms=10
            )
        
        results = executor.execute_group_parallel(steps, mock_executor, {})
        
        assert len(results) == 3
        assert results[0].status == ExecutionStatus.COMPLETED
        assert results[1].status == ExecutionStatus.FAILED
        assert results[2].status == ExecutionStatus.COMPLETED


class TestExecutionMetrics:
    """Test ExecutionMetrics tracking"""
    
    def test_metrics_initialization(self):
        """Metrics should initialize to zero"""
        metrics = ExecutionMetrics()
        
        assert metrics.serial_time_ms == 0
        assert metrics.parallel_time_ms == 0
        assert metrics.steps_parallelized == 0
        assert metrics.total_steps == 0
        assert metrics.parallel_groups == 0
    
    def test_speedup_calculation(self):
        """Speedup should be calculated correctly"""
        metrics = ExecutionMetrics()
        
        # No time elapsed
        assert metrics.speedup == 1.0
        
        # Serial faster (shouldn't happen, but handle it)
        metrics.serial_time_ms = 100
        metrics.parallel_time_ms = 0
        assert metrics.speedup == 1.0
        
        # Normal case: parallel faster
        metrics.parallel_time_ms = 50
        assert metrics.speedup == 2.0
        
        # 3x speedup
        metrics.serial_time_ms = 300
        metrics.parallel_time_ms = 100
        assert metrics.speedup == 3.0
    
    def test_parallelization_ratio(self):
        """Parallelization ratio should be calculated correctly"""
        metrics = ExecutionMetrics()
        
        # No steps
        assert metrics.parallelization_ratio == 0.0
        
        # All steps parallelized
        metrics.total_steps = 10
        metrics.steps_parallelized = 10
        assert metrics.parallelization_ratio == 1.0
        
        # Half parallelized
        metrics.steps_parallelized = 5
        assert metrics.parallelization_ratio == 0.5
        
        # None parallelized
        metrics.steps_parallelized = 0
        assert metrics.parallelization_ratio == 0.0
    
    def test_to_dict_format(self):
        """to_dict should return properly formatted metrics"""
        metrics = ExecutionMetrics()
        metrics.serial_time_ms = 300
        metrics.parallel_time_ms = 100
        metrics.steps_parallelized = 6
        metrics.total_steps = 10
        metrics.parallel_groups = 3
        
        result = metrics.to_dict()
        
        assert result["serial_time_ms"] == 300
        assert result["parallel_time_ms"] == 100
        assert result["speedup"] == "3.00x"
        assert result["steps_parallelized"] == 6
        assert result["total_steps"] == 10
        assert result["parallel_groups"] == 3
        assert result["parallelization_ratio"] == "60.0%"


class TestQueryExecutorParallel:
    """Test QueryExecutor with parallel execution"""
    
    def test_parallel_enabled_by_default(self):
        """Parallel execution should be enabled by default"""
        executor = QueryExecutor(use_real_tools=False)
        
        assert executor.enable_parallel is True
        assert executor.parallel_executor is not None
    
    def test_parallel_disabled(self):
        """Can disable parallel execution"""
        executor = QueryExecutor(use_real_tools=False, enable_parallel=False)
        
        assert executor.enable_parallel is False
    
    def test_custom_max_workers(self):
        """Can customize max workers"""
        executor = QueryExecutor(use_real_tools=False, max_workers=8)
        
        assert executor.parallel_executor.max_workers == 8
    
    def test_single_step_plan(self):
        """Single step plan should complete without parallelism"""
        # Create registry and register mock tool
        registry = ToolRegistry(use_real_tools=False)
        registry.register("test_tool", lambda: {"value": 42})
        
        executor = QueryExecutor(tool_registry=registry)
        
        plan = QueryPlan(
            intent_type=IntentType.COMPOUND_LOOKUP,
            steps=[
                PlanStep(
                    step_id=0,
                    tool_name="test_tool",
                    args={},
                    output_name="result"
                )
            ]
        )
        
        result = executor.execute(plan)
        
        assert result.status == ExecutionStatus.COMPLETED
        assert result.parallel_metrics is not None
        assert result.parallel_metrics["steps_parallelized"] == 0
    
    def test_parallel_metrics_in_result(self):
        """Execution result should include parallel metrics"""
        executor = QueryExecutor(use_real_tools=False, enable_parallel=True)
        
        plan = QueryPlan(
            intent_type=IntentType.COMPOUND_LOOKUP,
            steps=[
                PlanStep(
                    step_id=0,
                    tool_name="test_tool",
                    args={},
                    output_name="result"
                )
            ]
        )
        
        result = executor.execute(plan)
        
        assert result.parallel_metrics is not None
        assert "speedup" in result.parallel_metrics
        assert "steps_parallelized" in result.parallel_metrics
        assert "total_steps" in result.parallel_metrics
        assert "parallel_groups" in result.parallel_metrics
        assert "parallelization_ratio" in result.parallel_metrics
    
    def test_parallel_disabled_no_metrics(self):
        """No parallel metrics when parallel execution is disabled"""
        executor = QueryExecutor(use_real_tools=False, enable_parallel=False)
        
        plan = QueryPlan(
            intent_type=IntentType.COMPOUND_LOOKUP,
            steps=[
                PlanStep(
                    step_id=0,
                    tool_name="test_tool",
                    args={},
                    output_name="result"
                )
            ]
        )
        
        result = executor.execute(plan)
        
        assert result.parallel_metrics is None


class TestParallelExecutionIntegration:
    """Integration tests for parallel execution"""
    
    def test_multiple_independent_groups(self):
        """Plan with multiple independent groups should parallelize each group"""
        # Create registry and register mock tools
        registry = ToolRegistry(use_real_tools=False)
        for i in range(4):
            registry.register(f"tool_{i}", lambda i=i: {"value": i})
        
        executor = QueryExecutor(tool_registry=registry, enable_parallel=True)
        
        # Create plan with 2 groups of 2 steps each
        plan = QueryPlan(
            intent_type=IntentType.PROPERTY_CALCULATION,
            steps=[
                # Group 1: Two independent steps
                PlanStep(
                    step_id=0,
                    tool_name="tool_0",
                    args={},
                    output_name="result_0"
                ),
                PlanStep(
                    step_id=1,
                    tool_name="tool_1",
                    args={},
                    output_name="result_1"
                ),
                # Group 2: Two steps depending on group 1
                PlanStep(
                    step_id=2,
                    tool_name="tool_2",
                    args={},
                    output_name="result_2",
                    depends_on=[0]
                ),
                PlanStep(
                    step_id=3,
                    tool_name="tool_3",
                    args={},
                    output_name="result_3",
                    depends_on=[1]
                )
            ]
        )
        
        result = executor.execute(plan)
        
        assert result.status == ExecutionStatus.COMPLETED
        metrics = result.parallel_metrics
        assert metrics is not None
        assert metrics["parallel_groups"] >= 2
    
    def test_performance_comparison(self):
        """Compare parallel vs serial execution performance"""
        # This is a synthetic test - real performance gains depend on I/O
        
        # Create registry and register mock tools
        registry = ToolRegistry(use_real_tools=False)
        for i in range(3):
            registry.register(f"tool_{i}", lambda i=i: {"value": i})
        
        plan = QueryPlan(
            intent_type=IntentType.PROPERTY_CALCULATION,
            steps=[
                PlanStep(
                    step_id=i,
                    tool_name=f"tool_{i}",
                    args={},
                    output_name=f"result_{i}"
                )
                for i in range(3)
            ]
        )
        
        # Serial execution
        executor_serial = QueryExecutor(tool_registry=registry, enable_parallel=False)
        result_serial = executor_serial.execute(plan)
        
        # Parallel execution (use same registry)
        executor_parallel = QueryExecutor(tool_registry=registry, enable_parallel=True)
        result_parallel = executor_parallel.execute(plan)
        
        # Both should complete successfully
        assert result_serial.status == ExecutionStatus.COMPLETED
        assert result_parallel.status == ExecutionStatus.COMPLETED
        
        # Parallel should have metrics
        assert result_parallel.parallel_metrics is not None
        assert result_serial.parallel_metrics is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
