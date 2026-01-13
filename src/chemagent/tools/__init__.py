"""
ChemAgent Tools.

This module provides tools for chemistry/pharma data access:

Data Sources:
- ChEMBL: Bioactivity data, compound info
- Open Targets: Target-disease evidence
- UniProt: Protein information
- PubChem: Chemical compounds
- BindingDB: Binding affinities
- RDKit: Chemical computations

All tools return results with provenance tracking.
"""

from .chembl_client import ChEMBLClient
from .uniprot_client import UniProtClient
from .rdkit_tools import RDKitTools
from .opentargets import (
    search_target,
    search_disease,
    get_target_disease_evidence,
    get_target_associations,
    OPEN_TARGETS_TOOLS,
    execute_open_targets_tool,
)

# New Phase G/H tools
from .admet_predictor import ADMETPredictor
from .drugbank_client import DrugBankClient, check_drug_interactions
from .pubmed_client import PubMedClient, search_pubmed
from .rag_pipeline import RAGPipeline, search_literature, get_augmented_context

__all__ = [
    # Clients
    "ChEMBLClient",
    "UniProtClient",
    "RDKitTools",
    
    # Open Targets tools
    "search_target",
    "search_disease",
    "get_target_disease_evidence",
    "get_target_associations",
    "OPEN_TARGETS_TOOLS",
    "execute_open_targets_tool",
    
    # ADMET Prediction (Phase H)
    "ADMETPredictor",
    
    # Drug Interactions (Phase H)
    "DrugBankClient",
    "check_drug_interactions",
    
    # Literature Search (Phase G)
    "PubMedClient",
    "search_pubmed",
    
    # RAG Pipeline (Phase G)
    "RAGPipeline",
    "search_literature",
    "get_augmented_context",
]
