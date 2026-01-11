"""Core evaluation engine for running golden queries."""

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from chemagent import ChemAgent
from chemagent.config import get_config

logger = logging.getLogger(__name__)


@dataclass
class EvaluationResult:
    """Result of evaluating a single golden query."""
    
    query_id: str
    category: str
    difficulty: str
    query: str
    success: bool
    passed: bool
    execution_time: float
    steps_taken: int
    error: Optional[str] = None
    actual_result: Optional[Dict[str, Any]] = None
    expected_result: Optional[Dict[str, Any]] = None
    validation_details: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class GoldenQueryEvaluator:
    """Evaluates ChemAgent against golden query datasets."""
    
    def __init__(
        self,
        golden_queries_dir: str = "data/golden_queries",
        agent: Optional[ChemAgent] = None
    ):
        """Initialize evaluator.
        
        Args:
            golden_queries_dir: Directory containing golden query JSON files
            agent: ChemAgent instance (creates new one if None)
        """
        self.golden_queries_dir = Path(golden_queries_dir)
        self.agent = agent or ChemAgent()
        self.config = get_config()
        self.results: List[EvaluationResult] = []
        
    def load_golden_queries(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Load golden queries from JSON files.
        
        Args:
            category: Specific category to load (loads all if None)
            
        Returns:
            List of golden query dictionaries
        """
        queries = []
        
        if category:
            file_path = self.golden_queries_dir / f"{category}.json"
            if file_path.exists():
                with open(file_path) as f:
                    queries.extend(json.load(f))
            else:
                logger.warning(f"Category file not found: {file_path}")
        else:
            # Load all category files
            for file_path in self.golden_queries_dir.glob("*.json"):
                try:
                    with open(file_path) as f:
                        queries.extend(json.load(f))
                except Exception as e:
                    logger.error(f"Error loading {file_path}: {e}")
                    
        logger.info(f"Loaded {len(queries)} golden queries")
        return queries
    
    def validate_result(
        self,
        actual: Dict[str, Any],
        expected: Dict[str, Any]
    ) -> tuple[bool, Dict[str, Any]]:
        """Validate actual result against expected.
        
        Args:
            actual: Actual result from agent
            expected: Expected result specification
            
        Returns:
            Tuple of (passed, validation_details)
        """
        details = {}
        passed = True
        
        # Check success flag
        if "success" in expected:
            success_match = actual.get("success") == expected["success"]
            details["success_match"] = success_match
            if not success_match:
                passed = False
                
        # Check intent type
        if "intent_type" in expected:
            intent_match = actual.get("intent_type") == expected["intent_type"]
            details["intent_match"] = intent_match
            if not intent_match:
                passed = False
                
        # Check for required content
        if "should_contain" in expected:
            content_checks = {}
            result_str = json.dumps(actual).lower()
            for required in expected["should_contain"]:
                found = required.lower() in result_str
                content_checks[required] = found
                if not found:
                    passed = False
            details["content_checks"] = content_checks
            
        # Check if result is a list when expected
        if expected.get("should_return_list"):
            is_list = isinstance(actual.get("result"), list)
            details["returns_list"] = is_list
            if not is_list:
                passed = False
                
        # Check error type for failure cases
        if "error_type" in expected:
            error_match = actual.get("error_type") == expected["error_type"]
            details["error_type_match"] = error_match
            if not error_match:
                passed = False
                
        # Check specific values
        for key in ["entity_type", "entity_value", "property", "compound"]:
            if key in expected:
                value_match = actual.get(key) == expected[key]
                details[f"{key}_match"] = value_match
                if not value_match:
                    passed = False
                    
        return passed, details
    
    def evaluate_query(self, query: Dict[str, Any]) -> EvaluationResult:
        """Evaluate a single golden query.
        
        Args:
            query: Golden query dictionary
            
        Returns:
            EvaluationResult with validation outcome
        """
        logger.info(f"Evaluating query: {query['id']}")
        
        start_time = time.time()
        success = False
        actual_result = None
        error = None
        steps_taken = 0
        
        try:
            # Run the query through the agent
            response = self.agent.process_query(query["query"])
            success = response.get("success", False)
            actual_result = response
            steps_taken = len(response.get("steps", []))
            
        except Exception as e:
            error = str(e)
            logger.error(f"Query {query['id']} failed with error: {error}")
            actual_result = {"success": False, "error": error}
            
        execution_time = time.time() - start_time
        
        # Validate the result
        passed, validation_details = self.validate_result(
            actual_result,
            query["expected"]
        )
        
        return EvaluationResult(
            query_id=query["id"],
            category=query["category"],
            difficulty=query["difficulty"],
            query=query["query"],
            success=success,
            passed=passed,
            execution_time=execution_time,
            steps_taken=steps_taken,
            error=error,
            actual_result=actual_result,
            expected_result=query["expected"],
            validation_details=validation_details,
            metadata=query.get("metadata", {})
        )
    
    def evaluate_all(
        self,
        category: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[EvaluationResult]:
        """Evaluate all golden queries.
        
        Args:
            category: Specific category to evaluate (all if None)
            limit: Maximum number of queries to evaluate
            
        Returns:
            List of evaluation results
        """
        queries = self.load_golden_queries(category)
        
        if limit:
            queries = queries[:limit]
            
        self.results = []
        for i, query in enumerate(queries, 1):
            logger.info(f"Processing query {i}/{len(queries)}")
            result = self.evaluate_query(query)
            self.results.append(result)
            
        return self.results
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics of evaluation results.
        
        Returns:
            Dictionary with summary statistics
        """
        if not self.results:
            return {}
            
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        success = sum(1 for r in self.results if r.success)
        
        # By category
        by_category = {}
        for result in self.results:
            cat = result.category
            if cat not in by_category:
                by_category[cat] = {"total": 0, "passed": 0}
            by_category[cat]["total"] += 1
            if result.passed:
                by_category[cat]["passed"] += 1
                
        # By difficulty
        by_difficulty = {}
        for result in self.results:
            diff = result.difficulty
            if diff not in by_difficulty:
                by_difficulty[diff] = {"total": 0, "passed": 0}
            by_difficulty[diff]["total"] += 1
            if result.passed:
                by_difficulty[diff]["passed"] += 1
                
        # Performance metrics
        execution_times = [r.execution_time for r in self.results]
        avg_time = sum(execution_times) / len(execution_times)
        
        return {
            "total_queries": total,
            "passed": passed,
            "failed": total - passed,
            "pass_rate": passed / total if total > 0 else 0,
            "success_rate": success / total if total > 0 else 0,
            "by_category": by_category,
            "by_difficulty": by_difficulty,
            "avg_execution_time": avg_time,
            "min_execution_time": min(execution_times),
            "max_execution_time": max(execution_times),
        }
