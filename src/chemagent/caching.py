"""
Result caching for ChemAgent.

Caches API responses and computation results to improve performance
and reduce redundant API calls.
"""

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Dict, Optional

from diskcache import Cache


class ResultCache:
    """
    Cache for query execution results.
    
    Uses disk-based cache with configurable TTL (time-to-live).
    """
    
    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        ttl: int = 3600  # 1 hour default
    ):
        """
        Initialize cache.
        
        Args:
            cache_dir: Cache directory (default: ~/.chemagent/cache)
            ttl: Time-to-live in seconds (default: 3600 = 1 hour)
        """
        if cache_dir is None:
            cache_dir = Path.home() / ".chemagent" / "cache"
        
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.cache = Cache(str(cache_dir))
        self.ttl = ttl
        self._hits = 0
        self._misses = 0
    
    def get(
        self,
        tool_name: str,
        args: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached result.
        
        Args:
            tool_name: Name of the tool
            args: Tool arguments
            ttl: Optional custom TTL
            
        Returns:
            Cached result or None if not found/expired
        """
        key = self._make_key(tool_name, args)
        
        try:
            result = self.cache.get(key)
            if result is not None:
                self._hits += 1
                return result
        except Exception:
            pass
        
        self._misses += 1
        return None
    
    def set(
        self,
        tool_name: str,
        args: Dict[str, Any],
        result: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> None:
        """
        Store result in cache.
        
        Args:
            tool_name: Name of the tool
            args: Tool arguments
            result: Result to cache
            ttl: Optional custom TTL (uses default if None)
        """
        key = self._make_key(tool_name, args)
        expire_time = ttl or self.ttl
        
        try:
            self.cache.set(key, result, expire=expire_time)
        except Exception:
            # Silently fail on cache errors
            pass
    
    def _make_key(self, tool_name: str, args: Dict[str, Any]) -> str:
        """
        Create cache key from tool name and arguments.
        
        Args:
            tool_name: Name of the tool
            args: Tool arguments
            
        Returns:
            Cache key string
        """
        # Create deterministic string representation
        args_str = json.dumps(args, sort_keys=True)
        combined = f"{tool_name}:{args_str}"
        
        # Hash to keep keys short
        return hashlib.sha256(combined.encode()).hexdigest()
    
    def clear(self) -> None:
        """Clear all cached results."""
        self.cache.clear()
    
    def stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dict with hits, misses, hit rate, size
        """
        total = self._hits + self._misses
        hit_rate = self._hits / total if total > 0 else 0.0
        
        return {
            "hits": self._hits,
            "misses": self._misses,
            "total_requests": total,
            "hit_rate": hit_rate,
            "cache_size": len(self.cache)
        }
    
    def __del__(self):
        """Cleanup cache on deletion."""
        try:
            self.cache.close()
        except Exception:
            pass


class CachedToolWrapper:
    """
    Wrapper that adds caching to tool functions.
    
    Automatically caches tool results based on function name and arguments.
    """
    
    def __init__(self, tool_func, cache: ResultCache, tool_name: str):
        """
        Initialize wrapper.
        
        Args:
            tool_func: Original tool function
            cache: ResultCache instance
            tool_name: Name of the tool for cache keys
        """
        self.tool_func = tool_func
        self.cache = cache
        self.tool_name = tool_name
        self.__name__ = tool_name
    
    def __call__(self, **kwargs) -> Dict[str, Any]:
        """
        Execute tool with caching.
        
        Args:
            **kwargs: Tool arguments
            
        Returns:
            Tool result (from cache or fresh execution)
        """
        # Check cache first
        cached = self.cache.get(self.tool_name, kwargs)
        if cached is not None:
            # Add cache hit indicator
            if isinstance(cached, dict):
                cached = cached.copy()
                cached["_cached"] = True
            return cached
        
        # Execute tool
        result = self.tool_func(**kwargs)
        
        # Cache successful results
        if isinstance(result, dict) and result.get("status") in ["success", "completed"]:
            self.cache.set(self.tool_name, kwargs, result)
        
        return result


def add_caching_to_registry(registry, cache: Optional[ResultCache] = None):
    """
    Add caching to all tools in a registry.
    
    Args:
        registry: ToolRegistry to add caching to
        cache: Optional ResultCache (creates new one if None)
    """
    if cache is None:
        cache = ResultCache()
    
    # Wrap all tools with caching
    tool_names = registry.list_tools()
    for tool_name in tool_names:
        tool = registry.get(tool_name)
        if tool:
            wrapped = CachedToolWrapper(tool, cache, tool_name)
            registry.register(tool_name, wrapped)
    
    return cache


def create_cached_executor(use_real_tools: bool = True, cache_ttl: int = 3600):
    """
    Create a QueryExecutor with caching enabled.
    
    Args:
        use_real_tools: Use real tool implementations
        cache_ttl: Cache TTL in seconds
        
    Returns:
        Tuple of (executor, cache)
    """
    from chemagent.core import QueryExecutor, ToolRegistry
    
    # Create executor
    registry = ToolRegistry(use_real_tools=use_real_tools)
    executor = QueryExecutor(tool_registry=registry)
    
    # Add caching
    cache = ResultCache(ttl=cache_ttl)
    add_caching_to_registry(registry, cache)
    
    return executor, cache
