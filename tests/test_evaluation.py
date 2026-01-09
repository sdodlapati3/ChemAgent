"""Tests for the evaluation framework."""

import json
import pytest
from pathlib import Path

from chemagent.evaluation import (
    GoldenQueryEvaluator,
    MetricsCalculator,
    EvaluationResult
)


class TestGoldenQueryEvaluator:
    """Test golden query evaluation."""
    
    def test_load_golden_queries_all(self, tmp_path):
        """Test loading all golden queries."""
        # Create test data
        queries_dir = tmp_path / "golden_queries"
        queries_dir.mkdir()
        
        test_queries = [
            {
                "id": "test_001",
                "category": "compound_lookup",
                "difficulty": "easy",
                "query": "What is CHEMBL25?",
                "expected": {"intent_type": "compound_lookup", "success": True},
                "metadata": {"steps_expected": 1}
            }
        ]
        
        with open(queries_dir / "test.json", "w") as f:
            json.dump(test_queries, f)
        
        evaluator = GoldenQueryEvaluator(str(queries_dir))
        queries = evaluator.load_golden_queries()
        
        assert len(queries) == 1
        assert queries[0]["id"] == "test_001"
    
    def test_load_golden_queries_by_category(self, tmp_path):
        """Test loading queries by category."""
        queries_dir = tmp_path / "golden_queries"
        queries_dir.mkdir()
        
        compound_queries = [{"id": "c1", "category": "compound_lookup"}]
        property_queries = [{"id": "p1", "category": "properties"}]
        
        with open(queries_dir / "compound_lookup.json", "w") as f:
            json.dump(compound_queries, f)
        with open(queries_dir / "properties.json", "w") as f:
            json.dump(property_queries, f)
        
        evaluator = GoldenQueryEvaluator(str(queries_dir))
        
        # Load specific category
        queries = evaluator.load_golden_queries("compound_lookup")
        assert len(queries) == 1
        assert queries[0]["id"] == "c1"
    
    def test_validate_result_success(self):
        """Test result validation for successful query."""
        evaluator = GoldenQueryEvaluator()
        
        actual = {
            "success": True,
            "intent_type": "compound_lookup",
            "result": {"name": "aspirin"}
        }
        
        expected = {
            "success": True,
            "intent_type": "compound_lookup"
        }
        
        passed, details = evaluator.validate_result(actual, expected)
        
        assert passed is True
        assert details["success_match"] is True
        assert details["intent_match"] is True
    
    def test_validate_result_content_check(self):
        """Test result validation with content checks."""
        evaluator = GoldenQueryEvaluator()
        
        actual = {
            "success": True,
            "result": {"compound": "aspirin", "chembl_id": "CHEMBL25"}
        }
        
        expected = {
            "success": True,
            "should_contain": ["aspirin", "CHEMBL25"]
        }
        
        passed, details = evaluator.validate_result(actual, expected)
        
        assert passed is True
        assert details["content_checks"]["aspirin"] is True
        assert details["content_checks"]["CHEMBL25"] is True
    
    def test_validate_result_failure(self):
        """Test result validation for failed query."""
        evaluator = GoldenQueryEvaluator()
        
        actual = {
            "success": False,
            "error_type": "not_found"
        }
        
        expected = {
            "success": False,
            "error_type": "not_found"
        }
        
        passed, details = evaluator.validate_result(actual, expected)
        
        assert passed is True
        assert details["error_type_match"] is True


class TestMetricsCalculator:
    """Test metrics calculation."""
    
    def test_calculate_basic_metrics(self):
        """Test calculation of basic metrics."""
        results = [
            EvaluationResult(
                query_id="q1",
                category="compound_lookup",
                difficulty="easy",
                query="test",
                success=True,
                passed=True,
                execution_time=0.1,
                steps_taken=1
            ),
            EvaluationResult(
                query_id="q2",
                category="properties",
                difficulty="medium",
                query="test2",
                success=True,
                passed=False,
                execution_time=0.2,
                steps_taken=2
            )
        ]
        
        metrics = MetricsCalculator.calculate(results)
        
        assert metrics.total_queries == 2
        assert metrics.passed == 1
        assert metrics.failed == 1
        assert metrics.pass_rate == 0.5
        assert metrics.avg_execution_time == 0.15
    
    def test_calculate_by_category(self):
        """Test metrics grouped by category."""
        results = [
            EvaluationResult(
                query_id="q1",
                category="compound_lookup",
                difficulty="easy",
                query="test",
                success=True,
                passed=True,
                execution_time=0.1,
                steps_taken=1
            ),
            EvaluationResult(
                query_id="q2",
                category="compound_lookup",
                difficulty="easy",
                query="test2",
                success=True,
                passed=True,
                execution_time=0.2,
                steps_taken=1
            )
        ]
        
        metrics = MetricsCalculator.calculate(results)
        
        assert "compound_lookup" in metrics.by_category
        assert metrics.by_category["compound_lookup"]["total"] == 2
        assert metrics.by_category["compound_lookup"]["passed"] == 2
        assert metrics.by_category["compound_lookup"]["pass_rate"] == 1.0
    
    def test_compare_metrics_regression(self):
        """Test metrics comparison for regression detection."""
        current = MetricsCalculator.calculate([
            EvaluationResult(
                "q1", "test", "easy", "test", True, True, 1.0, 1
            )
        ])
        
        baseline = MetricsCalculator.calculate([
            EvaluationResult(
                "q1", "test", "easy", "test", True, True, 0.5, 1
            )
        ])
        
        comparison = MetricsCalculator.compare_metrics(current, baseline)
        
        assert comparison["performance_change"] > 0  # Slower
        assert len(comparison["regressions"]) > 0  # Regression detected


@pytest.fixture
def sample_evaluation_result():
    """Sample evaluation result for testing."""
    return EvaluationResult(
        query_id="test_001",
        category="compound_lookup",
        difficulty="easy",
        query="What is CHEMBL25?",
        success=True,
        passed=True,
        execution_time=0.123,
        steps_taken=1,
        actual_result={"success": True, "compound": "aspirin"},
        expected_result={"success": True, "intent_type": "compound_lookup"},
        validation_details={"success_match": True, "intent_match": True},
        metadata={"steps_expected": 1, "cache_eligible": True}
    )
