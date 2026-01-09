"""Benchmark suite for ChemAgent performance testing."""

import json
import statistics
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..evaluation import GoldenQueryEvaluator


@dataclass
class BenchmarkResult:
    """Result of a single benchmark run."""
    
    name: str
    category: str
    execution_time: float
    memory_usage_mb: float
    success: bool
    cached: bool
    steps_taken: int
    parallel_eligible: bool
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BenchmarkSuite:
    """Complete benchmark suite results."""
    
    timestamp: str
    version: str
    total_benchmarks: int
    results: List[BenchmarkResult]
    
    # Performance metrics
    avg_execution_time: float = 0.0
    median_execution_time: float = 0.0
    p95_execution_time: float = 0.0
    p99_execution_time: float = 0.0
    
    # Category breakdown
    by_category: Dict[str, Dict[str, float]] = field(default_factory=dict)
    
    # Comparison with baseline
    baseline_comparison: Optional[Dict[str, Any]] = None


class BenchmarkRunner:
    """Run performance benchmarks on ChemAgent."""
    
    def __init__(
        self,
        golden_queries_dir: str = "data/golden_queries",
        baseline_file: str = "benchmarks/baseline_metrics.json"
    ):
        """Initialize benchmark runner.
        
        Args:
            golden_queries_dir: Directory with golden queries
            baseline_file: Path to baseline metrics file
        """
        self.golden_queries_dir = Path(golden_queries_dir)
        self.baseline_file = Path(baseline_file)
        self.evaluator = GoldenQueryEvaluator(str(self.golden_queries_dir))
        
    def run_benchmarks(
        self,
        categories: Optional[List[str]] = None,
        iterations: int = 3
    ) -> BenchmarkSuite:
        """Run performance benchmarks.
        
        Args:
            categories: Specific categories to benchmark (all if None)
            iterations: Number of iterations per query
            
        Returns:
            BenchmarkSuite with results
        """
        print(f"🏃 Running benchmarks ({iterations} iterations)...")
        
        # Load queries
        queries = self.evaluator.load_golden_queries()
        if categories:
            queries = [q for q in queries if q["category"] in categories]
            
        results = []
        
        for query in queries:
            # Run multiple iterations
            times = []
            for i in range(iterations):
                start = time.perf_counter()
                
                try:
                    result = self.evaluator.evaluate_query(query)
                    execution_time = time.perf_counter() - start
                    times.append(execution_time)
                    
                    # Only keep first iteration's full result
                    if i == 0:
                        benchmark_result = BenchmarkResult(
                            name=query["id"],
                            category=query["category"],
                            execution_time=execution_time,
                            memory_usage_mb=0.0,  # TODO: Add memory profiling
                            success=result.success,
                            cached=False,  # First run not cached
                            steps_taken=result.steps_taken,
                            parallel_eligible=query.get("metadata", {}).get("parallel_eligible", False),
                            metadata={
                                "difficulty": query["difficulty"],
                                "iterations": iterations,
                                "min_time": 0,
                                "max_time": 0,
                                "std_dev": 0
                            }
                        )
                        results.append(benchmark_result)
                        
                except Exception as e:
                    print(f"❌ Benchmark failed for {query['id']}: {e}")
                    continue
            
            # Update with iteration statistics
            if times and results:
                results[-1].metadata["min_time"] = min(times)
                results[-1].metadata["max_time"] = max(times)
                results[-1].metadata["std_dev"] = statistics.stdev(times) if len(times) > 1 else 0
                results[-1].execution_time = statistics.mean(times)
        
        # Create suite
        suite = self._create_suite(results)
        
        # Compare with baseline
        if self.baseline_file.exists():
            suite.baseline_comparison = self._compare_with_baseline(suite)
        
        return suite
    
    def _create_suite(self, results: List[BenchmarkResult]) -> BenchmarkSuite:
        """Create benchmark suite from results."""
        execution_times = sorted([r.execution_time for r in results])
        
        suite = BenchmarkSuite(
            timestamp=datetime.now().isoformat(),
            version="1.0.0",  # TODO: Get from package
            total_benchmarks=len(results),
            results=results,
            avg_execution_time=statistics.mean(execution_times) if execution_times else 0,
            median_execution_time=statistics.median(execution_times) if execution_times else 0,
            p95_execution_time=self._percentile(execution_times, 95),
            p99_execution_time=self._percentile(execution_times, 99)
        )
        
        # Calculate by category
        by_category = {}
        for result in results:
            cat = result.category
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(result.execution_time)
        
        suite.by_category = {
            cat: {
                "avg": statistics.mean(times),
                "median": statistics.median(times),
                "min": min(times),
                "max": max(times)
            }
            for cat, times in by_category.items()
        }
        
        return suite
    
    def _percentile(self, sorted_values: List[float], percentile: int) -> float:
        """Calculate percentile."""
        if not sorted_values:
            return 0.0
        index = int(len(sorted_values) * percentile / 100)
        return sorted_values[min(index, len(sorted_values) - 1)]
    
    def _compare_with_baseline(self, suite: BenchmarkSuite) -> Dict[str, Any]:
        """Compare current results with baseline."""
        with open(self.baseline_file) as f:
            baseline = json.load(f)
        
        comparison = {
            "baseline_timestamp": baseline.get("timestamp"),
            "performance_change": suite.avg_execution_time - baseline.get("avg_execution_time", 0),
            "performance_change_pct": (
                (suite.avg_execution_time / baseline.get("avg_execution_time", 1) - 1) * 100
            ),
            "regressions": [],
            "improvements": []
        }
        
        # Check for regressions
        baseline_avg = baseline.get("avg_execution_time", 0)
        if suite.avg_execution_time > baseline_avg * 1.2:  # 20% slower
            comparison["regressions"].append({
                "metric": "avg_execution_time",
                "baseline": baseline_avg,
                "current": suite.avg_execution_time,
                "change_pct": comparison["performance_change_pct"]
            })
        
        # Check for improvements
        if suite.avg_execution_time < baseline_avg * 0.9:  # 10% faster
            comparison["improvements"].append({
                "metric": "avg_execution_time",
                "baseline": baseline_avg,
                "current": suite.avg_execution_time,
                "change_pct": comparison["performance_change_pct"]
            })
        
        return comparison
    
    def save_baseline(self, suite: BenchmarkSuite):
        """Save current results as new baseline."""
        self.baseline_file.parent.mkdir(parents=True, exist_ok=True)
        
        baseline = {
            "timestamp": suite.timestamp,
            "version": suite.version,
            "avg_execution_time": suite.avg_execution_time,
            "median_execution_time": suite.median_execution_time,
            "p95_execution_time": suite.p95_execution_time,
            "p99_execution_time": suite.p99_execution_time,
            "by_category": suite.by_category
        }
        
        with open(self.baseline_file, "w") as f:
            json.dump(baseline, f, indent=2)
        
        print(f"✓ Baseline saved to {self.baseline_file}")
    
    def generate_report(self, suite: BenchmarkSuite, output_file: Optional[Path] = None) -> str:
        """Generate benchmark report."""
        lines = []
        lines.append("=" * 80)
        lines.append("ChemAgent Performance Benchmark Report")
        lines.append("=" * 80)
        lines.append(f"Timestamp: {suite.timestamp}")
        lines.append(f"Version: {suite.version}")
        lines.append(f"Total Benchmarks: {suite.total_benchmarks}")
        lines.append("")
        
        # Overall performance
        lines.append("PERFORMANCE METRICS")
        lines.append("-" * 80)
        lines.append(f"Average Execution: {suite.avg_execution_time:.3f}s")
        lines.append(f"Median Execution:  {suite.median_execution_time:.3f}s")
        lines.append(f"P95 Execution:     {suite.p95_execution_time:.3f}s")
        lines.append(f"P99 Execution:     {suite.p99_execution_time:.3f}s")
        lines.append("")
        
        # By category
        lines.append("PERFORMANCE BY CATEGORY")
        lines.append("-" * 80)
        lines.append(f"{'Category':<20} {'Avg':>10} {'Median':>10} {'Min':>10} {'Max':>10}")
        lines.append("-" * 80)
        for category, metrics in sorted(suite.by_category.items()):
            lines.append(
                f"{category:<20} {metrics['avg']:>9.3f}s {metrics['median']:>9.3f}s "
                f"{metrics['min']:>9.3f}s {metrics['max']:>9.3f}s"
            )
        lines.append("")
        
        # Baseline comparison
        if suite.baseline_comparison:
            lines.append("BASELINE COMPARISON")
            lines.append("-" * 80)
            comp = suite.baseline_comparison
            lines.append(f"Baseline: {comp['baseline_timestamp']}")
            lines.append(f"Performance Change: {comp['performance_change']:+.3f}s ({comp['performance_change_pct']:+.1f}%)")
            
            if comp['regressions']:
                lines.append("\n⚠️  REGRESSIONS DETECTED:")
                for reg in comp['regressions']:
                    lines.append(f"  - {reg['metric']}: {reg['change_pct']:+.1f}%")
            
            if comp['improvements']:
                lines.append("\n✓ IMPROVEMENTS:")
                for imp in comp['improvements']:
                    lines.append(f"  - {imp['metric']}: {imp['change_pct']:+.1f}%")
            lines.append("")
        
        lines.append("=" * 80)
        
        report = "\n".join(lines)
        
        if output_file:
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, "w") as f:
                f.write(report)
            print(f"✓ Report saved to {output_file}")
        
        return report
