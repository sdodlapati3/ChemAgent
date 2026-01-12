"""
Assertion-Based Evaluation Runner for ChemAgent.

Runs evaluation tasks and checks assertions against responses.
"""

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from .assertions import Assertion, AssertionResult, AssertionOutcome
from .task_suite import EvaluationTask, TaskSuite, TaskCategory

logger = logging.getLogger(__name__)


@dataclass
class TaskResult:
    """Result of evaluating a single task."""
    task_id: str
    query: str
    category: str
    difficulty: str
    success: bool
    response: str
    execution_time_ms: float
    tools_used: List[str]
    assertion_outcomes: List[AssertionOutcome]
    passed_assertions: int
    failed_assertions: int
    skipped_assertions: int
    overall_pass: bool
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "task_id": self.task_id,
            "query": self.query,
            "category": self.category,
            "difficulty": self.difficulty,
            "success": self.success,
            "overall_pass": self.overall_pass,
            "execution_time_ms": self.execution_time_ms,
            "tools_used": self.tools_used,
            "passed_assertions": self.passed_assertions,
            "failed_assertions": self.failed_assertions,
            "skipped_assertions": self.skipped_assertions,
            "assertion_details": [
                {
                    "name": ao.assertion_name,
                    "result": ao.result.value,
                    "message": ao.message
                }
                for ao in self.assertion_outcomes
            ],
            "error": self.error
        }


@dataclass
class EvaluationReport:
    """Complete evaluation report."""
    suite_name: str
    timestamp: str
    total_tasks: int
    passed_tasks: int
    failed_tasks: int
    error_tasks: int
    pass_rate: float
    total_execution_time_ms: float
    avg_execution_time_ms: float
    results_by_category: Dict[str, Dict[str, int]]
    results_by_difficulty: Dict[str, Dict[str, int]]
    task_results: List[TaskResult]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "suite_name": self.suite_name,
            "timestamp": self.timestamp,
            "summary": {
                "total_tasks": self.total_tasks,
                "passed_tasks": self.passed_tasks,
                "failed_tasks": self.failed_tasks,
                "error_tasks": self.error_tasks,
                "pass_rate": round(self.pass_rate * 100, 2),
            },
            "timing": {
                "total_execution_time_ms": round(self.total_execution_time_ms, 2),
                "avg_execution_time_ms": round(self.avg_execution_time_ms, 2),
            },
            "results_by_category": self.results_by_category,
            "results_by_difficulty": self.results_by_difficulty,
            "task_results": [tr.to_dict() for tr in self.task_results]
        }
    
    def to_markdown(self) -> str:
        """Generate markdown report."""
        lines = [
            f"# ChemAgent Evaluation Report",
            f"",
            f"**Suite:** {self.suite_name}",
            f"**Timestamp:** {self.timestamp}",
            f"",
            f"## Summary",
            f"",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Total Tasks | {self.total_tasks} |",
            f"| Passed | {self.passed_tasks} |",
            f"| Failed | {self.failed_tasks} |",
            f"| Errors | {self.error_tasks} |",
            f"| **Pass Rate** | **{self.pass_rate * 100:.1f}%** |",
            f"| Avg Time | {self.avg_execution_time_ms:.0f}ms |",
            f"",
            f"## Results by Category",
            f"",
            f"| Category | Passed | Failed | Pass Rate |",
            f"|----------|--------|--------|-----------|",
        ]
        
        for cat, stats in self.results_by_category.items():
            total = stats.get("passed", 0) + stats.get("failed", 0)
            rate = stats.get("passed", 0) / total * 100 if total > 0 else 0
            lines.append(f"| {cat} | {stats.get('passed', 0)} | {stats.get('failed', 0)} | {rate:.0f}% |")
        
        lines.extend([
            f"",
            f"## Results by Difficulty",
            f"",
            f"| Difficulty | Passed | Failed | Pass Rate |",
            f"|------------|--------|--------|-----------|",
        ])
        
        for diff, stats in self.results_by_difficulty.items():
            total = stats.get("passed", 0) + stats.get("failed", 0)
            rate = stats.get("passed", 0) / total * 100 if total > 0 else 0
            lines.append(f"| {diff} | {stats.get('passed', 0)} | {stats.get('failed', 0)} | {rate:.0f}% |")
        
        # Failed tasks details
        failed = [tr for tr in self.task_results if not tr.overall_pass]
        if failed:
            lines.extend([
                f"",
                f"## Failed Tasks",
                f"",
            ])
            for tr in failed[:10]:  # Show first 10
                lines.append(f"### {tr.task_id}")
                lines.append(f"**Query:** {tr.query}")
                lines.append(f"**Failed assertions:**")
                for ao in tr.assertion_outcomes:
                    if ao.result == AssertionResult.FAILED:
                        lines.append(f"- {ao.assertion_name}: {ao.message}")
                lines.append("")
        
        return "\n".join(lines)


class AssertionEvaluator:
    """Runs evaluation tasks and checks assertions."""
    
    def __init__(self, agent=None):
        """
        Initialize evaluator.
        
        Args:
            agent: ChemAgent instance (OptimalAgent or similar)
        """
        self.agent = agent
    
    def set_agent(self, agent):
        """Set the agent to evaluate."""
        self.agent = agent
    
    def evaluate_task(self, task: EvaluationTask) -> TaskResult:
        """
        Evaluate a single task.
        
        Args:
            task: The evaluation task
        
        Returns:
            TaskResult with assertion outcomes
        """
        logger.info(f"Evaluating task: {task.task_id}")
        
        start_time = time.time()
        success = False
        response_text = ""
        tool_results = {}
        tools_used = []
        error = None
        
        try:
            # Run the query through the agent
            if self.agent is None:
                raise ValueError("No agent configured")
            
            result = self.agent.process(task.query)
            success = result.success
            response_text = result.answer
            tool_results = result.tool_results or {}
            tools_used = result.tools_used or []
            
        except Exception as e:
            error = str(e)
            logger.error(f"Task {task.task_id} failed: {error}")
            response_text = f"Error: {error}"
        
        execution_time = (time.time() - start_time) * 1000
        
        # Run assertions
        assertion_outcomes = []
        metadata = {
            "query": task.query,
            "task_id": task.task_id,
        }
        
        for assertion in task.assertions:
            try:
                outcome = assertion.check(response_text, tool_results, metadata)
                assertion_outcomes.append(outcome)
            except Exception as e:
                logger.error(f"Assertion {assertion.name} failed: {e}")
                assertion_outcomes.append(AssertionOutcome(
                    assertion_name=assertion.name,
                    result=AssertionResult.SKIPPED,
                    message=f"Assertion error: {str(e)}"
                ))
        
        # Count results
        passed = sum(1 for ao in assertion_outcomes if ao.result == AssertionResult.PASSED)
        failed = sum(1 for ao in assertion_outcomes if ao.result == AssertionResult.FAILED)
        skipped = sum(1 for ao in assertion_outcomes if ao.result == AssertionResult.SKIPPED)
        
        # Overall pass if no failures and agent succeeded
        overall_pass = success and failed == 0
        
        return TaskResult(
            task_id=task.task_id,
            query=task.query,
            category=task.category.value,
            difficulty=task.difficulty.value,
            success=success,
            response=response_text[:1000],  # Truncate for storage
            execution_time_ms=execution_time,
            tools_used=tools_used,
            assertion_outcomes=assertion_outcomes,
            passed_assertions=passed,
            failed_assertions=failed,
            skipped_assertions=skipped,
            overall_pass=overall_pass,
            error=error
        )
    
    def evaluate_suite(
        self, 
        suite: TaskSuite,
        categories: Optional[List[TaskCategory]] = None,
        max_tasks: Optional[int] = None
    ) -> EvaluationReport:
        """
        Evaluate a complete task suite.
        
        Args:
            suite: The task suite to evaluate
            categories: Optional filter by categories
            max_tasks: Optional maximum number of tasks
        
        Returns:
            EvaluationReport with all results
        """
        logger.info(f"Starting evaluation of suite: {suite.name}")
        
        # Filter tasks
        tasks = list(suite.tasks)
        if categories:
            tasks = [t for t in tasks if t.category in categories]
        if max_tasks:
            tasks = tasks[:max_tasks]
        
        logger.info(f"Evaluating {len(tasks)} tasks")
        
        # Run evaluations
        task_results = []
        total_time = 0
        
        for i, task in enumerate(tasks):
            logger.info(f"Progress: {i+1}/{len(tasks)} - {task.task_id}")
            result = self.evaluate_task(task)
            task_results.append(result)
            total_time += result.execution_time_ms
        
        # Aggregate results
        passed_tasks = sum(1 for tr in task_results if tr.overall_pass)
        failed_tasks = sum(1 for tr in task_results if not tr.overall_pass and tr.error is None)
        error_tasks = sum(1 for tr in task_results if tr.error is not None)
        
        # Results by category
        by_category = {}
        for tr in task_results:
            cat = tr.category
            if cat not in by_category:
                by_category[cat] = {"passed": 0, "failed": 0}
            if tr.overall_pass:
                by_category[cat]["passed"] += 1
            else:
                by_category[cat]["failed"] += 1
        
        # Results by difficulty
        by_difficulty = {}
        for tr in task_results:
            diff = tr.difficulty
            if diff not in by_difficulty:
                by_difficulty[diff] = {"passed": 0, "failed": 0}
            if tr.overall_pass:
                by_difficulty[diff]["passed"] += 1
            else:
                by_difficulty[diff]["failed"] += 1
        
        report = EvaluationReport(
            suite_name=suite.name,
            timestamp=datetime.now().isoformat(),
            total_tasks=len(tasks),
            passed_tasks=passed_tasks,
            failed_tasks=failed_tasks,
            error_tasks=error_tasks,
            pass_rate=passed_tasks / len(tasks) if tasks else 0,
            total_execution_time_ms=total_time,
            avg_execution_time_ms=total_time / len(tasks) if tasks else 0,
            results_by_category=by_category,
            results_by_difficulty=by_difficulty,
            task_results=task_results
        )
        
        logger.info(f"Evaluation complete: {passed_tasks}/{len(tasks)} passed ({report.pass_rate*100:.1f}%)")
        
        return report
    
    def save_report(self, report: EvaluationReport, path: str):
        """Save evaluation report to file."""
        with open(path, "w") as f:
            json.dump(report.to_dict(), f, indent=2)
        logger.info(f"Saved report to {path}")
    
    def save_markdown_report(self, report: EvaluationReport, path: str):
        """Save markdown report to file."""
        with open(path, "w") as f:
            f.write(report.to_markdown())
        logger.info(f"Saved markdown report to {path}")
