#!/usr/bin/env python3
"""
Regression Test Suite for ChemAgent

Fast validation tests for specific bug fixes and critical functionality.
Run these tests before each full test round to quickly verify fixes.

Usage:
    python -m tests.integration.test_regression
    pytest tests/integration/test_regression.py -v
"""
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from chemagent import ChemAgent

# Configure logging
logging.basicConfig(
    level=logging.WARNING,  # Reduce noise for fast tests
    format="%(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class TestDrugNameParsing:
    """Regression tests for drug name vs SMILES parsing (Issue #1)"""
    
    def test_similarity_with_common_drugs(self):
        """Test that common drug names are correctly parsed as compounds, not SMILES"""
        agent = ChemAgent()
        
        test_cases = [
            "Search for analogs of diazepam",
            "Find compounds similar to caffeine",
            "What compounds are similar to morphine?",
            "Compounds like ibuprofen",
            "Analogs of amoxicillin",
        ]
        
        for query in test_cases:
            result = agent.query(query)
            assert result.success, f"Failed: {query} - Error: {result.error}"
            logger.info(f"✓ {query}")
    
    def test_similarity_with_new_drugs(self):
        """Test newly added drugs to common list"""
        agent = ChemAgent()
        
        test_cases = [
            "Find analogs of lisinopril",
            "Search for compounds similar to omeprazole",
            "What is similar to metoprolol?",
        ]
        
        for query in test_cases:
            result = agent.query(query)
            assert result.success, f"Failed: {query} - Error: {result.error}"
            logger.info(f"✓ {query}")


class TestActivityLookup:
    """Regression tests for activity lookup parameters (Issue #2)"""
    
    def test_activity_queries(self):
        """Test that activity lookups use correct parameter names"""
        agent = ChemAgent()
        
        test_cases = [
            "What is the IC50 of ibuprofen?",
            "Get activities for aspirin",
            "Show bioactivities of caffeine",
        ]
        
        for query in test_cases:
            result = agent.query(query)
            # Note: These might fail if compound has no activities, 
            # but should not fail with parameter errors
            if not result.success:
                error_lower = str(result.error).lower()
                assert "unexpected keyword" not in error_lower, \
                    f"Parameter error in: {query} - {result.error}"
                assert "activity_type" not in error_lower, \
                    f"Old parameter name used in: {query}"
            logger.info(f"✓ {query}")


class TestComparisonQueries:
    """Regression tests for comparison query performance (Issue #3)"""
    
    def test_comparison_completes_quickly(self):
        """Test that comparison queries complete in reasonable time"""
        import time
        agent = ChemAgent()
        
        test_cases = [
            ("Compare aspirin and ibuprofen", 5.0),
            ("aspirin vs ibuprofen", 5.0),
            ("Compare metformin and insulin", 5.0),
        ]
        
        for query, max_seconds in test_cases:
            start = time.time()
            result = agent.query(query)
            elapsed = time.time() - start
            
            assert result.success, f"Failed: {query} - Error: {result.error}"
            assert elapsed < max_seconds, \
                f"Too slow: {query} took {elapsed:.2f}s (max {max_seconds}s)"
            logger.info(f"✓ {query} ({elapsed:.2f}s)")
    
    def test_comparison_extracts_both_compounds(self):
        """Test that both compounds are extracted from comparison queries"""
        agent = ChemAgent()
        
        result = agent.query("Compare aspirin and ibuprofen")
        assert result.success, f"Comparison failed: {result.error}"
        
        # Check that answer mentions both drugs
        answer_lower = result.answer.lower() if result.answer else ""
        assert "aspirin" in answer_lower, "aspirin not found in comparison result"
        assert "ibuprofen" in answer_lower, "ibuprofen not found in comparison result"
        logger.info("✓ Both compounds present in comparison")


class TestPropertyCalculation:
    """Regression tests for property calculation queries"""
    
    def test_property_queries(self):
        """Test basic property calculation queries"""
        agent = ChemAgent()
        
        test_cases = [
            "Calculate properties of metformin",
            "What is the molecular weight of aspirin?",
            "Get properties of caffeine",
        ]
        
        for query in test_cases:
            result = agent.query(query)
            assert result.success, f"Failed: {query} - Error: {result.error}"
            logger.info(f"✓ {query}")


class TestLipinskiCheck:
    """Regression tests for Lipinski rule checking"""
    
    def test_lipinski_queries(self):
        """Test Lipinski rule checking queries"""
        agent = ChemAgent()
        
        test_cases = [
            "Check Lipinski rules for aspirin",
            "Is ibuprofen drug-like?",
            "Does caffeine pass Lipinski?",
        ]
        
        for query in test_cases:
            result = agent.query(query)
            assert result.success, f"Failed: {query} - Error: {result.error}"
            logger.info(f"✓ {query}")


class TestErrorHandling:
    """Regression tests for error handling and edge cases"""
    
    def test_invalid_smiles(self):
        """Test that invalid SMILES are handled gracefully"""
        agent = ChemAgent()
        
        result = agent.query("Calculate properties of INVALID_SMILES_STRING")
        # Should fail gracefully with error message
        assert not result.success, "Should fail on invalid SMILES"
        assert result.error is not None, "Should have error message"
        logger.info("✓ Invalid SMILES handled gracefully")
    
    def test_nonexistent_compound(self):
        """Test that nonexistent compounds are handled gracefully"""
        agent = ChemAgent()
        
        result = agent.query("Find analogs of NONEXISTENT_COMPOUND_XYZ")
        # Should fail gracefully
        assert not result.success or "not found" in str(result.answer).lower(), \
            "Should handle nonexistent compound"
        logger.info("✓ Nonexistent compound handled")
    
    def test_empty_query(self):
        """Test that empty queries are handled"""
        agent = ChemAgent()
        
        result = agent.query("")
        assert not result.success, "Should fail on empty query"
        assert result.error is not None, "Should have error message"
        logger.info("✓ Empty query handled")


def run_all_tests():
    """Run all regression tests and report results"""
    import traceback
    
    test_classes = [
        TestDrugNameParsing,
        TestActivityLookup,
        TestComparisonQueries,
        TestPropertyCalculation,
        TestLipinskiCheck,
        TestErrorHandling,
    ]
    
    total_tests = 0
    passed_tests = 0
    failed_tests = []
    
    print("=" * 70)
    print("Running ChemAgent Regression Tests")
    print("=" * 70)
    print()
    
    for test_class in test_classes:
        class_name = test_class.__name__
        print(f"\n{class_name}:")
        print("-" * 70)
        
        test_instance = test_class()
        test_methods = [m for m in dir(test_instance) if m.startswith("test_")]
        
        for method_name in test_methods:
            total_tests += 1
            test_method = getattr(test_instance, method_name)
            
            try:
                test_method()
                passed_tests += 1
                print(f"  ✓ {method_name}")
            except AssertionError as e:
                failed_tests.append((class_name, method_name, str(e)))
                print(f"  ✗ {method_name}: {str(e)}")
            except Exception as e:
                failed_tests.append((class_name, method_name, traceback.format_exc()))
                print(f"  ✗ {method_name}: {type(e).__name__}: {str(e)}")
    
    # Summary
    print()
    print("=" * 70)
    print(f"Regression Test Summary")
    print("=" * 70)
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests} ({100*passed_tests/total_tests:.1f}%)")
    print(f"Failed: {len(failed_tests)}")
    
    if failed_tests:
        print("\nFailed Tests:")
        for class_name, method_name, error in failed_tests:
            print(f"  - {class_name}.{method_name}")
            print(f"    {error[:200]}")
    
    print("=" * 70)
    
    return len(failed_tests) == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
