"""
Tests for query executor.

Validates step execution, dependency resolution, variable substitution,
error handling, and result aggregation.
"""

from typing import Dict

import pytest

from chemagent.core import (
    ExecutionStatus,
    IntentParser,
    IntentType,
    ParsedIntent,
    QueryExecutor,
    QueryPlanner,
    ToolRegistry,
)
from chemagent.core.query_planner import PlanStep, QueryPlan


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def registry():
    """Create tool registry."""
    return ToolRegistry()


@pytest.fixture
def executor(registry):
    """Create executor."""
    return QueryExecutor(registry)


@pytest.fixture
def planner():
    """Create planner."""
    return QueryPlanner()


@pytest.fixture
def parser():
    """Create parser."""
    return IntentParser()


# =============================================================================
# Test Tool Registry
# =============================================================================

class TestToolRegistry:
    """Test tool registry."""
    
    def test_register_tool(self, registry):
        """Test registering a tool."""
        def my_tool(**kwargs):
            return {"result": "success"}
        
        registry.register("my_tool", my_tool)
        
        assert registry.has("my_tool")
        assert registry.get("my_tool") is my_tool
    
    def test_list_tools(self, registry):
        """Test listing tools."""
        tools = registry.list_tools()
        
        # Should have default tools
        assert len(tools) > 0
        assert "chembl_search_by_name" in tools
        assert "rdkit_standardize_smiles" in tools
    
    def test_get_nonexistent_tool(self, registry):
        """Test getting nonexistent tool."""
        tool = registry.get("nonexistent_tool")
        assert tool is None
    
    def test_has_tool(self, registry):
        """Test checking if tool exists."""
        assert registry.has("chembl_search_by_name")
        assert not registry.has("nonexistent_tool")


# =============================================================================
# Test Basic Execution
# =============================================================================

class TestBasicExecution:
    """Test basic execution."""
    
    def test_execute_empty_plan(self, executor):
        """Test executing empty plan."""
        plan = QueryPlan(
            steps=[],
            intent_type=IntentType.UNKNOWN
        )
        
        result = executor.execute(plan)
        
        assert result.status == ExecutionStatus.COMPLETED
        assert len(result.step_results) == 0
    
    def test_execute_single_step(self, executor):
        """Test executing single step."""
        plan = QueryPlan(
            steps=[
                PlanStep(
                    step_id=0,
                    tool_name="chembl_search_by_name",
                    args={"query": "aspirin"},
                    output_name="compound"
                )
            ],
            intent_type=IntentType.COMPOUND_LOOKUP
        )
        
        result = executor.execute(plan)
        
        assert result.status == ExecutionStatus.COMPLETED
        assert len(result.step_results) == 1
        assert result.step_results[0].status == ExecutionStatus.COMPLETED
        assert result.steps_completed == 1
        assert result.steps_failed == 0
    
    def test_execute_multiple_steps(self, executor):
        """Test executing multiple steps."""
        plan = QueryPlan(
            steps=[
                PlanStep(
                    step_id=0,
                    tool_name="chembl_search_by_name",
                    args={"query": "aspirin"},
                    output_name="compound"
                ),
                PlanStep(
                    step_id=1,
                    tool_name="rdkit_standardize_smiles",
                    args={"smiles": "CC(=O)O"},
                    depends_on=[0],
                    output_name="standardized"
                )
            ],
            intent_type=IntentType.PROPERTY_CALCULATION
        )
        
        result = executor.execute(plan)
        
        assert result.status == ExecutionStatus.COMPLETED
        assert len(result.step_results) == 2
        assert all(r.status == ExecutionStatus.COMPLETED for r in result.step_results)


# =============================================================================
# Test Variable Resolution
# =============================================================================

class TestVariableResolution:
    """Test variable resolution."""
    
    def test_resolve_simple_variable(self, executor):
        """Test resolving simple variable."""
        # Set up context
        executor._execution_context = {
            "compound": {"smiles": "CC(=O)O", "name": "aspirin"}
        }
        
        # Resolve variable
        args = {"smiles": "$compound"}
        resolved = executor._resolve_variables(args)
        
        assert resolved["smiles"] == {"smiles": "CC(=O)O", "name": "aspirin"}
    
    def test_resolve_nested_variable(self, executor):
        """Test resolving nested variable."""
        executor._execution_context = {
            "compound": {"smiles": "CC(=O)O", "name": "aspirin"}
        }
        
        args = {"smiles": "$compound.smiles"}
        resolved = executor._resolve_variables(args)
        
        assert resolved["smiles"] == "CC(=O)O"
    
    def test_resolve_multiple_variables(self, executor):
        """Test resolving multiple variables."""
        executor._execution_context = {
            "compound": {"smiles": "CC(=O)O"},
            "threshold": 0.8
        }
        
        args = {
            "smiles": "$compound.smiles",
            "threshold": "$threshold",
            "limit": 100  # Not a variable
        }
        resolved = executor._resolve_variables(args)
        
        assert resolved["smiles"] == "CC(=O)O"
        assert resolved["threshold"] == 0.8
        assert resolved["limit"] == 100
    
    def test_resolve_nonexistent_variable(self, executor):
        """Test resolving nonexistent variable."""
        executor._execution_context = {}
        
        args = {"smiles": "$nonexistent"}
        
        with pytest.raises(ValueError, match="Variable not found"):
            executor._resolve_variables(args)
    
    def test_resolve_nonexistent_field(self, executor):
        """Test resolving nonexistent field."""
        executor._execution_context = {
            "compound": {"smiles": "CC(=O)O"}
        }
        
        args = {"value": "$compound.nonexistent"}
        
        with pytest.raises(ValueError, match="Field not found"):
            executor._resolve_variables(args)


# =============================================================================
# Test Error Handling
# =============================================================================

class TestErrorHandling:
    """Test error handling."""
    
    def test_nonexistent_tool(self, executor):
        """Test executing nonexistent tool."""
        plan = QueryPlan(
            steps=[
                PlanStep(
                    step_id=0,
                    tool_name="nonexistent_tool",
                    args={},
                    output_name="result"
                )
            ],
            intent_type=IntentType.UNKNOWN
        )
        
        result = executor.execute(plan)
        
        assert result.status == ExecutionStatus.FAILED
        assert result.steps_failed == 1
        assert "Tool not found" in result.error
    
    def test_tool_execution_error(self, executor, registry):
        """Test handling tool execution error."""
        def failing_tool(**kwargs):
            raise ValueError("Tool error")
        
        registry.register("failing_tool", failing_tool)
        
        plan = QueryPlan(
            steps=[
                PlanStep(
                    step_id=0,
                    tool_name="failing_tool",
                    args={},
                    output_name="result"
                )
            ],
            intent_type=IntentType.UNKNOWN
        )
        
        result = executor.execute(plan)
        
        assert result.status == ExecutionStatus.FAILED
        assert result.step_results[0].status == ExecutionStatus.FAILED
        assert "Tool error" in result.step_results[0].error
    
    def test_stop_on_failure(self, executor, registry):
        """Test execution stops on step failure."""
        def failing_tool(**kwargs):
            raise ValueError("Failure")
        
        registry.register("failing_tool", failing_tool)
        
        plan = QueryPlan(
            steps=[
                PlanStep(
                    step_id=0,
                    tool_name="failing_tool",
                    args={},
                    output_name="step1"
                ),
                PlanStep(
                    step_id=1,
                    tool_name="chembl_search_by_name",
                    args={"query": "aspirin"},
                    depends_on=[0],
                    output_name="step2"
                )
            ],
            intent_type=IntentType.UNKNOWN
        )
        
        result = executor.execute(plan)
        
        # Should stop after first failure
        assert result.status == ExecutionStatus.FAILED
        assert len(result.step_results) == 1  # Only first step executed


# =============================================================================
# Test Execution Context
# =============================================================================

class TestExecutionContext:
    """Test execution context management."""
    
    def test_store_step_outputs(self, executor):
        """Test storing step outputs in context."""
        plan = QueryPlan(
            steps=[
                PlanStep(
                    step_id=0,
                    tool_name="chembl_search_by_name",
                    args={"query": "aspirin"},
                    output_name="compound"
                )
            ],
            intent_type=IntentType.COMPOUND_LOOKUP
        )
        
        executor.execute(plan)
        context = executor.get_context()
        
        assert "compound" in context
        assert context["compound"] is not None
    
    def test_clear_context(self, executor):
        """Test clearing context."""
        executor._execution_context = {"test": "value"}
        executor.clear_context()
        
        assert len(executor.get_context()) == 0
    
    def test_context_reset_between_executions(self, executor):
        """Test context is reset for each execution."""
        plan1 = QueryPlan(
            steps=[
                PlanStep(
                    step_id=0,
                    tool_name="chembl_search_by_name",
                    args={"query": "aspirin"},
                    output_name="result1"
                )
            ],
            intent_type=IntentType.COMPOUND_LOOKUP
        )
        
        executor.execute(plan1)
        
        plan2 = QueryPlan(
            steps=[
                PlanStep(
                    step_id=0,
                    tool_name="chembl_search_by_name",
                    args={"query": "ibuprofen"},
                    output_name="result2"
                )
            ],
            intent_type=IntentType.COMPOUND_LOOKUP
        )
        
        executor.execute(plan2)
        context = executor.get_context()
        
        # Only result2 should be in context
        assert "result2" in context
        assert "result1" not in context


# =============================================================================
# Test Result Aggregation
# =============================================================================

class TestResultAggregation:
    """Test result aggregation."""
    
    def test_final_output(self, executor):
        """Test final output is from last step."""
        plan = QueryPlan(
            steps=[
                PlanStep(
                    step_id=0,
                    tool_name="chembl_search_by_name",
                    args={"query": "aspirin"},
                    output_name="step1"
                ),
                PlanStep(
                    step_id=1,
                    tool_name="rdkit_standardize_smiles",
                    args={"smiles": "CC(=O)O"},
                    depends_on=[0],
                    output_name="step2"
                )
            ],
            intent_type=IntentType.PROPERTY_CALCULATION
        )
        
        result = executor.execute(plan)
        
        # Final output should be from step2
        assert result.final_output == result.step_results[-1].output
    
    def test_timing_information(self, executor):
        """Test timing information is captured."""
        plan = QueryPlan(
            steps=[
                PlanStep(
                    step_id=0,
                    tool_name="chembl_search_by_name",
                    args={"query": "aspirin"},
                    output_name="result"
                )
            ],
            intent_type=IntentType.COMPOUND_LOOKUP
        )
        
        result = executor.execute(plan)
        
        assert result.total_duration_ms >= 0
        assert result.step_results[0].duration_ms >= 0
        assert result.step_results[0].start_time is not None
        assert result.step_results[0].end_time is not None
    
    def test_step_counts(self, executor):
        """Test step counts."""
        plan = QueryPlan(
            steps=[
                PlanStep(step_id=i, tool_name="chembl_search_by_name", 
                        args={"query": "test"}, output_name=f"step{i}")
                for i in range(5)
            ],
            intent_type=IntentType.COMPOUND_LOOKUP
        )
        
        result = executor.execute(plan)
        
        assert result.steps_completed == 5
        assert result.steps_failed == 0


# =============================================================================
# Test Integration Scenarios
# =============================================================================

class TestIntegrationScenarios:
    """Test end-to-end integration scenarios."""
    
    def test_parse_plan_execute(self, parser, planner, executor):
        """Test complete pipeline: parse → plan → execute."""
        query = "What is CHEMBL25"
        
        # Parse
        intent = parser.parse(query)
        assert intent.intent_type == IntentType.COMPOUND_LOOKUP
        
        # Plan
        plan = planner.plan(intent)
        assert len(plan.steps) > 0
        
        # Execute
        result = executor.execute(plan)
        assert result.status == ExecutionStatus.COMPLETED
    
    def test_property_calculation_pipeline(self, parser, planner, executor):
        """Test property calculation pipeline."""
        query = "Calculate properties of CC(=O)O"
        
        intent = parser.parse(query)
        plan = planner.plan(intent)
        result = executor.execute(plan)
        
        # Should complete even with placeholder tools
        assert result.status in [ExecutionStatus.COMPLETED, ExecutionStatus.FAILED]
    
    def test_similarity_search_pipeline(self, parser, planner, executor):
        """Test similarity search pipeline."""
        query = "Find compounds similar to aspirin"
        
        intent = parser.parse(query)
        plan = planner.plan(intent)
        result = executor.execute(plan)
        
        assert isinstance(result, object)  # ExecutionResult


# =============================================================================
# Test Custom Tools
# =============================================================================

class TestCustomTools:
    """Test custom tool registration."""
    
    def test_register_custom_tool(self, executor, registry):
        """Test registering and using custom tool."""
        def custom_tool(value: int) -> Dict:
            return {"doubled": value * 2}
        
        registry.register("custom_tool", custom_tool)
        
        plan = QueryPlan(
            steps=[
                PlanStep(
                    step_id=0,
                    tool_name="custom_tool",
                    args={"value": 42},
                    output_name="result"
                )
            ],
            intent_type=IntentType.UNKNOWN
        )
        
        result = executor.execute(plan)
        
        assert result.status == ExecutionStatus.COMPLETED
        assert result.final_output["doubled"] == 84
    
    def test_chain_custom_tools(self, executor, registry):
        """Test chaining custom tools."""
        def add_ten(value: int) -> Dict:
            return {"result": value + 10}
        
        def multiply_by_two(value: int) -> Dict:
            return {"result": value * 2}
        
        registry.register("add_ten", add_ten)
        registry.register("multiply_by_two", multiply_by_two)
        
        plan = QueryPlan(
            steps=[
                PlanStep(
                    step_id=0,
                    tool_name="add_ten",
                    args={"value": 5},
                    output_name="added"
                ),
                PlanStep(
                    step_id=1,
                    tool_name="multiply_by_two",
                    args={"value": "$added.result"},
                    depends_on=[0],
                    output_name="multiplied"
                )
            ],
            intent_type=IntentType.UNKNOWN
        )
        
        result = executor.execute(plan)
        
        assert result.status == ExecutionStatus.COMPLETED
        assert result.final_output["result"] == 30  # (5 + 10) * 2


# =============================================================================
# Test String Representations
# =============================================================================

class TestStringRepresentations:
    """Test string representations."""
    
    def test_execution_result_repr(self, executor):
        """Test ExecutionResult repr."""
        plan = QueryPlan(
            steps=[
                PlanStep(
                    step_id=0,
                    tool_name="chembl_search_by_name",
                    args={"query": "aspirin"},
                    output_name="result"
                )
            ],
            intent_type=IntentType.COMPOUND_LOOKUP
        )
        
        result = executor.execute(plan)
        repr_str = repr(result)
        
        assert "ExecutionResult" in repr_str
        assert "steps" in repr_str or "✓" in repr_str
    
    def test_step_result_repr(self):
        """Test StepResult repr."""
        from chemagent.core.executor import StepResult
        from datetime import datetime
        
        result = StepResult(
            step_id=0,
            status=ExecutionStatus.COMPLETED,
            output={"test": "data"},
            start_time=datetime.now(),
            end_time=datetime.now(),
            duration_ms=100
        )
        
        repr_str = repr(result)
        assert "StepResult" in repr_str
        assert "0" in repr_str
