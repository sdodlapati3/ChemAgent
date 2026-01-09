"""
Performance monitoring and metrics collection for ChemAgent.

Tracks execution times, parallel execution efficiency, cache performance,
and API usage patterns for production observability and optimization.
"""

import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from collections import defaultdict
import json
from pathlib import Path


@dataclass
class QueryMetrics:
    """Metrics for a single query execution"""
    query: str
    intent_type: str
    timestamp: datetime
    total_duration_ms: float
    steps_count: int
    steps_completed: int
    steps_failed: int
    execution_status: str
    cache_hit: bool = False
    parallel_enabled: bool = True
    parallel_speedup: float = 1.0
    parallelization_ratio: float = 0.0
    api_calls_count: int = 0
    tools_used: List[str] = field(default_factory=list)
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "query": self.query,
            "intent_type": self.intent_type,
            "timestamp": self.timestamp.isoformat(),
            "total_duration_ms": self.total_duration_ms,
            "steps_count": self.steps_count,
            "steps_completed": self.steps_completed,
            "steps_failed": self.steps_failed,
            "execution_status": self.execution_status,
            "cache_hit": self.cache_hit,
            "parallel_enabled": self.parallel_enabled,
            "parallel_speedup": self.parallel_speedup,
            "parallelization_ratio": self.parallelization_ratio,
            "api_calls_count": self.api_calls_count,
            "tools_used": self.tools_used,
            "error_message": self.error_message
        }


class PerformanceMonitor:
    """
    Monitor and track ChemAgent performance metrics.
    
    Collects execution statistics, identifies bottlenecks,
    and provides insights for optimization.
    """
    
    def __init__(self, metrics_file: Optional[str] = None):
        """
        Initialize performance monitor.
        
        Args:
            metrics_file: Optional file path to persist metrics
        """
        self.metrics_file = Path(metrics_file) if metrics_file else None
        self.query_history: List[QueryMetrics] = []
        self.tool_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "count": 0,
            "total_duration_ms": 0.0,
            "failures": 0,
            "avg_duration_ms": 0.0
        })
        self.intent_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "count": 0,
            "total_duration_ms": 0.0,
            "failures": 0,
            "cache_hits": 0,
            "avg_duration_ms": 0.0
        })
        self.parallel_stats = {
            "queries_with_parallel": 0,
            "total_speedup": 0.0,
            "avg_speedup": 1.0,
            "queries_benefited": 0  # speedup > 1.2
        }
    
    def record_query(self, metrics: QueryMetrics) -> None:
        """
        Record metrics for a query execution.
        
        Args:
            metrics: QueryMetrics instance
        """
        self.query_history.append(metrics)
        
        # Update intent stats
        intent_stat = self.intent_stats[metrics.intent_type]
        intent_stat["count"] += 1
        intent_stat["total_duration_ms"] += metrics.total_duration_ms
        if metrics.execution_status == "failed":
            intent_stat["failures"] += 1
        if metrics.cache_hit:
            intent_stat["cache_hits"] += 1
        intent_stat["avg_duration_ms"] = (
            intent_stat["total_duration_ms"] / intent_stat["count"]
        )
        
        # Update tool stats
        for tool_name in metrics.tools_used:
            tool_stat = self.tool_stats[tool_name]
            tool_stat["count"] += 1
            # We don't have per-tool duration here, would need step-level metrics
        
        # Update parallel stats
        if metrics.parallel_enabled and metrics.parallel_speedup > 1.0:
            self.parallel_stats["queries_with_parallel"] += 1
            self.parallel_stats["total_speedup"] += metrics.parallel_speedup
            self.parallel_stats["avg_speedup"] = (
                self.parallel_stats["total_speedup"] / 
                self.parallel_stats["queries_with_parallel"]
            )
            if metrics.parallel_speedup > 1.2:
                self.parallel_stats["queries_benefited"] += 1
        
        # Persist if file specified
        if self.metrics_file:
            self._persist_metrics()
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary statistics.
        
        Returns:
            Dictionary with summary metrics
        """
        total_queries = len(self.query_history)
        if total_queries == 0:
            return {"message": "No queries recorded yet"}
        
        failed_queries = sum(
            1 for m in self.query_history 
            if m.execution_status == "failed"
        )
        cache_hits = sum(1 for m in self.query_history if m.cache_hit)
        
        total_duration = sum(m.total_duration_ms for m in self.query_history)
        avg_duration = total_duration / total_queries if total_queries > 0 else 0
        
        return {
            "total_queries": total_queries,
            "successful_queries": total_queries - failed_queries,
            "failed_queries": failed_queries,
            "success_rate": (total_queries - failed_queries) / total_queries * 100,
            "cache_hit_rate": cache_hits / total_queries * 100 if total_queries > 0 else 0,
            "avg_duration_ms": avg_duration,
            "total_duration_ms": total_duration,
            "parallel_stats": self.parallel_stats,
            "intent_distribution": {
                intent: stats["count"] 
                for intent, stats in self.intent_stats.items()
            },
            "top_tools": sorted(
                [(tool, stats["count"]) for tool, stats in self.tool_stats.items()],
                key=lambda x: x[1],
                reverse=True
            )[:10]
        }
    
    def get_intent_stats(self, intent_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Get statistics for specific intent type or all intents.
        
        Args:
            intent_type: Optional specific intent to get stats for
            
        Returns:
            Intent statistics dictionary
        """
        if intent_type:
            return dict(self.intent_stats.get(intent_type, {}))
        return dict(self.intent_stats)
    
    def get_tool_stats(self, tool_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get statistics for specific tool or all tools.
        
        Args:
            tool_name: Optional specific tool to get stats for
            
        Returns:
            Tool statistics dictionary
        """
        if tool_name:
            return dict(self.tool_stats.get(tool_name, {}))
        return dict(self.tool_stats)
    
    def get_slow_queries(self, threshold_ms: float = 1000.0) -> List[Dict[str, Any]]:
        """
        Get queries that took longer than threshold.
        
        Args:
            threshold_ms: Duration threshold in milliseconds
            
        Returns:
            List of slow query metrics
        """
        slow_queries = [
            m for m in self.query_history 
            if m.total_duration_ms > threshold_ms
        ]
        return [q.to_dict() for q in sorted(
            slow_queries,
            key=lambda x: x.total_duration_ms,
            reverse=True
        )]
    
    def get_failed_queries(self) -> List[Dict[str, Any]]:
        """
        Get all failed queries.
        
        Returns:
            List of failed query metrics
        """
        failed = [
            m for m in self.query_history 
            if m.execution_status == "failed"
        ]
        return [q.to_dict() for q in failed]
    
    def get_parallel_efficiency(self) -> Dict[str, Any]:
        """
        Analyze parallel execution efficiency.
        
        Returns:
            Parallel execution analysis
        """
        parallel_queries = [
            m for m in self.query_history 
            if m.parallel_enabled and m.parallel_speedup > 1.0
        ]
        
        if not parallel_queries:
            return {
                "message": "No parallel executions recorded",
                "total_queries": len(self.query_history)
            }
        
        speedups = [q.parallel_speedup for q in parallel_queries]
        ratios = [q.parallelization_ratio for q in parallel_queries]
        
        return {
            "queries_analyzed": len(parallel_queries),
            "avg_speedup": sum(speedups) / len(speedups),
            "max_speedup": max(speedups),
            "min_speedup": min(speedups),
            "avg_parallelization_ratio": sum(ratios) / len(ratios) * 100,
            "queries_with_significant_speedup": sum(
                1 for s in speedups if s > 1.5
            ),
            "distribution": {
                "1.0x - 1.5x": sum(1 for s in speedups if 1.0 <= s < 1.5),
                "1.5x - 2.0x": sum(1 for s in speedups if 1.5 <= s < 2.0),
                "2.0x - 3.0x": sum(1 for s in speedups if 2.0 <= s < 3.0),
                "3.0x+": sum(1 for s in speedups if s >= 3.0)
            }
        }
    
    def get_cache_efficiency(self) -> Dict[str, Any]:
        """
        Analyze cache performance.
        
        Returns:
            Cache efficiency analysis
        """
        if not self.query_history:
            return {"message": "No queries recorded"}
        
        total = len(self.query_history)
        hits = sum(1 for m in self.query_history if m.cache_hit)
        misses = total - hits
        
        # Calculate time saved by cache
        cache_hit_queries = [m for m in self.query_history if m.cache_hit]
        cache_miss_queries = [m for m in self.query_history if not m.cache_hit]
        
        avg_hit_time = (
            sum(m.total_duration_ms for m in cache_hit_queries) / len(cache_hit_queries)
            if cache_hit_queries else 0
        )
        avg_miss_time = (
            sum(m.total_duration_ms for m in cache_miss_queries) / len(cache_miss_queries)
            if cache_miss_queries else 0
        )
        
        estimated_savings = hits * (avg_miss_time - avg_hit_time) if avg_miss_time > avg_hit_time else 0
        
        return {
            "total_queries": total,
            "cache_hits": hits,
            "cache_misses": misses,
            "hit_rate": hits / total * 100 if total > 0 else 0,
            "avg_hit_time_ms": avg_hit_time,
            "avg_miss_time_ms": avg_miss_time,
            "speedup_factor": avg_miss_time / avg_hit_time if avg_hit_time > 0 else 1.0,
            "estimated_time_saved_ms": estimated_savings
        }
    
    def export_metrics(self, filepath: str) -> None:
        """
        Export all metrics to JSON file.
        
        Args:
            filepath: Path to export file
        """
        export_data = {
            "export_timestamp": datetime.now().isoformat(),
            "summary": self.get_summary(),
            "intent_stats": dict(self.intent_stats),
            "tool_stats": dict(self.tool_stats),
            "parallel_efficiency": self.get_parallel_efficiency(),
            "cache_efficiency": self.get_cache_efficiency(),
            "query_history": [m.to_dict() for m in self.query_history]
        }
        
        Path(filepath).write_text(json.dumps(export_data, indent=2))
    
    def _persist_metrics(self) -> None:
        """Persist metrics to file (append mode)"""
        if not self.metrics_file:
            return
        
        # Append latest metric
        if self.query_history:
            latest = self.query_history[-1]
            with open(self.metrics_file, 'a') as f:
                f.write(json.dumps(latest.to_dict()) + '\n')
    
    def load_metrics(self, filepath: str) -> None:
        """
        Load metrics from JSON file.
        
        Args:
            filepath: Path to metrics file
        """
        content = Path(filepath).read_text()
        for line in content.strip().split('\n'):
            if line:
                data = json.loads(line)
                metrics = QueryMetrics(
                    query=data["query"],
                    intent_type=data["intent_type"],
                    timestamp=datetime.fromisoformat(data["timestamp"]),
                    total_duration_ms=data["total_duration_ms"],
                    steps_count=data["steps_count"],
                    steps_completed=data["steps_completed"],
                    steps_failed=data["steps_failed"],
                    execution_status=data["execution_status"],
                    cache_hit=data.get("cache_hit", False),
                    parallel_enabled=data.get("parallel_enabled", True),
                    parallel_speedup=data.get("parallel_speedup", 1.0),
                    parallelization_ratio=data.get("parallelization_ratio", 0.0),
                    api_calls_count=data.get("api_calls_count", 0),
                    tools_used=data.get("tools_used", []),
                    error_message=data.get("error_message")
                )
                self.record_query(metrics)
    
    def clear(self) -> None:
        """Clear all recorded metrics"""
        self.query_history.clear()
        self.tool_stats.clear()
        self.intent_stats.clear()
        self.parallel_stats = {
            "queries_with_parallel": 0,
            "total_speedup": 0.0,
            "avg_speedup": 1.0,
            "queries_benefited": 0
        }


# Global monitor instance
_global_monitor: Optional[PerformanceMonitor] = None


def get_monitor() -> PerformanceMonitor:
    """Get or create global performance monitor"""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = PerformanceMonitor()
    return _global_monitor


def set_monitor(monitor: PerformanceMonitor) -> None:
    """Set global performance monitor"""
    global _global_monitor
    _global_monitor = monitor
