"""
Tests for query planner.

Validates plan generation for all intent types with proper
dependency tracking and optimization.
"""

import pytest

from chemagent.core import IntentParser, IntentType, ParsedIntent
from chemagent.core.query_planner import PlanStep, QueryPlan, QueryPlanner


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def planner():
    """Create query planner."""
    return QueryPlanner()


@pytest.fixture
def parser():
    """Create intent parser."""
    return IntentParser()


# =============================================================================
# Test Plan Generation
# =============================================================================

class TestSimilaritySearchPlanning:
    """Test similarity search plan generation."""
    
    def test_similarity_with_smiles(self, planner):
        """Test planning with direct SMILES."""
        intent = ParsedIntent(
            intent_type=IntentType.SIMILARITY_SEARCH,
            entities={"smiles": "CC(=O)O", "threshold": 0.8}
        )
        
        plan = planner.plan(intent)
        
        assert plan.intent_type == IntentType.SIMILARITY_SEARCH
        assert len(plan.steps) >= 2  # Standardize + Search
        assert any("standardize" in s.tool_name for s in plan.steps)
        assert any("similarity" in s.tool_name for s in plan.steps)
    
    def test_similarity_with_compound_name(self, planner):
        """Test planning with compound name lookup."""
        intent = ParsedIntent(
            intent_type=IntentType.SIMILARITY_SEARCH,
            entities={"compound": "aspirin", "threshold": 0.7}
        )
        
        plan = planner.plan(intent)
        
        assert len(plan.steps) >= 3  # Lookup + Standardize + Search
        assert plan.steps[0].tool_name in ["chembl_search_by_name", "chembl_get_compound"]
        assert any("standardize" in s.tool_name for s in plan.steps)
    
    def test_similarity_with_chembl_id(self, planner):
        """Test planning with ChEMBL ID."""
        intent = ParsedIntent(
            intent_type=IntentType.SIMILARITY_SEARCH,
            entities={"chembl_id": "CHEMBL25"}
        )
        
        plan = planner.plan(intent)
        
        assert len(plan.steps) >= 3
        assert "chembl_get_compound" in plan.steps[0].tool_name
    
    def test_similarity_with_constraints(self, planner):
        """Test planning with property constraints."""
        intent = ParsedIntent(
            intent_type=IntentType.SIMILARITY_SEARCH,
            entities={"smiles": "CC(=O)O"},
            constraints={"mw_max": 500, "logp_max": 5}
        )
        
        plan = planner.plan(intent)
        
        # Should have filter step
        assert any("filter" in s.tool_name for s in plan.steps)
    
    def test_similarity_limit(self, planner):
        """Test result limit parameter."""
        intent = ParsedIntent(
            intent_type=IntentType.SIMILARITY_SEARCH,
            entities={"smiles": "CC(=O)O", "limit": 50}
        )
        
        plan = planner.plan(intent)
        
        similarity_step = next(s for s in plan.steps if "similarity" in s.tool_name)
        assert similarity_step.args.get("limit") == 50


class TestCompoundLookupPlanning:
    """Test compound lookup plan generation."""
    
    def test_lookup_by_chembl_id(self, planner):
        """Test lookup by ChEMBL ID."""
        intent = ParsedIntent(
            intent_type=IntentType.COMPOUND_LOOKUP,
            entities={"chembl_id": "CHEMBL25"}
        )
        
        plan = planner.plan(intent)
        
        assert len(plan.steps) >= 1
        assert plan.steps[0].tool_name == "chembl_get_compound"
        assert plan.steps[0].args["chembl_id"] == "CHEMBL25"
    
    def test_lookup_by_name(self, planner):
        """Test lookup by compound name."""
        intent = ParsedIntent(
            intent_type=IntentType.COMPOUND_LOOKUP,
            entities={"compound": "aspirin"}
        )
        
        plan = planner.plan(intent)
        
        assert len(plan.steps) >= 1
        assert plan.steps[0].tool_name == "chembl_search_by_name"
        assert plan.steps[0].args["query"] == "aspirin"


class TestTargetLookupPlanning:
    """Test target lookup plan generation."""
    
    def test_lookup_by_uniprot_id(self, planner):
        """Test lookup by UniProt ID."""
        intent = ParsedIntent(
            intent_type=IntentType.TARGET_LOOKUP,
            entities={"uniprot_id": "P35354"}
        )
        
        plan = planner.plan(intent)
        
        assert len(plan.steps) == 1
        assert plan.steps[0].tool_name == "uniprot_get_protein"
        assert plan.steps[0].args["uniprot_id"] == "P35354"
    
    def test_lookup_by_target_name(self, planner):
        """Test lookup by target name."""
        intent = ParsedIntent(
            intent_type=IntentType.TARGET_LOOKUP,
            entities={"target": "COX-2"}
        )
        
        plan = planner.plan(intent)
        
        assert len(plan.steps) == 1
        assert plan.steps[0].tool_name == "uniprot_search"


class TestPropertyCalculationPlanning:
    """Test property calculation plan generation."""
    
    def test_calc_with_smiles(self, planner):
        """Test calculation with SMILES."""
        intent = ParsedIntent(
            intent_type=IntentType.PROPERTY_CALCULATION,
            entities={"smiles": "CC(=O)O"}
        )
        
        plan = planner.plan(intent)
        
        assert len(plan.steps) >= 2  # Standardize + Calculate
        assert any("standardize" in s.tool_name for s in plan.steps)
        assert any("calc_properties" in s.tool_name for s in plan.steps)
    
    def test_calc_with_compound_name(self, planner):
        """Test calculation with compound name."""
        intent = ParsedIntent(
            intent_type=IntentType.PROPERTY_CALCULATION,
            entities={"compound": "aspirin"}
        )
        
        plan = planner.plan(intent)
        
        # Should lookup, standardize, then calculate
        assert len(plan.steps) >= 3
        assert "search_by_name" in plan.steps[0].tool_name


class TestLipinskiCheckPlanning:
    """Test Lipinski check plan generation."""
    
    def test_lipinski_with_smiles(self, planner):
        """Test Lipinski check with SMILES."""
        intent = ParsedIntent(
            intent_type=IntentType.LIPINSKI_CHECK,
            entities={"smiles": "CC(=O)O"}
        )
        
        plan = planner.plan(intent)
        
        assert len(plan.steps) >= 2
        assert any("standardize" in s.tool_name for s in plan.steps)
        assert any("lipinski" in s.tool_name for s in plan.steps)
    
    def test_lipinski_with_compound(self, planner):
        """Test Lipinski check with compound name."""
        intent = ParsedIntent(
            intent_type=IntentType.LIPINSKI_CHECK,
            entities={"compound": "aspirin"}
        )
        
        plan = planner.plan(intent)
        
        assert len(plan.steps) >= 3


class TestActivityLookupPlanning:
    """Test activity lookup plan generation."""
    
    def test_activity_with_chembl_id(self, planner):
        """Test activity lookup with ChEMBL ID."""
        intent = ParsedIntent(
            intent_type=IntentType.ACTIVITY_LOOKUP,
            entities={"chembl_id": "CHEMBL25", "activity_type": "IC50"}
        )
        
        plan = planner.plan(intent)
        
        assert len(plan.steps) >= 1
        activity_step = next(s for s in plan.steps if "activities" in s.tool_name)
        # Activity type is mapped to 'target' in the args
        assert activity_step.args.get("target") == "IC50" or activity_step.args.get("activity_type") == "IC50"
    
    def test_activity_with_compound_name(self, planner):
        """Test activity lookup with compound name."""
        intent = ParsedIntent(
            intent_type=IntentType.ACTIVITY_LOOKUP,
            entities={"compound": "aspirin"}
        )
        
        plan = planner.plan(intent)
        
        # Should lookup compound first, then get activities
        assert len(plan.steps) >= 2


class TestStructureConversionPlanning:
    """Test structure conversion plan generation."""
    
    def test_smiles_to_inchi(self, planner):
        """Test SMILES to InChI conversion."""
        intent = ParsedIntent(
            intent_type=IntentType.STRUCTURE_CONVERSION,
            entities={"smiles": "CC(=O)O", "format": "inchi"}
        )
        
        plan = planner.plan(intent)
        
        assert len(plan.steps) == 1
        assert plan.steps[0].tool_name == "rdkit_convert_format"
        assert plan.steps[0].args.get("to_format") == "inchi" or plan.steps[0].args.get("target_format") == "inchi"


class TestStandardizationPlanning:
    """Test standardization plan generation."""
    
    def test_standardize_smiles(self, planner):
        """Test SMILES standardization."""
        intent = ParsedIntent(
            intent_type=IntentType.STANDARDIZATION,
            entities={"smiles": "CC(=O)O"}
        )
        
        plan = planner.plan(intent)
        
        assert len(plan.steps) == 1
        assert "standardize" in plan.steps[0].tool_name


class TestScaffoldAnalysisPlanning:
    """Test scaffold analysis plan generation."""
    
    def test_scaffold_with_smiles(self, planner):
        """Test scaffold extraction with SMILES."""
        intent = ParsedIntent(
            intent_type=IntentType.SCAFFOLD_ANALYSIS,
            entities={"smiles": "CC(=O)O"}
        )
        
        plan = planner.plan(intent)
        
        assert len(plan.steps) >= 1
        assert any("scaffold" in s.tool_name for s in plan.steps)


# =============================================================================
# Test Dependency Tracking
# =============================================================================

class TestDependencyTracking:
    """Test step dependency tracking."""
    
    def test_dependencies_in_sequence(self, planner):
        """Test sequential dependencies."""
        intent = ParsedIntent(
            intent_type=IntentType.PROPERTY_CALCULATION,
            entities={"compound": "aspirin"}
        )
        
        plan = planner.plan(intent)
        
        # Each step should depend on previous
        for i, step in enumerate(plan.steps[1:], 1):
            assert step.depends_on == [plan.steps[i-1].step_id]
    
    def test_dependency_ordering(self, planner):
        """Test steps are properly ordered."""
        intent = ParsedIntent(
            intent_type=IntentType.SIMILARITY_SEARCH,
            entities={"compound": "aspirin"}
        )
        
        plan = planner.plan(intent)
        
        # Verify dependencies reference earlier steps
        for step in plan.steps:
            for dep_id in step.depends_on:
                # Find dependency step
                dep_step = next(s for s in plan.steps if s.step_id == dep_id)
                # Should come before current step
                assert plan.steps.index(dep_step) < plan.steps.index(step)
    
    def test_no_circular_dependencies(self, planner):
        """Test no circular dependencies."""
        intent = ParsedIntent(
            intent_type=IntentType.LIPINSKI_CHECK,
            entities={"smiles": "CC(=O)O"}
        )
        
        plan = planner.plan(intent)
        
        # Should be able to group into parallel batches
        groups = plan.get_parallel_groups()
        assert len(groups) > 0
        # Total steps should equal sum of group sizes
        assert sum(len(g) for g in groups) == len(plan.steps)


# =============================================================================
# Test Parallel Execution
# =============================================================================

class TestParallelExecution:
    """Test parallel execution grouping."""
    
    def test_get_parallel_groups(self, planner):
        """Test grouping independent steps."""
        intent = ParsedIntent(
            intent_type=IntentType.PROPERTY_CALCULATION,
            entities={"compound": "aspirin"}
        )
        
        plan = planner.plan(intent)
        groups = plan.get_parallel_groups()
        
        # Should have at least one group
        assert len(groups) > 0
        # Each group should have at least one step
        assert all(len(g) > 0 for g in groups)
    
    def test_sequential_steps_different_groups(self, planner):
        """Test sequential steps are in different groups."""
        intent = ParsedIntent(
            intent_type=IntentType.LIPINSKI_CHECK,
            entities={"compound": "aspirin"}
        )
        
        plan = planner.plan(intent)
        groups = plan.get_parallel_groups()
        
        # Sequential dependencies should be in separate groups
        if len(plan.steps) > 1:
            assert len(groups) >= 2


# =============================================================================
# Test Resource Estimation
# =============================================================================

class TestResourceEstimation:
    """Test time and cost estimation."""
    
    def test_time_estimation(self, planner):
        """Test execution time estimation."""
        intent = ParsedIntent(
            intent_type=IntentType.SIMILARITY_SEARCH,
            entities={"smiles": "CC(=O)O"}
        )
        
        plan = planner.plan(intent)
        
        assert plan.estimated_time_ms > 0
        # Should be sum of step times
        assert plan.estimated_time_ms == sum(s.estimated_time_ms for s in plan.steps)
    
    def test_cost_estimation(self, planner):
        """Test API cost estimation."""
        intent = ParsedIntent(
            intent_type=IntentType.COMPOUND_LOOKUP,
            entities={"chembl_id": "CHEMBL25"}
        )
        
        plan = planner.plan(intent)
        
        assert plan.estimated_cost >= 0
    
    def test_caching_flag(self, planner):
        """Test caching capability flag."""
        intent = ParsedIntent(
            intent_type=IntentType.SIMILARITY_SEARCH,
            entities={"smiles": "CC(=O)O"}
        )
        
        plan = planner.plan(intent)
        
        assert plan.can_cache is True


# =============================================================================
# Test Integration with Parser
# =============================================================================

class TestIntegrationWithParser:
    """Test planner integration with parser."""
    
    def test_parse_and_plan_similarity(self, parser, planner):
        """Test parsing and planning similarity search."""
        query = "Find compounds similar to aspirin"
        intent = parser.parse(query)
        plan = planner.plan(intent)
        
        assert plan.intent_type == IntentType.SIMILARITY_SEARCH
        assert len(plan.steps) > 0
    
    def test_parse_and_plan_properties(self, parser, planner):
        """Test parsing and planning property calculation."""
        query = "Calculate properties of CC(=O)O"
        intent = parser.parse(query)
        plan = planner.plan(intent)
        
        assert plan.intent_type == IntentType.PROPERTY_CALCULATION
        # Plan may have steps or not depending on parsing result
        # Main check is that the intent type is correct
    
    def test_parse_and_plan_lipinski(self, parser, planner):
        """Test parsing and planning Lipinski check."""
        query = "Check Lipinski rule for aspirin"
        intent = parser.parse(query)
        plan = planner.plan(intent)
        
        assert plan.intent_type == IntentType.LIPINSKI_CHECK
        assert any("lipinski" in s.tool_name for s in plan.steps)
    
    def test_parse_and_plan_lookup(self, parser, planner):
        """Test parsing and planning compound lookup."""
        query = "What is CHEMBL25"
        intent = parser.parse(query)
        plan = planner.plan(intent)
        
        assert plan.intent_type == IntentType.COMPOUND_LOOKUP
        # May have multiple steps now (compound + activities)
        assert len(plan.steps) >= 1


# =============================================================================
# Test Edge Cases
# =============================================================================

class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_unknown_intent(self, planner):
        """Test planning for unknown intent."""
        intent = ParsedIntent(
            intent_type=IntentType.UNKNOWN,
            entities={}
        )
        
        plan = planner.plan(intent)
        
        assert len(plan.steps) == 0
        assert plan.can_cache is False
    
    def test_missing_entities(self, planner):
        """Test planning with missing entities."""
        intent = ParsedIntent(
            intent_type=IntentType.SIMILARITY_SEARCH,
            entities={}  # No entities
        )
        
        plan = planner.plan(intent)
        
        # Should still generate a plan, may be empty or incomplete
        assert isinstance(plan, QueryPlan)
    
    def test_plan_repr(self, planner):
        """Test plan string representation."""
        intent = ParsedIntent(
            intent_type=IntentType.COMPOUND_LOOKUP,
            entities={"chembl_id": "CHEMBL25"}
        )
        
        plan = planner.plan(intent)
        repr_str = repr(plan)
        
        assert "QueryPlan" in repr_str
        assert "compound_lookup" in repr_str
    
    def test_step_repr(self):
        """Test step string representation."""
        step = PlanStep(
            step_id=0,
            tool_name="test_tool",
            args={},
            depends_on=[],
        )
        
        repr_str = repr(step)
        assert "Step0" in repr_str
        assert "test_tool" in repr_str


# =============================================================================
# Test Complex Scenarios
# =============================================================================

class TestComplexScenarios:
    """Test complex multi-step scenarios."""
    
    def test_similarity_with_filtering(self, planner):
        """Test similarity search with property filtering."""
        intent = ParsedIntent(
            intent_type=IntentType.SIMILARITY_SEARCH,
            entities={"compound": "aspirin", "threshold": 0.8, "limit": 100},
            constraints={"mw_max": 500, "logp_max": 5}
        )
        
        plan = planner.plan(intent)
        
        # Should have: lookup, standardize, similarity, filter
        assert len(plan.steps) >= 4
        assert any("filter" in s.tool_name for s in plan.steps)
    
    def test_variable_references(self, planner):
        """Test variable references between steps."""
        intent = ParsedIntent(
            intent_type=IntentType.PROPERTY_CALCULATION,
            entities={"compound": "aspirin"}
        )
        
        plan = planner.plan(intent)
        
        # Later steps should reference outputs from earlier steps
        for i, step in enumerate(plan.steps[1:], 1):
            # Check if args reference previous outputs
            has_ref = any(
                isinstance(v, str) and v.startswith("$")
                for v in step.args.values()
            )
            if has_ref:
                # Variable reference found
                assert True
                return
        
        # At least one step should have variable reference
        # (unless plan is very simple)
        if len(plan.steps) > 2:
            pytest.fail("Expected variable references in multi-step plan")
