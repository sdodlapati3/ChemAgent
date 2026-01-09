"""
Tests for performance monitoring and metrics collection.
"""

import pytest
from datetime import datetime
from pathlib import Path
import json
import tempfile

from chemagent.monitoring import (
    QueryMetrics,
    PerformanceMonitor,
    get_monitor,
    set_monitor
)


class TestQueryMetrics:
    """Test QueryMetrics dataclass"""
    
    def test_initialization(self):
        """Test basic initialization"""
        metrics = QueryMetrics(
            query="What is CHEMBL25?",
            intent_type="compound_lookup",
            timestamp=datetime.now(),
            total_duration_ms=15.5,
            steps_count=1,
            steps_completed=1,
            steps_failed=0,
            execution_status="completed"
        )
        
        assert metrics.query == "What is CHEMBL25?"
        assert metrics.intent_type == "compound_lookup"
        assert metrics.total_duration_ms == 15.5
        assert metrics.execution_status == "completed"
        assert metrics.cache_hit is False
        assert metrics.parallel_enabled is True
    
    def test_to_dict(self):
        """Test conversion to dictionary"""
        now = datetime.now()
        metrics = QueryMetrics(
            query="Calculate properties",
            intent_type="property_calculation",
            timestamp=now,
            total_duration_ms=100.0,
            steps_count=3,
            steps_completed=3,
            steps_failed=0,
            execution_status="completed",
            cache_hit=True,
            parallel_speedup=2.5,
            tools_used=["tool1", "tool2"]
        )
        
        result = metrics.to_dict()
        
        assert result["query"] == "Calculate properties"
        assert result["intent_type"] == "property_calculation"
        assert result["timestamp"] == now.isoformat()
        assert result["total_duration_ms"] == 100.0
        assert result["cache_hit"] is True
        assert result["parallel_speedup"] == 2.5
        assert result["tools_used"] == ["tool1", "tool2"]


class TestPerformanceMonitor:
    """Test PerformanceMonitor functionality"""
    
    def test_initialization(self):
        """Test monitor initialization"""
        monitor = PerformanceMonitor()
        
        assert len(monitor.query_history) == 0
        assert len(monitor.tool_stats) == 0
        assert len(monitor.intent_stats) == 0
        assert monitor.parallel_stats["queries_with_parallel"] == 0
    
    def test_record_single_query(self):
        """Test recording a single query"""
        monitor = PerformanceMonitor()
        
        metrics = QueryMetrics(
            query="What is CHEMBL25?",
            intent_type="compound_lookup",
            timestamp=datetime.now(),
            total_duration_ms=15.0,
            steps_count=1,
            steps_completed=1,
            steps_failed=0,
            execution_status="completed"
        )
        
        monitor.record_query(metrics)
        
        assert len(monitor.query_history) == 1
        assert monitor.intent_stats["compound_lookup"]["count"] == 1
        assert monitor.intent_stats["compound_lookup"]["total_duration_ms"] == 15.0
    
    def test_record_multiple_queries(self):
        """Test recording multiple queries"""
        monitor = PerformanceMonitor()
        
        for i in range(5):
            metrics = QueryMetrics(
                query=f"Query {i}",
                intent_type="compound_lookup",
                timestamp=datetime.now(),
                total_duration_ms=10.0 + i,
                steps_count=1,
                steps_completed=1,
                steps_failed=0,
                execution_status="completed"
            )
            monitor.record_query(metrics)
        
        assert len(monitor.query_history) == 5
        assert monitor.intent_stats["compound_lookup"]["count"] == 5
        assert monitor.intent_stats["compound_lookup"]["avg_duration_ms"] == 12.0
    
    def test_cache_hit_tracking(self):
        """Test cache hit tracking"""
        monitor = PerformanceMonitor()
        
        # Record cache hit
        monitor.record_query(QueryMetrics(
            query="Query 1",
            intent_type="compound_lookup",
            timestamp=datetime.now(),
            total_duration_ms=2.0,
            steps_count=1,
            steps_completed=1,
            steps_failed=0,
            execution_status="completed",
            cache_hit=True
        ))
        
        # Record cache miss
        monitor.record_query(QueryMetrics(
            query="Query 2",
            intent_type="compound_lookup",
            timestamp=datetime.now(),
            total_duration_ms=50.0,
            steps_count=1,
            steps_completed=1,
            steps_failed=0,
            execution_status="completed",
            cache_hit=False
        ))
        
        summary = monitor.get_summary()
        assert summary["cache_hit_rate"] == 50.0
    
    def test_parallel_stats_tracking(self):
        """Test parallel execution stats tracking"""
        monitor = PerformanceMonitor()
        
        # Query with good speedup
        monitor.record_query(QueryMetrics(
            query="Parallel query 1",
            intent_type="property_calculation",
            timestamp=datetime.now(),
            total_duration_ms=50.0,
            steps_count=3,
            steps_completed=3,
            steps_failed=0,
            execution_status="completed",
            parallel_enabled=True,
            parallel_speedup=2.5,
            parallelization_ratio=0.67
        ))
        
        # Query with minor speedup
        monitor.record_query(QueryMetrics(
            query="Parallel query 2",
            intent_type="property_calculation",
            timestamp=datetime.now(),
            total_duration_ms=45.0,
            steps_count=3,
            steps_completed=3,
            steps_failed=0,
            execution_status="completed",
            parallel_enabled=True,
            parallel_speedup=1.1,
            parallelization_ratio=0.33
        ))
        
        summary = monitor.get_summary()
        assert summary["parallel_stats"]["queries_with_parallel"] == 2
        assert summary["parallel_stats"]["queries_benefited"] == 1  # > 1.2 speedup
        assert summary["parallel_stats"]["avg_speedup"] == 1.8  # (2.5 + 1.1) / 2
    
    def test_failed_query_tracking(self):
        """Test failed query tracking"""
        monitor = PerformanceMonitor()
        
        # Successful query
        monitor.record_query(QueryMetrics(
            query="Success",
            intent_type="compound_lookup",
            timestamp=datetime.now(),
            total_duration_ms=15.0,
            steps_count=1,
            steps_completed=1,
            steps_failed=0,
            execution_status="completed"
        ))
        
        # Failed query
        monitor.record_query(QueryMetrics(
            query="Failure",
            intent_type="compound_lookup",
            timestamp=datetime.now(),
            total_duration_ms=5.0,
            steps_count=1,
            steps_completed=0,
            steps_failed=1,
            execution_status="failed",
            error_message="Tool not found"
        ))
        
        summary = monitor.get_summary()
        assert summary["total_queries"] == 2
        assert summary["successful_queries"] == 1
        assert summary["failed_queries"] == 1
        assert summary["success_rate"] == 50.0
        
        failed = monitor.get_failed_queries()
        assert len(failed) == 1
        assert failed[0]["error_message"] == "Tool not found"
    
    def test_get_slow_queries(self):
        """Test slow query detection"""
        monitor = PerformanceMonitor()
        
        # Fast queries
        for i in range(3):
            monitor.record_query(QueryMetrics(
                query=f"Fast {i}",
                intent_type="compound_lookup",
                timestamp=datetime.now(),
                total_duration_ms=50.0,
                steps_count=1,
                steps_completed=1,
                steps_failed=0,
                execution_status="completed"
            ))
        
        # Slow query
        monitor.record_query(QueryMetrics(
            query="Slow query",
            intent_type="similarity_search",
            timestamp=datetime.now(),
            total_duration_ms=1500.0,
            steps_count=5,
            steps_completed=5,
            steps_failed=0,
            execution_status="completed"
        ))
        
        slow_queries = monitor.get_slow_queries(threshold_ms=1000.0)
        assert len(slow_queries) == 1
        assert slow_queries[0]["query"] == "Slow query"
        assert slow_queries[0]["total_duration_ms"] == 1500.0
    
    def test_parallel_efficiency_analysis(self):
        """Test parallel execution efficiency analysis"""
        monitor = PerformanceMonitor()
        
        # Add queries with different speedups
        speedups = [1.2, 1.8, 2.5, 3.2]
        for speedup in speedups:
            monitor.record_query(QueryMetrics(
                query=f"Query with {speedup}x speedup",
                intent_type="property_calculation",
                timestamp=datetime.now(),
                total_duration_ms=100.0 / speedup,
                steps_count=4,
                steps_completed=4,
                steps_failed=0,
                execution_status="completed",
                parallel_enabled=True,
                parallel_speedup=speedup,
                parallelization_ratio=0.5
            ))
        
        efficiency = monitor.get_parallel_efficiency()
        
        assert efficiency["queries_analyzed"] == 4
        assert efficiency["avg_speedup"] == sum(speedups) / len(speedups)
        assert efficiency["max_speedup"] == 3.2
        assert efficiency["min_speedup"] == 1.2
        assert efficiency["distribution"]["1.0x - 1.5x"] == 1
        assert efficiency["distribution"]["1.5x - 2.0x"] == 1
        assert efficiency["distribution"]["2.0x - 3.0x"] == 1
        assert efficiency["distribution"]["3.0x+"] == 1
    
    def test_cache_efficiency_analysis(self):
        """Test cache efficiency analysis"""
        monitor = PerformanceMonitor()
        
        # Cache hits (fast)
        for i in range(3):
            monitor.record_query(QueryMetrics(
                query=f"Cached {i}",
                intent_type="compound_lookup",
                timestamp=datetime.now(),
                total_duration_ms=2.0,
                steps_count=1,
                steps_completed=1,
                steps_failed=0,
                execution_status="completed",
                cache_hit=True
            ))
        
        # Cache misses (slow)
        for i in range(2):
            monitor.record_query(QueryMetrics(
                query=f"Uncached {i}",
                intent_type="compound_lookup",
                timestamp=datetime.now(),
                total_duration_ms=50.0,
                steps_count=1,
                steps_completed=1,
                steps_failed=0,
                execution_status="completed",
                cache_hit=False
            ))
        
        cache_eff = monitor.get_cache_efficiency()
        
        assert cache_eff["total_queries"] == 5
        assert cache_eff["cache_hits"] == 3
        assert cache_eff["cache_misses"] == 2
        assert cache_eff["hit_rate"] == 60.0
        assert cache_eff["avg_hit_time_ms"] == 2.0
        assert cache_eff["avg_miss_time_ms"] == 50.0
        assert cache_eff["speedup_factor"] == 25.0  # 50 / 2
        assert cache_eff["estimated_time_saved_ms"] > 0
    
    def test_export_and_load_metrics(self):
        """Test exporting and loading metrics"""
        monitor = PerformanceMonitor()
        
        # Record some metrics
        for i in range(3):
            monitor.record_query(QueryMetrics(
                query=f"Query {i}",
                intent_type="compound_lookup",
                timestamp=datetime.now(),
                total_duration_ms=10.0 + i,
                steps_count=1,
                steps_completed=1,
                steps_failed=0,
                execution_status="completed"
            ))
        
        # Export to temp file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            export_path = f.name
        
        try:
            monitor.export_metrics(export_path)
            
            # Verify file exists and has content
            assert Path(export_path).exists()
            data = json.loads(Path(export_path).read_text())
            
            assert "summary" in data
            assert "query_history" in data
            assert len(data["query_history"]) == 3
            assert data["summary"]["total_queries"] == 3
        finally:
            Path(export_path).unlink()
    
    def test_clear_metrics(self):
        """Test clearing all metrics"""
        monitor = PerformanceMonitor()
        
        # Record some metrics
        monitor.record_query(QueryMetrics(
            query="Query",
            intent_type="compound_lookup",
            timestamp=datetime.now(),
            total_duration_ms=10.0,
            steps_count=1,
            steps_completed=1,
            steps_failed=0,
            execution_status="completed"
        ))
        
        assert len(monitor.query_history) == 1
        
        monitor.clear()
        
        assert len(monitor.query_history) == 0
        assert len(monitor.intent_stats) == 0
        assert len(monitor.tool_stats) == 0
        assert monitor.parallel_stats["queries_with_parallel"] == 0


class TestGlobalMonitor:
    """Test global monitor instance management"""
    
    def test_get_monitor(self):
        """Test getting global monitor"""
        monitor = get_monitor()
        assert isinstance(monitor, PerformanceMonitor)
        
        # Should return same instance
        monitor2 = get_monitor()
        assert monitor is monitor2
    
    def test_set_monitor(self):
        """Test setting global monitor"""
        custom_monitor = PerformanceMonitor()
        set_monitor(custom_monitor)
        
        retrieved = get_monitor()
        assert retrieved is custom_monitor


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
