"""
Query Plan Persistence for reproducible research workflows.

Provides storage and retrieval of query execution plans for:
- Reproducibility: Re-run exact same workflow later
- Debugging: Inspect what happened during execution
- Sharing: Export/import workflows between users
- Auditing: Track what queries were run and when

Storage Backends:
- SQLite (default): Local file-based storage
- JSON: Simple file export/import

Usage:
    >>> from chemagent.core.persistence import QueryPlanStore
    >>> 
    >>> store = QueryPlanStore()  # Uses SQLite by default
    >>> 
    >>> # Save a query plan
    >>> plan_id = store.save(query_plan, result, metadata={"user": "researcher1"})
    >>> 
    >>> # Retrieve later
    >>> saved = store.get(plan_id)
    >>> print(saved.query, saved.result.answer)
    >>> 
    >>> # Search plans
    >>> plans = store.search(intent_type="similarity_search", limit=10)
    >>> 
    >>> # Export for sharing
    >>> store.export_json(plan_id, "my_workflow.json")
"""

import hashlib
import json
import logging
import sqlite3
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import uuid

from chemagent.core.query_planner import QueryPlan, PlanStep
from chemagent.core.intent_parser import IntentType, ParsedIntent

logger = logging.getLogger(__name__)


@dataclass
class SavedPlan:
    """A persisted query plan with execution results."""
    
    plan_id: str
    query: str
    intent_type: str
    plan: QueryPlan
    result: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    execution_time_ms: float = 0.0
    success: bool = False
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat()
        if not self.plan_id:
            self.plan_id = self._generate_id()
    
    def _generate_id(self) -> str:
        """Generate unique plan ID based on query hash + timestamp."""
        content = f"{self.query}:{self.created_at}"
        hash_part = hashlib.sha256(content.encode()).hexdigest()[:12]
        return f"plan_{hash_part}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "plan_id": self.plan_id,
            "query": self.query,
            "intent_type": self.intent_type,
            "plan": self._plan_to_dict(self.plan),
            "result": self.result,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "execution_time_ms": self.execution_time_ms,
            "success": self.success,
        }
    
    def _plan_to_dict(self, plan: QueryPlan) -> Dict[str, Any]:
        """Convert QueryPlan to serializable dict."""
        return {
            "intent": plan.intent.value if hasattr(plan.intent, 'value') else str(plan.intent),
            "steps": [
                {
                    "tool_name": step.tool_name,
                    "args": step.args,
                    "description": step.description,
                    "depends_on": step.depends_on,
                }
                for step in plan.steps
            ],
            "entities": plan.entities,
            "parallel_groups": plan.parallel_groups,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SavedPlan":
        """Create SavedPlan from dictionary."""
        plan_data = data.get("plan", {})
        
        # Reconstruct QueryPlan
        intent = IntentType(plan_data.get("intent", "unknown"))
        steps = [
            PlanStep(
                tool_name=s["tool_name"],
                args=s.get("args", {}),
                description=s.get("description", ""),
                depends_on=s.get("depends_on", []),
            )
            for s in plan_data.get("steps", [])
        ]
        
        plan = QueryPlan(
            intent=intent,
            steps=steps,
            entities=plan_data.get("entities", {}),
            parallel_groups=plan_data.get("parallel_groups", []),
        )
        
        return cls(
            plan_id=data.get("plan_id", ""),
            query=data.get("query", ""),
            intent_type=data.get("intent_type", "unknown"),
            plan=plan,
            result=data.get("result"),
            metadata=data.get("metadata", {}),
            created_at=data.get("created_at", ""),
            execution_time_ms=data.get("execution_time_ms", 0.0),
            success=data.get("success", False),
        )


class QueryPlanStore:
    """
    Persistent storage for query plans.
    
    Supports SQLite for local storage and JSON export/import.
    
    Example:
        >>> store = QueryPlanStore("~/.chemagent/plans.db")
        >>> 
        >>> # Save after execution
        >>> plan_id = store.save(
        ...     plan=query_plan,
        ...     query="Find compounds similar to aspirin",
        ...     result={"answer": "Found 5 compounds...", "success": True},
        ...     metadata={"session": "abc123"}
        ... )
        >>> 
        >>> # Retrieve
        >>> saved = store.get(plan_id)
        >>> 
        >>> # List recent
        >>> recent = store.list_recent(limit=10)
    """
    
    def __init__(self, db_path: Optional[Union[str, Path]] = None):
        """
        Initialize the plan store.
        
        Args:
            db_path: Path to SQLite database. Defaults to ~/.chemagent/plans.db
        """
        if db_path is None:
            db_path = Path.home() / ".chemagent" / "plans.db"
        
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._init_db()
    
    def _init_db(self):
        """Initialize the SQLite database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS query_plans (
                    plan_id TEXT PRIMARY KEY,
                    query TEXT NOT NULL,
                    intent_type TEXT NOT NULL,
                    plan_json TEXT NOT NULL,
                    result_json TEXT,
                    metadata_json TEXT,
                    created_at TEXT NOT NULL,
                    execution_time_ms REAL,
                    success INTEGER,
                    UNIQUE(plan_id)
                )
            """)
            
            # Index for efficient queries
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_intent_type 
                ON query_plans(intent_type)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_created_at 
                ON query_plans(created_at DESC)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_success 
                ON query_plans(success)
            """)
            
            conn.commit()
    
    def save(
        self,
        plan: QueryPlan,
        query: str,
        result: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        execution_time_ms: float = 0.0,
        success: bool = False,
    ) -> str:
        """
        Save a query plan to the store.
        
        Args:
            plan: The QueryPlan to save
            query: Original query string
            result: Execution result (answer, raw_output, etc.)
            metadata: Additional metadata (user, session, etc.)
            execution_time_ms: Execution time
            success: Whether execution succeeded
            
        Returns:
            The plan_id of the saved plan
        """
        saved = SavedPlan(
            plan_id="",
            query=query,
            intent_type=plan.intent.value if hasattr(plan.intent, 'value') else str(plan.intent),
            plan=plan,
            result=result,
            metadata=metadata or {},
            execution_time_ms=execution_time_ms,
            success=success,
        )
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO query_plans 
                (plan_id, query, intent_type, plan_json, result_json, metadata_json, 
                 created_at, execution_time_ms, success)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                saved.plan_id,
                saved.query,
                saved.intent_type,
                json.dumps(saved._plan_to_dict(plan)),
                json.dumps(result) if result else None,
                json.dumps(saved.metadata),
                saved.created_at,
                execution_time_ms,
                1 if success else 0,
            ))
            conn.commit()
        
        logger.debug(f"Saved plan {saved.plan_id} for query: {query[:50]}...")
        return saved.plan_id
    
    def get(self, plan_id: str) -> Optional[SavedPlan]:
        """
        Retrieve a saved plan by ID.
        
        Args:
            plan_id: The plan ID
            
        Returns:
            SavedPlan if found, None otherwise
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM query_plans WHERE plan_id = ?",
                (plan_id,)
            )
            row = cursor.fetchone()
            
            if row is None:
                return None
            
            return self._row_to_saved_plan(row)
    
    def _row_to_saved_plan(self, row: sqlite3.Row) -> SavedPlan:
        """Convert database row to SavedPlan."""
        data = {
            "plan_id": row["plan_id"],
            "query": row["query"],
            "intent_type": row["intent_type"],
            "plan": json.loads(row["plan_json"]),
            "result": json.loads(row["result_json"]) if row["result_json"] else None,
            "metadata": json.loads(row["metadata_json"]) if row["metadata_json"] else {},
            "created_at": row["created_at"],
            "execution_time_ms": row["execution_time_ms"] or 0.0,
            "success": bool(row["success"]),
        }
        return SavedPlan.from_dict(data)
    
    def list_recent(self, limit: int = 20) -> List[SavedPlan]:
        """
        List most recent plans.
        
        Args:
            limit: Maximum number of plans to return
            
        Returns:
            List of SavedPlan objects, most recent first
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM query_plans ORDER BY created_at DESC LIMIT ?",
                (limit,)
            )
            return [self._row_to_saved_plan(row) for row in cursor.fetchall()]
    
    def search(
        self,
        intent_type: Optional[str] = None,
        query_contains: Optional[str] = None,
        success_only: bool = False,
        limit: int = 50,
    ) -> List[SavedPlan]:
        """
        Search for plans matching criteria.
        
        Args:
            intent_type: Filter by intent type
            query_contains: Filter by query substring
            success_only: Only return successful executions
            limit: Maximum results
            
        Returns:
            List of matching SavedPlan objects
        """
        conditions = []
        params = []
        
        if intent_type:
            conditions.append("intent_type = ?")
            params.append(intent_type)
        
        if query_contains:
            conditions.append("query LIKE ?")
            params.append(f"%{query_contains}%")
        
        if success_only:
            conditions.append("success = 1")
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                f"SELECT * FROM query_plans WHERE {where_clause} "
                f"ORDER BY created_at DESC LIMIT ?",
                params + [limit]
            )
            return [self._row_to_saved_plan(row) for row in cursor.fetchall()]
    
    def delete(self, plan_id: str) -> bool:
        """
        Delete a plan by ID.
        
        Args:
            plan_id: The plan ID to delete
            
        Returns:
            True if deleted, False if not found
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM query_plans WHERE plan_id = ?",
                (plan_id,)
            )
            conn.commit()
            return cursor.rowcount > 0
    
    def export_json(self, plan_id: str, filepath: Union[str, Path]) -> bool:
        """
        Export a plan to JSON file for sharing.
        
        Args:
            plan_id: The plan ID to export
            filepath: Output file path
            
        Returns:
            True if exported successfully
        """
        saved = self.get(plan_id)
        if saved is None:
            logger.warning(f"Plan {plan_id} not found for export")
            return False
        
        filepath = Path(filepath)
        with open(filepath, 'w') as f:
            json.dump(saved.to_dict(), f, indent=2)
        
        logger.info(f"Exported plan {plan_id} to {filepath}")
        return True
    
    def import_json(self, filepath: Union[str, Path]) -> Optional[str]:
        """
        Import a plan from JSON file.
        
        Args:
            filepath: Input file path
            
        Returns:
            The plan_id of imported plan, or None on failure
        """
        filepath = Path(filepath)
        if not filepath.exists():
            logger.error(f"Import file not found: {filepath}")
            return None
        
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            saved = SavedPlan.from_dict(data)
            
            # Re-save to database with new ID to avoid conflicts
            return self.save(
                plan=saved.plan,
                query=saved.query,
                result=saved.result,
                metadata={**saved.metadata, "imported_from": str(filepath)},
                execution_time_ms=saved.execution_time_ms,
                success=saved.success,
            )
        except Exception as e:
            logger.error(f"Failed to import plan: {e}")
            return None
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get storage statistics.
        
        Returns:
            Dictionary with counts and stats
        """
        with sqlite3.connect(self.db_path) as conn:
            total = conn.execute("SELECT COUNT(*) FROM query_plans").fetchone()[0]
            successful = conn.execute("SELECT COUNT(*) FROM query_plans WHERE success = 1").fetchone()[0]
            
            # Intent type breakdown
            cursor = conn.execute(
                "SELECT intent_type, COUNT(*) FROM query_plans GROUP BY intent_type"
            )
            by_intent = dict(cursor.fetchall())
            
            # Average execution time
            avg_time = conn.execute(
                "SELECT AVG(execution_time_ms) FROM query_plans WHERE execution_time_ms > 0"
            ).fetchone()[0]
        
        return {
            "total_plans": total,
            "successful_plans": successful,
            "success_rate": f"{successful/total*100:.1f}%" if total > 0 else "N/A",
            "by_intent": by_intent,
            "avg_execution_time_ms": round(avg_time or 0, 1),
            "db_path": str(self.db_path),
        }


# Convenience function
def get_plan_store(db_path: Optional[str] = None) -> QueryPlanStore:
    """Get a QueryPlanStore instance."""
    return QueryPlanStore(db_path)
