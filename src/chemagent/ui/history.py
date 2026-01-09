"""Query history management for ChemAgent UI."""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class HistoryManager:
    """Manage query history with persistence."""
    
    def __init__(self, history_file: str = "data/query_history.json"):
        """Initialize history manager.
        
        Args:
            history_file: Path to history JSON file
        """
        self.history_file = Path(history_file)
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        self.history: List[Dict[str, Any]] = self._load_history()
        
    def add_query(
        self,
        query: str,
        result: Dict[str, Any],
        execution_time: float,
        cached: bool = False
    ) -> str:
        """Add a query to history.
        
        Args:
            query: Query text
            result: Query result
            execution_time: Execution time in seconds
            cached: Whether result was cached
            
        Returns:
            Query ID
        """
        query_id = str(uuid.uuid4())
        
        history_item = {
            "id": query_id,
            "query": query,
            "result": result,
            "execution_time": execution_time,
            "cached": cached,
            "timestamp": datetime.now().isoformat(),
            "favorite": False
        }
        
        self.history.insert(0, history_item)  # Most recent first
        
        # Keep only last 1000 queries
        if len(self.history) > 1000:
            self.history = self.history[:1000]
        
        self._save_history()
        
        return query_id
    
    def get_recent(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most recent queries.
        
        Args:
            limit: Maximum number of queries to return
            
        Returns:
            List of recent queries
        """
        return self.history[:limit]
    
    def get_by_id(self, query_id: str) -> Optional[Dict[str, Any]]:
        """Get query by ID.
        
        Args:
            query_id: Query ID
            
        Returns:
            Query item or None if not found
        """
        for item in self.history:
            if item["id"] == query_id:
                return item
        return None
    
    def search(self, search_term: str) -> List[Dict[str, Any]]:
        """Search queries by text.
        
        Args:
            search_term: Term to search for
            
        Returns:
            List of matching queries
        """
        if not search_term:
            return self.get_recent(10)
        
        search_lower = search_term.lower()
        matches = []
        
        for item in self.history:
            if search_lower in item["query"].lower():
                matches.append(item)
                if len(matches) >= 50:  # Limit results
                    break
        
        return matches
    
    def toggle_favorite(self, query_id: str) -> bool:
        """Toggle favorite status of a query.
        
        Args:
            query_id: Query ID
            
        Returns:
            New favorite status
        """
        for item in self.history:
            if item["id"] == query_id:
                item["favorite"] = not item.get("favorite", False)
                self._save_history()
                return item["favorite"]
        return False
    
    def get_favorites(self) -> List[Dict[str, Any]]:
        """Get favorite queries.
        
        Returns:
            List of favorite queries
        """
        return [item for item in self.history if item.get("favorite")]
    
    def clear(self):
        """Clear all history."""
        self.history = []
        self._save_history()
    
    def _load_history(self) -> List[Dict[str, Any]]:
        """Load history from file."""
        if self.history_file.exists():
            try:
                with open(self.history_file) as f:
                    return json.load(f)
            except Exception:
                return []
        return []
    
    def _save_history(self):
        """Save history to file."""
        try:
            with open(self.history_file, "w") as f:
                json.dump(self.history, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save history: {e}")
