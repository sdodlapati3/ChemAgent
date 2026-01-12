"""
Open Targets Tools for ChemAgent.

These tools provide access to Open Targets Platform data:
- Target-disease evidence (genetic, literature, expression)
- Association scores
- Known drugs for targets

All tools return results with full provenance tracking.
"""

import json
import logging
from typing import Any, Dict, List, Optional

from chemagent.clients.opentargets_client import get_open_targets_client
from chemagent.core.provenance import (
    DataSource,
    ProvenanceToolResult,
    EvidenceTable,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Tool Functions (for LLM agent use)
# =============================================================================

def search_target(query: str) -> Dict[str, Any]:
    """
    Search for targets (genes/proteins) in Open Targets.
    
    Use this tool to find the Ensembl ID for a target before querying
    for disease associations.
    
    Args:
        query: Target name or symbol (e.g., "EGFR", "epidermal growth factor receptor")
    
    Returns:
        Dictionary with matching targets and their Ensembl IDs
    
    Example:
        >>> search_target("EGFR")
        {
            "targets": [
                {"ensembl_id": "ENSG00000146648", "name": "EGFR", "description": "..."}
            ],
            "provenance": {...}
        }
    """
    client = get_open_targets_client()
    result = client.search_target(query)
    
    return {
        "success": result.success,
        "targets": result.data.get("targets", []) if result.data else [],
        "error": result.error,
        "provenance": {
            "source": "Open Targets Platform",
            "url": "https://platform.opentargets.org",
            "records": [r.to_citation() for r in result.provenance_records]
        }
    }


def search_disease(query: str) -> Dict[str, Any]:
    """
    Search for diseases in Open Targets.
    
    Use this tool to find the EFO ID for a disease before querying
    for target associations.
    
    Args:
        query: Disease name (e.g., "lung cancer", "type 2 diabetes")
    
    Returns:
        Dictionary with matching diseases and their EFO IDs
    
    Example:
        >>> search_disease("lung cancer")
        {
            "diseases": [
                {"efo_id": "EFO_0001378", "name": "lung adenocarcinoma", ...}
            ]
        }
    """
    client = get_open_targets_client()
    result = client.search_disease(query)
    
    return {
        "success": result.success,
        "diseases": result.data.get("diseases", []) if result.data else [],
        "error": result.error,
        "provenance": {
            "source": "Open Targets Platform",
            "url": "https://platform.opentargets.org",
            "records": [r.to_citation() for r in result.provenance_records]
        }
    }


def get_target_disease_evidence(
    ensembl_id: str, 
    efo_id: str
) -> Dict[str, Any]:
    """
    Get evidence linking a target to a disease.
    
    This is the KEY tool for answering target validation questions like:
    - "What's the evidence that EGFR is implicated in lung cancer?"
    - "Is BRCA1 a good target for breast cancer?"
    - "What genetic evidence links TP53 to cancer?"
    
    Args:
        ensembl_id: Ensembl gene ID (e.g., "ENSG00000146648" for EGFR)
        efo_id: EFO disease ID (e.g., "EFO_0001378" for lung adenocarcinoma)
    
    Returns:
        Dictionary with:
        - association_score: Overall evidence score (0-1)
        - datatype_scores: Breakdown by evidence type
        - evidence_count: Number of evidence pieces
        - known_drugs: Drugs targeting this gene for this disease
        - provenance: Full source attribution
    
    Example:
        >>> get_target_disease_evidence("ENSG00000146648", "EFO_0001378")
        {
            "association_score": 0.89,
            "datatype_scores": {
                "literature": 0.95,
                "genetic_association": 0.72,
                "known_drug": 0.88
            },
            "known_drugs": [{"name": "Erlotinib", "phase": 4, ...}],
            ...
        }
    """
    client = get_open_targets_client()
    result = client.get_target_disease_evidence(ensembl_id, efo_id)
    
    if not result.success:
        return {
            "success": False,
            "error": result.error,
            "provenance": {"source": "Open Targets Platform"}
        }
    
    data = result.data or {}
    
    # Generate evidence table for citation
    evidence_table = None
    if result.evidence:
        table = EvidenceTable(result.evidence)
        evidence_table = table.to_markdown()
    
    return {
        "success": True,
        "association_found": data.get("association_found", False),
        "target": data.get("target"),
        "disease": data.get("disease"),
        "association_score": data.get("association_score"),
        "datatype_scores": data.get("datatype_scores"),
        "evidence_count": data.get("evidence_count"),
        "evidence_by_type": data.get("evidence_by_type"),
        "known_drugs": data.get("known_drugs"),
        "evidence_table": evidence_table,
        "provenance": {
            "source": "Open Targets Platform",
            "url": f"https://platform.opentargets.org/evidence/{ensembl_id}/{efo_id}",
            "records": [r.to_citation() for r in result.provenance_records]
        }
    }


def get_target_associations(
    ensembl_id: str,
    limit: int = 10
) -> Dict[str, Any]:
    """
    Get all disease associations for a target.
    
    Use this to explore what diseases a target is implicated in.
    
    Args:
        ensembl_id: Ensembl gene ID (e.g., "ENSG00000146648" for EGFR)
        limit: Maximum number of diseases to return
    
    Returns:
        Dictionary with list of associated diseases and scores
    
    Example:
        >>> get_target_associations("ENSG00000146648")
        {
            "target": {"ensembl_id": "ENSG00000146648", "symbol": "EGFR"},
            "diseases": [
                {"name": "lung adenocarcinoma", "score": 0.89, ...},
                {"name": "glioblastoma", "score": 0.85, ...}
            ]
        }
    """
    client = get_open_targets_client()
    result = client.get_target_associations(ensembl_id, limit)
    
    if not result.success:
        return {
            "success": False,
            "error": result.error,
            "provenance": {"source": "Open Targets Platform"}
        }
    
    data = result.data or {}
    
    return {
        "success": True,
        "target": data.get("target"),
        "total_associations": data.get("total_associations", 0),
        "diseases": data.get("diseases", []),
        "provenance": {
            "source": "Open Targets Platform",
            "url": f"https://platform.opentargets.org/target/{ensembl_id}/associations",
            "records": [r.to_citation() for r in result.provenance_records]
        }
    }


# =============================================================================
# Tool Definitions (for LLM function calling)
# =============================================================================

OPEN_TARGETS_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "opentargets_search_target",
            "description": (
                "Search for targets (genes/proteins) in Open Targets Platform. "
                "Use this to find the Ensembl ID for a target before querying for evidence. "
                "Returns matching targets with their Ensembl IDs."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Target name or symbol (e.g., 'EGFR', 'epidermal growth factor receptor')"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "opentargets_search_disease",
            "description": (
                "Search for diseases in Open Targets Platform. "
                "Use this to find the EFO ID for a disease before querying for evidence. "
                "Returns matching diseases with their EFO IDs."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Disease name (e.g., 'lung cancer', 'type 2 diabetes')"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "opentargets_get_evidence",
            "description": (
                "Get evidence linking a target to a disease from Open Targets. "
                "This is the KEY tool for target validation questions like: "
                "'What evidence links EGFR to lung cancer?' "
                "Returns association scores, evidence breakdown by type, and known drugs."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "ensembl_id": {
                        "type": "string",
                        "description": "Ensembl gene ID (e.g., 'ENSG00000146648' for EGFR)"
                    },
                    "efo_id": {
                        "type": "string",
                        "description": "EFO disease ID (e.g., 'EFO_0001378' for lung adenocarcinoma)"
                    }
                },
                "required": ["ensembl_id", "efo_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "opentargets_get_associations",
            "description": (
                "Get all disease associations for a target. "
                "Use this to explore what diseases a target is implicated in. "
                "Returns list of diseases with association scores."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "ensembl_id": {
                        "type": "string",
                        "description": "Ensembl gene ID (e.g., 'ENSG00000146648' for EGFR)"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of diseases to return (default: 10)",
                        "default": 10
                    }
                },
                "required": ["ensembl_id"]
            }
        }
    }
]


# =============================================================================
# Tool Executor
# =============================================================================

def execute_open_targets_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute an Open Targets tool by name.
    
    Args:
        tool_name: Name of the tool to execute
        arguments: Tool arguments
    
    Returns:
        Tool result dictionary
    """
    tool_map = {
        "opentargets_search_target": lambda args: search_target(args["query"]),
        "opentargets_search_disease": lambda args: search_disease(args["query"]),
        "opentargets_get_evidence": lambda args: get_target_disease_evidence(
            args["ensembl_id"], args["efo_id"]
        ),
        "opentargets_get_associations": lambda args: get_target_associations(
            args["ensembl_id"], args.get("limit", 10)
        )
    }
    
    if tool_name not in tool_map:
        return {"success": False, "error": f"Unknown tool: {tool_name}"}
    
    try:
        return tool_map[tool_name](arguments)
    except Exception as e:
        logger.error(f"Tool execution failed: {tool_name} - {e}")
        return {"success": False, "error": str(e)}
