#!/usr/bin/env python3
"""
Comprehensive Frontend Integration Tests for ChemAgent

Simulates frontend user interactions to identify issues in query 
implementation and execution process.

Usage:
    python -m tests.integration.test_comprehensive --round 1  # 100 queries
    python -m tests.integration.test_comprehensive --round 2  # 500 queries
    python -m tests.integration.test_comprehensive --round 3  # 2000 queries
"""
import argparse
import json
import logging
import signal
import sys
import time
import traceback
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from chemagent import ChemAgent, QueryResult


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@contextmanager
def timeout(seconds: int):
    """
    Context manager for query timeout.
    
    Args:
        seconds: Timeout duration in seconds
        
    Raises:
        TimeoutError: If execution exceeds timeout
    """
    def timeout_handler(signum, frame):
        raise TimeoutError(f"Query exceeded {seconds}s timeout")
    
    # Set the signal handler and alarm
    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        # Restore original handler and cancel alarm
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)


class TestResult:
    """Container for test execution results."""
    
    def __init__(
        self,
        query_id: int,
        query: str,
        intent_type: Optional[str],
        success: bool,
        execution_time_ms: float,
        error: Optional[str] = None,
        answer: Optional[str] = None,
        cached: bool = False,
        expected_intent: Optional[str] = None
    ):
        self.query_id = query_id
        self.query = query
        self.intent_type = intent_type
        self.success = success
        self.execution_time_ms = execution_time_ms
        self.error = error
        self.answer = answer
        self.cached = cached
        self.expected_intent = expected_intent
        self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "query_id": self.query_id,
            "query": self.query,
            "intent_type": self.intent_type,
            "expected_intent": self.expected_intent,
            "success": self.success,
            "execution_time_ms": self.execution_time_ms,
            "error": self.error,
            "answer": self.answer[:500] if self.answer else None,  # Truncate
            "cached": self.cached,
            "timestamp": self.timestamp
        }


class TestExecutor:
    """Execute test queries and collect results."""
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.agent = ChemAgent()
        self.results: List[TestResult] = []
    
    def run_query(
        self,
        query_id: int,
        query: str,
        expected_intent: Optional[str] = None,
        timeout_seconds: int = 30,
        max_retries: int = 2
    ) -> TestResult:
        """Execute a single query and capture results with timeout and retry."""
        logger.info(f"[{query_id}] Testing: {query[:80]}...")
        
        start_time = time.time()
        last_error = None
        
        # Try with retries for transient failures
        for attempt in range(max_retries):
            try:
                # Execute with timeout protection
                with timeout(timeout_seconds):
                    result: QueryResult = self.agent.query(query)
                
                execution_time = (time.time() - start_time) * 1000
                
                test_result = TestResult(
                    query_id=query_id,
                    query=query,
                    intent_type=result.intent_type,
                    success=result.success,
                    execution_time_ms=result.execution_time_ms or execution_time,
                    error=result.error,
                    answer=result.answer,
                    cached=result.cached,
                    expected_intent=expected_intent
                )
                
                # Log issues
                if not result.success:
                    logger.warning(f"[{query_id}] FAILED: {result.error}")
                elif expected_intent and result.intent_type != expected_intent:
                    logger.warning(
                        f"[{query_id}] Intent mismatch: "
                        f"expected={expected_intent}, got={result.intent_type}"
                    )
                elif result.execution_time_ms > 10000:
                    logger.warning(
                        f"[{query_id}] SLOW: {result.execution_time_ms:.0f}ms"
                    )
                
                return test_result
                
            except TimeoutError as e:
                execution_time = (time.time() - start_time) * 1000
                logger.error(f"[{query_id}] TIMEOUT after {timeout_seconds}s")
                
                return TestResult(
                    query_id=query_id,
                    query=query,
                    intent_type=None,
                    success=False,
                    execution_time_ms=execution_time,
                    error=f"TIMEOUT: Query exceeded {timeout_seconds}s",
                    answer=None,
                    cached=False,
                    expected_intent=expected_intent
                )
            
            except Exception as e:
                last_error = e
                # Only retry on network-related errors, not logic errors
                error_str = str(e).lower()
                is_retryable = any(keyword in error_str for keyword in 
                                  ['timeout', 'connection', 'network', 'unavailable', 'rate limit'])
                
                if attempt < max_retries - 1 and is_retryable:
                    wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s
                    logger.warning(
                        f"[{query_id}] Attempt {attempt + 1} failed (retryable), "
                        f"retrying in {wait_time}s: {str(e)[:100]}"
                    )
                    time.sleep(wait_time)
                    continue
                else:
                    # Non-retryable or final attempt
                    execution_time = (time.time() - start_time) * 1000
                    logger.error(f"[{query_id}] EXCEPTION: {str(e)}")
                    logger.debug(traceback.format_exc())
                    
                    return TestResult(
                        query_id=query_id,
                        query=query,
                        intent_type=None,
                        success=False,
                        execution_time_ms=execution_time,
                        error=f"{type(e).__name__}: {str(e)}",
                        answer=None,
                        cached=False,
                        expected_intent=expected_intent
                    )
        
        # Should never reach here, but just in case
        return TestResult(
            query_id=query_id,
            query=query,
            intent_type=None,
            success=False,
            execution_time_ms=(time.time() - start_time) * 1000,
            error=f"Max retries ({max_retries}) exceeded",
            answer=None,
            cached=False,
            expected_intent=expected_intent
        )
    
    def run_batch(
        self,
        queries: List[Dict[str, str]],
        round_num: int
    ):
        """Execute a batch of queries."""
        logger.info(f"\n{'='*60}")
        logger.info(f"Starting Round {round_num} - {len(queries)} queries")
        logger.info(f"{'='*60}\n")
        
        start_time = time.time()
        
        for i, query_data in enumerate(queries, 1):
            query = query_data["query"]
            expected_intent = query_data.get("expected_intent")
            
            result = self.run_query(i, query, expected_intent)
            self.results.append(result)
            
            # Progress update every 50 queries
            if i % 50 == 0:
                elapsed = time.time() - start_time
                success_count = sum(1 for r in self.results if r.success)
                success_rate = (success_count / len(self.results)) * 100
                logger.info(
                    f"Progress: {i}/{len(queries)} queries "
                    f"({success_rate:.1f}% success, {elapsed:.1f}s elapsed)"
                )
        
        # Save results
        self._save_results(round_num)
        
        # Generate report
        self._generate_report(round_num)
    
    def _save_results(self, round_num: int):
        """Save test results to JSON file."""
        output_file = self.output_dir / f"round{round_num}_results.json"
        
        results_dict = {
            "round": round_num,
            "total_queries": len(self.results),
            "timestamp": datetime.now().isoformat(),
            "results": [r.to_dict() for r in self.results]
        }
        
        with open(output_file, "w") as f:
            json.dump(results_dict, f, indent=2)
        
        logger.info(f"\n✓ Results saved to: {output_file}")
    
    def _generate_report(self, round_num: int):
        """Generate enhanced summary report with detailed metrics."""
        total = len(self.results)
        successful = sum(1 for r in self.results if r.success)
        failed = total - successful
        
        # Calculate performance metrics
        avg_time = sum(r.execution_time_ms for r in self.results) / total
        max_time = max(r.execution_time_ms for r in self.results)
        min_time = min(r.execution_time_ms for r in self.results)
        
        # Find slowest queries
        slowest = sorted(self.results, key=lambda r: r.execution_time_ms, reverse=True)[:10]
        
        # Timeout and retry statistics
        timeout_count = sum(1 for r in self.results if r.error and "TIMEOUT" in str(r.error))
        retry_count = sum(1 for r in self.results if r.error and "Attempt" in str(r.error))
        
        # Cache statistics
        cached_count = sum(1 for r in self.results if r.cached)
        cache_rate = (cached_count / total * 100) if total > 0 else 0
        
        # Count by intent type
        intent_counts = {}
        intent_success_rates = {}
        for r in self.results:
            intent = r.intent_type or "unknown"
            intent_counts[intent] = intent_counts.get(intent, 0) + 1
            
            # Track success rate per intent
            if intent not in intent_success_rates:
                intent_success_rates[intent] = {"success": 0, "total": 0}
            intent_success_rates[intent]["total"] += 1
            if r.success:
                intent_success_rates[intent]["success"] += 1
        
        # Intent accuracy (if expected intent provided)
        intent_matches = sum(
            1 for r in self.results 
            if r.expected_intent and r.intent_type == r.expected_intent
        )
        queries_with_expected = sum(
            1 for r in self.results if r.expected_intent
        )
        
        # Error analysis - detailed breakdown
        error_types = {}
        error_examples = {}
        for r in self.results:
            if r.error:
                # Extract error type (first part before colon)
                error_parts = str(r.error).split(":")
                error_key = error_parts[0].strip()
                
                error_types[error_key] = error_types.get(error_key, 0) + 1
                
                # Store first example of each error type
                if error_key not in error_examples:
                    error_examples[error_key] = (r.query[:60], r.error[:150])
        
        # Generate enhanced report
        report = f"""
{'='*70}
COMPREHENSIVE TEST REPORT - ROUND {round_num}
{'='*70}

Overall Results:
  Total Queries:    {total}
  Successful:       {successful} ({successful/total*100:.1f}%)
  Failed:           {failed} ({failed/total*100:.1f}%)

Performance Metrics:
  Average Time:     {avg_time:.2f}ms
  Min Time:         {min_time:.2f}ms
  Max Time:         {max_time:.2f}ms
  
Cache Statistics:
  Cached Results:   {cached_count} ({cache_rate:.1f}%)
  Fresh Queries:    {total - cached_count} ({100-cache_rate:.1f}%)

Reliability Metrics:
  Timeouts:         {timeout_count}
  Retries Used:     {retry_count}
  
Intent Recognition:
"""
        
        for intent, count in sorted(intent_counts.items(), key=lambda x: -x[1]):
            # Calculate success rate for this intent
            stats = intent_success_rates[intent]
            success_pct = (stats["success"] / stats["total"] * 100) if stats["total"] > 0 else 0
            report += f"  {intent:25s} {count:4d} queries ({success_pct:.0f}% success)\n"
        
        if queries_with_expected > 0:
            accuracy = (intent_matches / queries_with_expected) * 100
            report += f"\n  Intent Accuracy:  {accuracy:.1f}% ({intent_matches}/{queries_with_expected})\n"
        
        if slowest:
            report += f"\nSlowest Queries (Top 10):\n"
            for i, r in enumerate(slowest, 1):
                status = "✓" if r.success else "✗"
                report += f"  {i:2d}. {status} {r.execution_time_ms:7.0f}ms - {r.query[:50]}\n"
        
        if error_types:
            report += f"\nError Analysis (by type):\n"
            for error_type, count in sorted(error_types.items(), key=lambda x: -x[1]):
                report += f"  {error_type:40s} {count:4d} occurrences\n"
                if error_type in error_examples:
                    ex_query, ex_error = error_examples[error_type]
                    report += f"    Example: \"{ex_query}...\"\n"
                    report += f"    → {ex_error}...\n"
        
        # Failed queries sample
        failed_queries = [r for r in self.results if not r.success]
        if failed_queries:
            report += f"\nSample Failed Queries (first 10):\n"
            for r in failed_queries[:10]:
                report += f"  [{r.query_id}] {r.query[:60]}...\n"
                report += f"      Error: {r.error}\n"
        
        report += f"\n{'='*70}\n"
        
        # Print and save report
        print(report)
        
        report_file = self.output_dir / f"round{round_num}_report.txt"
        with open(report_file, "w") as f:
            f.write(report)
        
        logger.info(f"✓ Report saved to: {report_file}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run comprehensive frontend integration tests"
    )
    parser.add_argument(
        "--round",
        type=int,
        choices=[1, 2, 3],
        required=True,
        help="Test round: 1 (100 queries), 2 (500 queries), 3 (2000 queries)"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("tests/integration/test_results"),
        help="Output directory for results"
    )
    
    args = parser.parse_args()
    
    # Import query generator
    from tests.integration.query_generator import generate_queries
    
    # Generate queries for the specified round
    queries = generate_queries(args.round)
    
    logger.info(f"\nGenerated {len(queries)} queries for Round {args.round}")
    
    # Execute tests
    executor = TestExecutor(args.output_dir)
    executor.run_batch(queries, args.round)
    
    logger.info("\n✓ Testing complete!")


if __name__ == "__main__":
    main()
