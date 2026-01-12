"""Evaluation framework for ChemAgent.

Provides:
- Golden query evaluation (original)
- Assertion-based evaluation (new)
- Task suites with constraint checking
- Provenance verification
"""

from .evaluator import GoldenQueryEvaluator, EvaluationResult
from .metrics import MetricsCalculator, EvaluationMetrics
from .report import ReportGenerator

# New assertion-based evaluation
from .assertions import (
    Assertion,
    AssertionResult,
    AssertionOutcome,
    HasProvenance,
    SourceIs,
    ContainsEntity,
    ContainsAnyEntity,
    HasNumericValue,
    HasAssociationScore,
    HasStructuredData,
    ResponseLength,
    NoHallucination,
    create_standard_assertions,
    create_evidence_assertions,
    create_compound_assertions,
)
from .task_suite import (
    EvaluationTask,
    TaskSuite,
    TaskCategory,
    TaskDifficulty,
    create_default_task_suite,
)
from .assertion_evaluator import (
    AssertionEvaluator,
    TaskResult,
    EvaluationReport,
)

__all__ = [
    # Original evaluation
    "GoldenQueryEvaluator",
    "EvaluationResult",
    "MetricsCalculator",
    "EvaluationMetrics",
    "ReportGenerator",
    
    # Assertion-based evaluation
    "Assertion",
    "AssertionResult",
    "AssertionOutcome",
    "HasProvenance",
    "SourceIs",
    "ContainsEntity",
    "ContainsAnyEntity",
    "HasNumericValue",
    "HasAssociationScore",
    "HasStructuredData",
    "ResponseLength",
    "NoHallucination",
    "create_standard_assertions",
    "create_evidence_assertions",
    "create_compound_assertions",
    
    # Task suite
    "EvaluationTask",
    "TaskSuite",
    "TaskCategory",
    "TaskDifficulty",
    "create_default_task_suite",
    
    # Evaluator
    "AssertionEvaluator",
    "TaskResult",
    "EvaluationReport",
]
