"""Metrics calculation for evaluation results."""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Any

from .evaluator import EvaluationResult

logger = logging.getLogger(__name__)


@dataclass
class EvaluationMetrics:
    """Comprehensive metrics from evaluation results."""
    
    # Overall metrics
    total_queries: int = 0
    passed: int = 0
    failed: int = 0
    pass_rate: float = 0.0
    success_rate: float = 0.0
    
    # Performance metrics
    avg_execution_time: float = 0.0
    median_execution_time: float = 0.0
    p95_execution_time: float = 0.0
    p99_execution_time: float = 0.0
    
    # Accuracy metrics
    intent_accuracy: float = 0.0
    content_accuracy: float = 0.0
    error_handling_rate: float = 0.0
    
    # Category breakdown
    by_category: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    by_difficulty: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # Step analysis
    avg_steps: float = 0.0
    expected_steps_accuracy: float = 0.0
    
    # Error analysis
    error_types: Dict[str, int] = field(default_factory=dict)
    failure_patterns: List[Dict[str, Any]] = field(default_factory=list)


class MetricsCalculator:
    """Calculate comprehensive metrics from evaluation results."""
    
    @staticmethod
    def calculate(results: List[EvaluationResult]) -> EvaluationMetrics:
        """Calculate all metrics from evaluation results.
        
        Args:
            results: List of evaluation results
            
        Returns:
            EvaluationMetrics object with all calculated metrics
        """
        if not results:
            return EvaluationMetrics()
            
        metrics = EvaluationMetrics()
        
        # Overall metrics
        metrics.total_queries = len(results)
        metrics.passed = sum(1 for r in results if r.passed)
        metrics.failed = metrics.total_queries - metrics.passed
        metrics.pass_rate = metrics.passed / metrics.total_queries
        metrics.success_rate = sum(1 for r in results if r.success) / metrics.total_queries
        
        # Performance metrics
        execution_times = sorted([r.execution_time for r in results])
        metrics.avg_execution_time = sum(execution_times) / len(execution_times)
        metrics.median_execution_time = MetricsCalculator._percentile(execution_times, 50)
        metrics.p95_execution_time = MetricsCalculator._percentile(execution_times, 95)
        metrics.p99_execution_time = MetricsCalculator._percentile(execution_times, 99)
        
        # Accuracy metrics
        intent_correct = sum(
            1 for r in results
            if r.validation_details.get("intent_match", False)
        )
        metrics.intent_accuracy = intent_correct / metrics.total_queries
        
        content_correct = sum(
            1 for r in results
            if all(r.validation_details.get("content_checks", {}).values())
        )
        metrics.content_accuracy = content_correct / metrics.total_queries
        
        error_queries = [r for r in results if r.expected_result and not r.expected_result.get("success", True)]
        if error_queries:
            error_handled = sum(
                1 for r in error_queries
                if r.validation_details.get("error_type_match", False)
            )
            metrics.error_handling_rate = error_handled / len(error_queries)
        
        # Category breakdown
        metrics.by_category = MetricsCalculator._calculate_by_group(
            results, "category"
        )
        
        # Difficulty breakdown
        metrics.by_difficulty = MetricsCalculator._calculate_by_group(
            results, "difficulty"
        )
        
        # Step analysis
        metrics.avg_steps = sum(r.steps_taken for r in results) / metrics.total_queries
        
        expected_steps_correct = sum(
            1 for r in results
            if r.steps_taken == r.metadata.get("steps_expected", 0)
        )
        metrics.expected_steps_accuracy = expected_steps_correct / metrics.total_queries
        
        # Error analysis
        metrics.error_types = MetricsCalculator._analyze_errors(results)
        metrics.failure_patterns = MetricsCalculator._analyze_failures(results)
        
        return metrics
    
    @staticmethod
    def _percentile(sorted_values: List[float], percentile: int) -> float:
        """Calculate percentile of sorted values."""
        if not sorted_values:
            return 0.0
        index = int(len(sorted_values) * percentile / 100)
        return sorted_values[min(index, len(sorted_values) - 1)]
    
    @staticmethod
    def _calculate_by_group(
        results: List[EvaluationResult],
        group_key: str
    ) -> Dict[str, Dict[str, Any]]:
        """Calculate metrics grouped by a key (category or difficulty)."""
        groups = {}
        
        for result in results:
            group = getattr(result, group_key)
            if group not in groups:
                groups[group] = {
                    "total": 0,
                    "passed": 0,
                    "failed": 0,
                    "pass_rate": 0.0,
                    "avg_time": 0.0,
                    "execution_times": []
                }
            
            groups[group]["total"] += 1
            if result.passed:
                groups[group]["passed"] += 1
            else:
                groups[group]["failed"] += 1
            groups[group]["execution_times"].append(result.execution_time)
        
        # Calculate derived metrics
        for group, data in groups.items():
            data["pass_rate"] = data["passed"] / data["total"]
            data["avg_time"] = sum(data["execution_times"]) / len(data["execution_times"])
            del data["execution_times"]  # Remove raw times from output
            
        return groups
    
    @staticmethod
    def _analyze_errors(results: List[EvaluationResult]) -> Dict[str, int]:
        """Analyze error types in results."""
        error_types = {}
        
        for result in results:
            if result.error:
                # Extract error type from error message
                error_type = result.error.split(":")[0] if ":" in result.error else "unknown"
                error_types[error_type] = error_types.get(error_type, 0) + 1
                
        return error_types
    
    @staticmethod
    def _analyze_failures(results: List[EvaluationResult]) -> List[Dict[str, Any]]:
        """Analyze failure patterns."""
        failures = []
        
        for result in results:
            if not result.passed:
                failures.append({
                    "query_id": result.query_id,
                    "category": result.category,
                    "difficulty": result.difficulty,
                    "error": result.error,
                    "validation_details": result.validation_details
                })
                
        return failures
    
    @staticmethod
    def compare_metrics(
        current: EvaluationMetrics,
        baseline: EvaluationMetrics
    ) -> Dict[str, Any]:
        """Compare current metrics against baseline.
        
        Args:
            current: Current evaluation metrics
            baseline: Baseline metrics to compare against
            
        Returns:
            Dictionary with comparison results and regressions
        """
        comparison = {
            "pass_rate_change": current.pass_rate - baseline.pass_rate,
            "performance_change": current.avg_execution_time - baseline.avg_execution_time,
            "accuracy_changes": {
                "intent": current.intent_accuracy - baseline.intent_accuracy,
                "content": current.content_accuracy - baseline.content_accuracy,
            },
            "regressions": [],
            "improvements": []
        }
        
        # Check for regressions
        if comparison["pass_rate_change"] < -0.05:  # 5% threshold
            comparison["regressions"].append({
                "type": "pass_rate",
                "change": comparison["pass_rate_change"],
                "severity": "high"
            })
            
        if comparison["performance_change"] > baseline.avg_execution_time * 0.2:  # 20% slower
            comparison["regressions"].append({
                "type": "performance",
                "change": comparison["performance_change"],
                "severity": "medium"
            })
            
        # Check for improvements
        if comparison["pass_rate_change"] > 0.05:
            comparison["improvements"].append({
                "type": "pass_rate",
                "change": comparison["pass_rate_change"]
            })
            
        if comparison["performance_change"] < -baseline.avg_execution_time * 0.1:  # 10% faster
            comparison["improvements"].append({
                "type": "performance",
                "change": comparison["performance_change"]
            })
            
        return comparison
