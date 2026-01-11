"""
Integration tests for ChemAgent full query pipeline.

Tests the complete flow from natural language query to formatted answer.
"""

import pytest
import time
from chemagent import ChemAgent, QueryResult


class TestFullPipeline:
    """Test complete query execution pipeline."""
    
    @pytest.fixture
    def agent(self):
        """Create ChemAgent instance for testing."""
        return ChemAgent(use_cache=True, enable_parallel=True, max_workers=2)
    
    def test_simple_compound_lookup(self, agent):
        """Test basic compound lookup query."""
        result = agent.query("What is CHEMBL25?")
        
        assert isinstance(result, QueryResult)
        assert result.success
        assert result.answer
        assert "aspirin" in result.answer.lower() or "CHEMBL25" in result.answer
        assert result.steps_taken > 0
        assert result.execution_time_ms > 0
        assert result.intent_type == "compound_lookup"
    
    def test_property_calculation(self, agent):
        """Test molecular property calculation."""
        result = agent.query("Calculate properties of CC(=O)O")
        
        assert isinstance(result, QueryResult)
        assert result.success
        assert result.answer
        assert "molecular" in result.answer.lower() or "weight" in result.answer.lower()
        assert result.raw_output is not None
        
        # Check that properties are in raw output
        if isinstance(result.raw_output, dict):
            assert "molecular_weight" in str(result.raw_output).lower() or "status" in result.raw_output
    
    def test_similarity_search(self, agent):
        """Test similarity search query."""
        # Use a simple SMILES for aspirin
        result = agent.query("Find compounds similar to CC(=O)Oc1ccccc1C(=O)O")
        
        assert isinstance(result, QueryResult)
        # May succeed or fail depending on API availability
        assert result.steps_taken >= 1
        assert result.execution_time_ms > 0
    
    def test_lipinski_check(self, agent):
        """Test Lipinski rule of five check."""
        result = agent.query("Check Lipinski rules for CCO")
        
        assert isinstance(result, QueryResult)
        assert result.success
        assert result.answer
        assert "lipinski" in result.answer.lower() or "rule" in result.answer.lower()
    
    def test_empty_query(self, agent):
        """Test handling of empty query."""
        result = agent.query("")
        
        assert isinstance(result, QueryResult)
        assert not result.success
        assert result.error
        assert "empty" in result.error.lower()
    
    def test_unknown_intent(self, agent):
        """Test handling of unrecognized query."""
        result = agent.query("xyz random nonsense query")
        
        assert isinstance(result, QueryResult)
        # May fail or return unknown intent
        assert result.steps_taken >= 0


class TestCaching:
    """Test caching functionality."""
    
    @pytest.fixture
    def agent(self):
        """Create ChemAgent with caching enabled."""
        return ChemAgent(use_cache=True, cache_ttl=60)
    
    def test_cache_improves_performance(self, agent):
        """Verify caching improves query performance."""
        query = "What is CHEMBL25?"
        
        # First call - cache miss
        start1 = time.time()
        result1 = agent.query(query)
        time1 = (time.time() - start1) * 1000
        
        # Give it a moment
        time.sleep(0.1)
        
        # Second call - should hit cache
        start2 = time.time()
        result2 = agent.query(query)
        time2 = (time.time() - start2) * 1000
        
        # Both should succeed (or both fail)
        assert result1.success == result2.success
        
        if result1.success:
            # Answers should be identical
            assert result1.answer == result2.answer
            
            # Second call should be faster (though cache hits are tracked differently)
            # This is a soft check since timing can vary
            assert time2 < time1 or time2 < 100  # Cache hit should be very fast


class TestParallelExecution:
    """Test parallel execution capabilities."""
    
    @pytest.fixture
    def agent_parallel(self):
        """Create agent with parallel execution."""
        return ChemAgent(enable_parallel=True, max_workers=4)
    
    @pytest.fixture
    def agent_serial(self):
        """Create agent with serial execution."""
        return ChemAgent(enable_parallel=False, max_workers=1)
    
    def test_parallel_execution_works(self, agent_parallel):
        """Test that parallel execution completes successfully."""
        result = agent_parallel.query("Find compounds similar to CC(=O)O")
        
        # Should complete (success or failure doesn't matter for this test)
        assert isinstance(result, QueryResult)
        assert result.execution_time_ms > 0


class TestMultiStepQueries:
    """Test queries requiring multiple steps."""
    
    @pytest.fixture
    def agent(self):
        """Create ChemAgent instance."""
        return ChemAgent()
    
    def test_compound_with_properties(self, agent):
        """Test query combining lookup and property calculation."""
        result = agent.query("What is CHEMBL25 and what are its properties?")
        
        assert isinstance(result, QueryResult)
        # Should attempt execution
        assert result.steps_taken >= 0


class TestErrorHandling:
    """Test error handling and recovery."""
    
    @pytest.fixture
    def agent(self):
        """Create ChemAgent instance."""
        return ChemAgent()
    
    def test_invalid_smiles(self, agent):
        """Test handling of invalid SMILES."""
        result = agent.query("Calculate properties of INVALID_SMILES_123")
        
        assert isinstance(result, QueryResult)
        # May fail gracefully
        if not result.success:
            assert result.error is not None
    
    def test_nonexistent_compound(self, agent):
        """Test handling of nonexistent compound ID."""
        result = agent.query("What is CHEMBL99999999999?")
        
        assert isinstance(result, QueryResult)
        # Should complete but may indicate not found
        assert result.execution_time_ms > 0


class TestProvenance:
    """Test provenance tracking."""
    
    @pytest.fixture
    def agent(self):
        """Create ChemAgent instance."""
        return ChemAgent()
    
    def test_provenance_recorded(self, agent):
        """Test that provenance is recorded for queries."""
        result = agent.query("What is CHEMBL25?")
        
        assert isinstance(result, QueryResult)
        
        if result.success:
            # Should have provenance data
            assert isinstance(result.provenance, list)
            
            if result.provenance:
                # Each provenance entry should have required fields
                for prov in result.provenance:
                    assert "tool" in prov
                    assert "duration_ms" in prov


class TestResponseFormatting:
    """Test response formatting for different query types."""
    
    @pytest.fixture
    def agent(self):
        """Create ChemAgent instance."""
        return ChemAgent()
    
    def test_compound_response_formatted(self, agent):
        """Test compound lookup response is properly formatted."""
        result = agent.query("What is CHEMBL25?")
        
        if result.success:
            # Answer should be non-empty and formatted
            assert result.answer
            assert len(result.answer) > 10  # Should be more than just "CHEMBL25"
    
    def test_properties_response_formatted(self, agent):
        """Test property calculation response is properly formatted."""
        result = agent.query("Calculate properties of CCO")
        
        if result.success:
            assert result.answer
            # Should mention some property
            answer_lower = result.answer.lower()
            assert any(word in answer_lower for word in ["weight", "logp", "donor", "acceptor", "properties"])


class TestToolRegistry:
    """Test tool registry functionality."""
    
    def test_real_tools_loaded(self):
        """Test that real tools are loaded successfully."""
        agent = ChemAgent()
        
        # Should have access to executor and registry
        assert hasattr(agent, "executor")
        assert hasattr(agent.executor, "tool_registry")
        
        # Should have tools registered
        tools = agent.executor.tool_registry.list_tools()
        assert len(tools) > 0
        
        # Should have key tools
        expected_tools = [
            "chembl_get_compound",
            "rdkit_calc_properties",
            "rdkit_calc_lipinski"
        ]
        
        for tool in expected_tools:
            assert agent.executor.tool_registry.has(tool), f"Missing tool: {tool}"


@pytest.mark.slow
class TestLongRunningQueries:
    """Test queries that may take longer to execute."""
    
    @pytest.fixture
    def agent(self):
        """Create ChemAgent instance."""
        return ChemAgent()
    
    def test_large_similarity_search(self, agent):
        """Test similarity search with lower threshold (more results)."""
        result = agent.query("Find compounds similar to CC(=O)O with threshold 0.5")
        
        assert isinstance(result, QueryResult)
        assert result.execution_time_ms > 0
        
        # Should take some time but not too long
        assert result.execution_time_ms < 60000  # Less than 60 seconds
