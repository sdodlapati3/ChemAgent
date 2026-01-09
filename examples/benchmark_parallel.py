"""
Benchmark parallel execution performance.

Compares serial vs parallel execution for various query patterns.
"""

import time
from typing import Dict, Any, List
import statistics

from chemagent.core.intent_parser import IntentParser
from chemagent.core.query_planner import QueryPlanner
from chemagent.core.executor import QueryExecutor


class ParallelExecutionBenchmark:
    """Benchmark parallel execution performance"""
    
    def __init__(self):
        self.parser = IntentParser()
        self.planner = QueryPlanner()
    
    def benchmark_query(self, query: str, iterations: int = 5) -> Dict[str, Any]:
        """
        Benchmark a single query with both serial and parallel execution.
        
        Args:
            query: Natural language query
            iterations: Number of iterations to average
            
        Returns:
            Benchmark results with timings and speedup
        """
        print(f"\n{'='*70}")
        print(f"Benchmarking: {query}")
        print(f"{'='*70}")
        
        # Parse and plan once
        parsed = self.parser.parse(query)
        plan = self.planner.plan(parsed)
        
        print(f"Intent: {parsed.intent_type.value}")
        print(f"Steps: {len(plan.steps)}")
        
        # Show parallel groups
        groups = plan.get_parallel_groups()
        print(f"Parallel groups: {len(groups)}")
        for i, group in enumerate(groups):
            if len(group) > 1:
                print(f"  Group {i+1}: {len(group)} steps can run in parallel")
                for step in group:
                    print(f"    - {step.tool_name}")
        
        # Serial execution
        print("\n🐌 Serial execution...")
        serial_executor = QueryExecutor(use_real_tools=True, enable_parallel=False)
        serial_times = []
        
        for i in range(iterations):
            result = serial_executor.execute(plan)
            serial_times.append(result.total_duration_ms)
            print(f"  Run {i+1}: {result.total_duration_ms}ms")
        
        serial_avg = statistics.mean(serial_times)
        serial_std = statistics.stdev(serial_times) if len(serial_times) > 1 else 0
        
        # Parallel execution
        print("\n⚡ Parallel execution...")
        parallel_executor = QueryExecutor(use_real_tools=True, enable_parallel=True, max_workers=4)
        parallel_times = []
        parallel_metrics_list = []
        
        for i in range(iterations):
            result = parallel_executor.execute(plan)
            parallel_times.append(result.total_duration_ms)
            if result.parallel_metrics:
                parallel_metrics_list.append(result.parallel_metrics)
            print(f"  Run {i+1}: {result.total_duration_ms}ms")
        
        parallel_avg = statistics.mean(parallel_times)
        parallel_std = statistics.stdev(parallel_times) if len(parallel_times) > 1 else 0
        
        # Calculate speedup
        speedup = serial_avg / parallel_avg if parallel_avg > 0 else 1.0
        
        # Results
        print(f"\n📊 Results:")
        print(f"  Serial:   {serial_avg:.1f}ms ± {serial_std:.1f}ms")
        print(f"  Parallel: {parallel_avg:.1f}ms ± {parallel_std:.1f}ms")
        print(f"  Speedup:  {speedup:.2f}x")
        
        if parallel_metrics_list:
            last_metrics = parallel_metrics_list[-1]
            print(f"\n  Parallel metrics:")
            print(f"    Steps parallelized: {last_metrics['steps_parallelized']}/{last_metrics['total_steps']}")
            print(f"    Parallelization ratio: {last_metrics['parallelization_ratio']}")
        
        if speedup >= 1.5:
            print("  ✅ Significant speedup achieved!")
        elif speedup >= 1.1:
            print("  ⚠️  Moderate speedup")
        else:
            print("  ❌ No significant speedup (query may be too simple)")
        
        return {
            "query": query,
            "intent": parsed.intent_type.value,
            "steps": len(plan.steps),
            "parallel_groups": len(groups),
            "serial_avg_ms": serial_avg,
            "serial_std_ms": serial_std,
            "parallel_avg_ms": parallel_avg,
            "parallel_std_ms": parallel_std,
            "speedup": speedup,
            "iterations": iterations,
            "parallel_metrics": parallel_metrics_list[-1] if parallel_metrics_list else None
        }
    
    def run_benchmark_suite(self) -> List[Dict[str, Any]]:
        """
        Run a comprehensive benchmark suite.
        
        Tests various query patterns to measure parallel execution performance.
        """
        print("\n" + "="*70)
        print("ChemAgent Parallel Execution Benchmark Suite")
        print("="*70)
        
        test_queries = [
            # Simple query (1 step - no parallelism expected)
            "What is CHEMBL25?",
            
            # Property calculation (3 steps - some parallelism)
            "Calculate properties of aspirin",
            
            # Similarity search (2-3 steps)
            "Find compounds similar to CC(=O)Oc1ccccc1C(=O)O",
            
            # Lipinski check (3-4 steps)
            "Check Lipinski for CHEMBL25",
            
            # Complex multi-step (if parsed correctly)
            "What are the properties and Lipinski status of CHEMBL25?",
        ]
        
        results = []
        
        for query in test_queries:
            try:
                result = self.benchmark_query(query, iterations=3)
                results.append(result)
            except Exception as e:
                print(f"\n❌ Error benchmarking query: {e}")
                continue
        
        # Summary
        print(f"\n{'='*70}")
        print("Benchmark Summary")
        print(f"{'='*70}")
        print(f"\n{'Query':<50} {'Steps':<8} {'Speedup':<10}")
        print("-" * 70)
        
        for r in results:
            speedup_str = f"{r['speedup']:.2f}x"
            print(f"{r['query'][:47]:<50} {r['steps']:<8} {speedup_str:<10}")
        
        avg_speedup = statistics.mean([r['speedup'] for r in results])
        print(f"\n{'Average speedup:':<60} {avg_speedup:.2f}x")
        
        return results


def main():
    """Run the benchmark suite"""
    benchmark = ParallelExecutionBenchmark()
    results = benchmark.run_benchmark_suite()
    
    print("\n✅ Benchmark complete!")
    print(f"Tested {len(results)} queries")
    
    # Count significant speedups
    significant = sum(1 for r in results if r['speedup'] >= 1.5)
    print(f"{significant}/{len(results)} queries achieved significant speedup (>1.5x)")


if __name__ == "__main__":
    main()
