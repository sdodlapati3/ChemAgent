"""
ChemAgent: AI-Powered Pharmaceutical Research Assistant
========================================================

ChemAgent is a production-grade agentic system for pharmaceutical R&D that combines:
- Evidence-grounded answers (every claim traced to source)
- Deterministic chemistry tools (RDKit-powered)
- Multi-source intelligence (ChEMBL, BindingDB, Open Targets, UniProt, PubChem, PDB)
- Smart LLM orchestration (local + cloud)
- Project workspaces with reproducible history

Example Usage:
    from chemagent import ChemAgent
    
    agent = ChemAgent()
    result = agent.query("Find compounds similar to aspirin with IC50 < 100nM")
    
    print(result.answer)
    print(result.provenance)

For more information, see: https://github.com/yourusername/ChemAgent
"""

__version__ = "0.1.0"
__author__ = "Your Name"
__license__ = "MIT"

# Core imports for easy access
from chemagent.core.orchestrator import ChemOrchestrator
from chemagent.core.intent_parser import IntentParser, ParsedIntent
from chemagent.core.intent_types import IntentType

# Tool imports
from chemagent.tools.rdkit_tools import RDKitTools
from chemagent.tools.chembl_client import ChEMBLClient

# Facade
class ChemAgent:
    """
    Main entry point for ChemAgent.
    
    Provides a simple, unified interface for all functionality.
    
    Example:
        agent = ChemAgent()
        result = agent.query("Find similar compounds to aspirin")
        print(result.answer)
    """
    
    def __init__(self, config_path: str | None = None):
        """
        Initialize ChemAgent.
        
        Args:
            config_path: Optional path to config file
        """
        self.orchestrator = ChemOrchestrator(config_path=config_path)
    
    def query(self, user_query: str):
        """
        Execute a natural language query.
        
        Args:
            user_query: Natural language query
            
        Returns:
            QueryResult with answer and provenance
        """
        return self.orchestrator.query(user_query)


__all__ = [
    "__version__",
    "ChemAgent",
    "ChemOrchestrator",
    "IntentParser",
    "ParsedIntent",
    "IntentType",
    "RDKitTools",
    "ChEMBLClient",
]
