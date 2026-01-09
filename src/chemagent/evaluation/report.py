"""Report generation for evaluation results."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

from .evaluator import EvaluationResult
from .metrics import EvaluationMetrics, MetricsCalculator

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generate evaluation reports in various formats."""
    
    @staticmethod
    def generate_text_report(
        results: List[EvaluationResult],
        metrics: EvaluationMetrics,
        output_file: Optional[Path] = None
    ) -> str:
        """Generate human-readable text report.
        
        Args:
            results: Evaluation results
            metrics: Calculated metrics
            output_file: Optional file to write report to
            
        Returns:
            Report as string
        """
        lines = []
        lines.append("=" * 80)
        lines.append("ChemAgent Golden Query Evaluation Report")
        lines.append("=" * 80)
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        # Overall results
        lines.append("OVERALL RESULTS")
        lines.append("-" * 80)
        lines.append(f"Total Queries:     {metrics.total_queries}")
        lines.append(f"Passed:            {metrics.passed} ({metrics.pass_rate:.1%})")
        lines.append(f"Failed:            {metrics.failed}")
        lines.append(f"Success Rate:      {metrics.success_rate:.1%}")
        lines.append("")
        
        # Performance
        lines.append("PERFORMANCE")
        lines.append("-" * 80)
        lines.append(f"Avg Execution:     {metrics.avg_execution_time:.3f}s")
        lines.append(f"Median Execution:  {metrics.median_execution_time:.3f}s")
        lines.append(f"P95 Execution:     {metrics.p95_execution_time:.3f}s")
        lines.append(f"P99 Execution:     {metrics.p99_execution_time:.3f}s")
        lines.append("")
        
        # Accuracy
        lines.append("ACCURACY")
        lines.append("-" * 80)
        lines.append(f"Intent Accuracy:   {metrics.intent_accuracy:.1%}")
        lines.append(f"Content Accuracy:  {metrics.content_accuracy:.1%}")
        lines.append(f"Error Handling:    {metrics.error_handling_rate:.1%}")
        lines.append(f"Steps Accuracy:    {metrics.expected_steps_accuracy:.1%}")
        lines.append(f"Avg Steps:         {metrics.avg_steps:.1f}")
        lines.append("")
        
        # By category
        lines.append("RESULTS BY CATEGORY")
        lines.append("-" * 80)
        lines.append(f"{'Category':<20} {'Total':>8} {'Passed':>8} {'Pass Rate':>10} {'Avg Time':>10}")
        lines.append("-" * 80)
        for category, data in sorted(metrics.by_category.items()):
            lines.append(
                f"{category:<20} {data['total']:>8} {data['passed']:>8} "
                f"{data['pass_rate']:>9.1%} {data['avg_time']:>9.3f}s"
            )
        lines.append("")
        
        # By difficulty
        lines.append("RESULTS BY DIFFICULTY")
        lines.append("-" * 80)
        lines.append(f"{'Difficulty':<20} {'Total':>8} {'Passed':>8} {'Pass Rate':>10} {'Avg Time':>10}")
        lines.append("-" * 80)
        for difficulty, data in sorted(metrics.by_difficulty.items()):
            lines.append(
                f"{difficulty:<20} {data['total']:>8} {data['passed']:>8} "
                f"{data['pass_rate']:>9.1%} {data['avg_time']:>9.3f}s"
            )
        lines.append("")
        
        # Errors
        if metrics.error_types:
            lines.append("ERROR ANALYSIS")
            lines.append("-" * 80)
            for error_type, count in sorted(
                metrics.error_types.items(),
                key=lambda x: x[1],
                reverse=True
            ):
                lines.append(f"{error_type}: {count}")
            lines.append("")
        
        # Failed queries
        if metrics.failure_patterns:
            lines.append("FAILED QUERIES")
            lines.append("-" * 80)
            for failure in metrics.failure_patterns[:10]:  # Top 10
                lines.append(f"Query: {failure['query_id']} ({failure['category']}/{failure['difficulty']})")
                if failure['error']:
                    lines.append(f"  Error: {failure['error']}")
                lines.append(f"  Details: {failure['validation_details']}")
                lines.append("")
        
        lines.append("=" * 80)
        
        report = "\n".join(lines)
        
        if output_file:
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, "w") as f:
                f.write(report)
            logger.info(f"Text report written to {output_file}")
            
        return report
    
    @staticmethod
    def generate_json_report(
        results: List[EvaluationResult],
        metrics: EvaluationMetrics,
        output_file: Optional[Path] = None
    ) -> Dict[str, Any]:
        """Generate JSON report.
        
        Args:
            results: Evaluation results
            metrics: Calculated metrics
            output_file: Optional file to write report to
            
        Returns:
            Report as dictionary
        """
        report = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "total_queries": metrics.total_queries,
            },
            "summary": {
                "passed": metrics.passed,
                "failed": metrics.failed,
                "pass_rate": metrics.pass_rate,
                "success_rate": metrics.success_rate,
            },
            "performance": {
                "avg_execution_time": metrics.avg_execution_time,
                "median_execution_time": metrics.median_execution_time,
                "p95_execution_time": metrics.p95_execution_time,
                "p99_execution_time": metrics.p99_execution_time,
            },
            "accuracy": {
                "intent_accuracy": metrics.intent_accuracy,
                "content_accuracy": metrics.content_accuracy,
                "error_handling_rate": metrics.error_handling_rate,
                "expected_steps_accuracy": metrics.expected_steps_accuracy,
                "avg_steps": metrics.avg_steps,
            },
            "by_category": metrics.by_category,
            "by_difficulty": metrics.by_difficulty,
            "errors": metrics.error_types,
            "failures": metrics.failure_patterns,
            "results": [
                {
                    "query_id": r.query_id,
                    "category": r.category,
                    "difficulty": r.difficulty,
                    "passed": r.passed,
                    "success": r.success,
                    "execution_time": r.execution_time,
                    "steps_taken": r.steps_taken,
                    "error": r.error,
                    "validation_details": r.validation_details,
                }
                for r in results
            ]
        }
        
        if output_file:
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, "w") as f:
                json.dump(report, f, indent=2)
            logger.info(f"JSON report written to {output_file}")
            
        return report
    
    @staticmethod
    def generate_html_report(
        results: List[EvaluationResult],
        metrics: EvaluationMetrics,
        output_file: Optional[Path] = None
    ) -> str:
        """Generate HTML report with visualizations.
        
        Args:
            results: Evaluation results
            metrics: Calculated metrics
            output_file: Optional file to write report to
            
        Returns:
            Report as HTML string
        """
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>ChemAgent Evaluation Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; }}
        h1 {{ color: #333; border-bottom: 3px solid #4CAF50; }}
        h2 {{ color: #555; border-bottom: 1px solid #ddd; margin-top: 30px; }}
        .metric {{ display: inline-block; margin: 10px 20px; }}
        .metric-label {{ font-size: 14px; color: #666; }}
        .metric-value {{ font-size: 24px; font-weight: bold; color: #4CAF50; }}
        .pass {{ color: #4CAF50; }}
        .fail {{ color: #f44336; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background-color: #4CAF50; color: white; }}
        tr:hover {{ background-color: #f5f5f5; }}
        .progress-bar {{ width: 100%; height: 30px; background: #f0f0f0; border-radius: 5px; }}
        .progress-fill {{ height: 100%; background: #4CAF50; border-radius: 5px; }}
        .timestamp {{ color: #999; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>ChemAgent Golden Query Evaluation Report</h1>
        <p class="timestamp">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        
        <h2>Overall Results</h2>
        <div class="metric">
            <div class="metric-label">Total Queries</div>
            <div class="metric-value">{metrics.total_queries}</div>
        </div>
        <div class="metric">
            <div class="metric-label">Passed</div>
            <div class="metric-value pass">{metrics.passed}</div>
        </div>
        <div class="metric">
            <div class="metric-label">Failed</div>
            <div class="metric-value fail">{metrics.failed}</div>
        </div>
        <div class="metric">
            <div class="metric-label">Pass Rate</div>
            <div class="metric-value">{metrics.pass_rate:.1%}</div>
        </div>
        
        <div class="progress-bar">
            <div class="progress-fill" style="width: {metrics.pass_rate * 100}%"></div>
        </div>
        
        <h2>Performance Metrics</h2>
        <table>
            <tr>
                <th>Metric</th>
                <th>Value</th>
            </tr>
            <tr>
                <td>Average Execution Time</td>
                <td>{metrics.avg_execution_time:.3f}s</td>
            </tr>
            <tr>
                <td>Median Execution Time</td>
                <td>{metrics.median_execution_time:.3f}s</td>
            </tr>
            <tr>
                <td>P95 Execution Time</td>
                <td>{metrics.p95_execution_time:.3f}s</td>
            </tr>
            <tr>
                <td>P99 Execution Time</td>
                <td>{metrics.p99_execution_time:.3f}s</td>
            </tr>
        </table>
        
        <h2>Results by Category</h2>
        <table>
            <tr>
                <th>Category</th>
                <th>Total</th>
                <th>Passed</th>
                <th>Pass Rate</th>
                <th>Avg Time</th>
            </tr>
"""
        
        for category, data in sorted(metrics.by_category.items()):
            html += f"""
            <tr>
                <td>{category}</td>
                <td>{data['total']}</td>
                <td>{data['passed']}</td>
                <td>{data['pass_rate']:.1%}</td>
                <td>{data['avg_time']:.3f}s</td>
            </tr>
"""
        
        html += """
        </table>
        
        <h2>Results by Difficulty</h2>
        <table>
            <tr>
                <th>Difficulty</th>
                <th>Total</th>
                <th>Passed</th>
                <th>Pass Rate</th>
                <th>Avg Time</th>
            </tr>
"""
        
        for difficulty, data in sorted(metrics.by_difficulty.items()):
            html += f"""
            <tr>
                <td>{difficulty}</td>
                <td>{data['total']}</td>
                <td>{data['passed']}</td>
                <td>{data['pass_rate']:.1%}</td>
                <td>{data['avg_time']:.3f}s</td>
            </tr>
"""
        
        html += """
        </table>
    </div>
</body>
</html>
"""
        
        if output_file:
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, "w") as f:
                f.write(html)
            logger.info(f"HTML report written to {output_file}")
            
        return html
