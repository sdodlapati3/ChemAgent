"""
ChemAgent Data Source Clients.

This module contains clients for various chemistry/pharma data sources:
- OpenTargetsClient: Target-disease evidence from Open Targets Platform
- (Future) BindingDBClient: Protein-ligand binding affinities
- (Future) PubChemClient: Chemical compounds and bioassays
"""

from .opentargets_client import (
    OpenTargetsClient,
    get_open_targets_client,
    TargetInfo,
    DiseaseInfo,
    AssociationScore,
    TargetDiseaseEvidence,
)

__all__ = [
    "OpenTargetsClient",
    "get_open_targets_client",
    "TargetInfo",
    "DiseaseInfo",
    "AssociationScore",
    "TargetDiseaseEvidence",
]
