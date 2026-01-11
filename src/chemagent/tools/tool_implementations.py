"""
Real tool implementations for ChemAgent.

Integrates actual ChEMBL, RDKit, BindingDB, and UniProt clients
with the query executor's tool registry.
"""

from typing import Any, Dict, List, Optional

from rdkit import Chem

from chemagent.tools.bindingdb_client import BindingDBClient
from chemagent.tools.chembl_client import ChEMBLClient
from chemagent.tools.rdkit_tools import RDKitTools
from chemagent.tools.uniprot_client import UniProtClient


class ChEMBLTools:
    """ChEMBL tool implementations."""
    
    def __init__(self):
        """Initialize ChEMBL client."""
        self.client = ChEMBLClient()
    
    def search_by_name(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """
        Search for compounds by name.
        
        Args:
            query: Search query
            limit: Maximum results
            
        Returns:
            Search results with compounds
        """
        try:
            results = self.client.search_by_name(query, limit=limit)
            return {
                "status": "success",
                "compounds": results,
                "count": len(results)
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def get_compound(self, chembl_id: str) -> Dict[str, Any]:
        """
        Get compound by ChEMBL ID.
        
        Args:
            chembl_id: ChEMBL identifier
            
        Returns:
            Compound data including SMILES, name, properties
        """
        try:
            compound = self.client.get_compound(chembl_id)
            if not compound:
                return {
                    "status": "not_found",
                    "chembl_id": chembl_id
                }
            
            # CompoundResult object - access as attributes
            name = compound.synonyms[0] if compound.synonyms else None
            
            return {
                "status": "success",
                "chembl_id": compound.chembl_id,
                "smiles": compound.smiles,
                "name": name,
                "synonyms": compound.synonyms,
                "molecular_weight": compound.molecular_weight,
                "alogp": compound.alogp,
                "psa": compound.psa,
                "inchi": compound.standard_inchi,
                "inchi_key": compound.standard_inchi_key,
                "formula": compound.molecular_formula
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "chembl_id": chembl_id
            }
    
    def similarity_search(
        self,
        smiles: str,
        threshold: float = 0.7,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Find similar compounds.
        
        Args:
            smiles: Query SMILES
            threshold: Similarity threshold (0-1)
            limit: Maximum results
            
        Returns:
            Similar compounds with similarity scores
        """
        try:
            # Convert threshold percentage to 0-100 scale for ChEMBL API
            threshold_percent = int(threshold * 100)
            
            results = self.client.similarity_search(
                smiles=smiles,
                threshold=threshold_percent,
                limit=limit
            )
            
            return {
                "status": "success",
                "query_smiles": smiles,
                "threshold": threshold,
                "compounds": results,
                "count": len(results)
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def substructure_search(
        self,
        smiles: str,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Find compounds containing substructure.
        
        Args:
            smiles: Substructure SMILES
            limit: Maximum results
            
        Returns:
            Matching compounds
        """
        try:
            results = self.client.substructure_search(
                smiles=smiles,
                limit=limit
            )
            
            return {
                "status": "success",
                "substructure": smiles,
                "compounds": results,
                "count": len(results)
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def get_activities(
        self,
        chembl_id: str,
        target: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get compound bioactivities.
        
        Args:
            chembl_id: Compound ChEMBL ID
            target: Optional target filter
            
        Returns:
            Activity data
        """
        try:
            activities = self.client.get_compound_activities(chembl_id)
            
            # Filter by target if specified
            if target and activities:
                activities = [
                    a for a in activities
                    if target.lower() in a.get("target_pref_name", "").lower()
                ]
            
            return {
                "status": "success",
                "chembl_id": chembl_id,
                "target": target,
                "activities": activities,
                "count": len(activities)
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }


class RDKitToolsWrapper:
    """RDKit tool implementations."""
    
    def __init__(self):
        """Initialize RDKit tools."""
        self.tools = RDKitTools()
    
    def standardize_smiles(self, smiles: str) -> Dict[str, Any]:
        """
        Standardize SMILES string.
        
        Args:
            smiles: Input SMILES
            
        Returns:
            Standardized SMILES and molecule info
        """
        try:
            mol = Chem.MolFromSmiles(smiles)
            if not mol:
                return {
                    "status": "error",
                    "error": "Invalid SMILES"
                }
            
            standardized = Chem.MolToSmiles(mol)
            
            return {
                "status": "success",
                "original_smiles": smiles,
                "smiles": standardized,
                "canonical_smiles": standardized
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def calc_properties(self, smiles: str) -> Dict[str, Any]:
        """
        Calculate molecular properties.
        
        Args:
            smiles: SMILES string
            
        Returns:
            Molecular properties (MW, LogP, etc.)
        """
        try:
            mol = Chem.MolFromSmiles(smiles)
            if not mol:
                return {
                    "status": "error",
                    "error": "Invalid SMILES"
                }
            
            props = self.tools.calc_molecular_properties(mol)
            
            if not props:
                return {
                    "status": "error",
                    "error": "Property calculation failed"
                }
            
            return {
                "status": "success",
                "smiles": smiles,
                "properties": {
                    "molecular_weight": props.molecular_weight,
                    "exact_mass": props.exact_mass,
                    "logp": props.logp,
                    "h_bond_donors": props.num_h_donors,
                    "h_bond_acceptors": props.num_h_acceptors,
                    "polar_surface_area": props.tpsa,
                    "rotatable_bonds": props.num_rotatable_bonds,
                    "num_rings": props.num_rings,
                    "num_aromatic_rings": props.num_aromatic_rings,
                    "num_heteroatoms": props.num_heteroatoms,
                    "fraction_csp3": props.fraction_csp3
                },
                # Flatten for easy access
                "molecular_weight": props.molecular_weight,
                "exact_mass": props.exact_mass,
                "logp": props.logp,
                "h_bond_donors": props.num_h_donors,
                "h_bond_acceptors": props.num_h_acceptors,
                "polar_surface_area": props.tpsa,
                "rotatable_bonds": props.num_rotatable_bonds,
                "num_rings": props.num_rings,
                "num_aromatic_rings": props.num_aromatic_rings,
                "num_heteroatoms": props.num_heteroatoms,
                "fraction_csp3": props.fraction_csp3
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def calc_lipinski(self, smiles: str) -> Dict[str, Any]:
        """
        Calculate Lipinski Rule of Five parameters.
        
        Args:
            smiles: SMILES string
            
        Returns:
            Lipinski parameters and pass/fail
        """
        try:
            mol = Chem.MolFromSmiles(smiles)
            if not mol:
                return {
                    "status": "error",
                    "error": "Invalid SMILES"
                }
            
            result = self.tools.calc_lipinski(mol)
            
            if not result:
                return {
                    "status": "error",
                    "error": "Lipinski calculation failed"
                }
            
            return {
                "status": "success",
                "smiles": smiles,
                "lipinski": {
                    "molecular_weight": result.molecular_weight,
                    "logp": result.logp,
                    "h_bond_donors": result.num_h_donors,
                    "h_bond_acceptors": result.num_h_acceptors
                },
                "passes_lipinski": result.passes,
                "violations": result.violations,
                # Flatten for easy access
                "molecular_weight": result.molecular_weight,
                "logp": result.logp,
                "h_bond_donors": result.num_h_donors,
                "h_bond_acceptors": result.num_h_acceptors
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def convert_format(
        self,
        smiles: str,
        to_format: str = "inchi"
    ) -> Dict[str, Any]:
        """
        Convert molecule format.
        
        Args:
            smiles: Input SMILES
            to_format: Target format (inchi, inchikey, mol, sdf)
            
        Returns:
            Converted format
        """
        try:
            mol = Chem.MolFromSmiles(smiles)
            if not mol:
                return {
                    "status": "error",
                    "error": "Invalid SMILES"
                }
            
            result = {"status": "success", "smiles": smiles}
            
            if to_format.lower() == "inchi":
                from rdkit.Chem import inchi
                result["inchi"] = inchi.MolToInchi(mol)
            elif to_format.lower() == "inchikey":
                from rdkit.Chem import inchi
                result["inchikey"] = inchi.MolToInchiKey(mol)
            elif to_format.lower() in ["mol", "sdf"]:
                result["mol_block"] = Chem.MolToMolBlock(mol)
            else:
                return {
                    "status": "error",
                    "error": f"Unsupported format: {to_format}"
                }
            
            return result
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def extract_scaffold(self, smiles: str) -> Dict[str, Any]:
        """
        Extract molecular scaffold.
        
        Args:
            smiles: Input SMILES
            
        Returns:
            Scaffold SMILES
        """
        try:
            scaffold = self.tools.get_murcko_scaffold(smiles)
            
            if not scaffold:
                return {
                    "status": "error",
                    "error": "Could not extract scaffold"
                }
            
            return {
                "status": "success",
                "original_smiles": smiles,
                "scaffold_smiles": scaffold,
                "smiles": scaffold
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }


class UniProtTools:
    """UniProt tool implementations."""
    
    def __init__(self):
        """Initialize UniProt client."""
        self.client = UniProtClient()
    
    def get_protein(self, uniprot_id: str) -> Dict[str, Any]:
        """
        Get protein by UniProt ID.
        
        Args:
            uniprot_id: UniProt identifier
            
        Returns:
            Protein data
        """
        try:
            protein = self.client.get_protein_by_id(uniprot_id)
            
            if not protein:
                return {
                    "status": "not_found",
                    "uniprot_id": uniprot_id
                }
            
            return {
                "status": "success",
                "uniprot_id": uniprot_id,
                "protein": protein,
                "name": protein.get("proteinDescription", {}).get("recommendedName", {}).get("fullName", {}).get("value"),
                "organism": protein.get("organism", {}).get("scientificName"),
                "sequence": protein.get("sequence", {}).get("value")
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def search(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """
        Search UniProt.
        
        Args:
            query: Search query
            limit: Maximum results
            
        Returns:
            Search results
        """
        try:
            results = self.client.search_proteins(query, limit=limit)
            
            return {
                "status": "success",
                "query": query,
                "proteins": results,
                "count": len(results)
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }


class UtilityTools:
    """Utility tools for filtering and processing."""
    
    @staticmethod
    def filter_by_properties(
        compounds: List[Dict],
        mw_min: Optional[float] = None,
        mw_max: Optional[float] = None,
        logp_min: Optional[float] = None,
        logp_max: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Filter compounds by molecular properties.
        
        Args:
            compounds: List of compound data
            mw_min: Minimum molecular weight
            mw_max: Maximum molecular weight
            logp_min: Minimum LogP
            logp_max: Maximum LogP
            
        Returns:
            Filtered compounds
        """
        filtered = []
        
        for compound in compounds:
            # Get properties (handle different data structures)
            props = compound.get("properties", compound.get("molecule_properties", {}))
            mw = props.get("molecular_weight", props.get("full_mwt"))
            logp = props.get("logp", props.get("alogp"))
            
            # Apply filters
            if mw_min and mw and mw < mw_min:
                continue
            if mw_max and mw and mw > mw_max:
                continue
            if logp_min and logp and logp < logp_min:
                continue
            if logp_max and logp and logp > logp_max:
                continue
            
            filtered.append(compound)
        
        return {
            "status": "success",
            "original_count": len(compounds),
            "filtered_count": len(filtered),
            "compounds": filtered
        }


def register_real_tools(registry) -> None:
    """
    Register real tool implementations.
    
    Args:
        registry: ToolRegistry to register tools with
    """
    # Initialize tool wrappers
    chembl = ChEMBLTools()
    rdkit = RDKitToolsWrapper()
    uniprot = UniProtTools()
    utility = UtilityTools()
    
    # Register ChEMBL tools
    registry.register("chembl_search_by_name", chembl.search_by_name)
    registry.register("chembl_get_compound", chembl.get_compound)
    registry.register("chembl_similarity_search", chembl.similarity_search)
    registry.register("chembl_substructure_search", chembl.substructure_search)
    registry.register("chembl_get_activities", chembl.get_activities)
    
    # Register RDKit tools
    registry.register("rdkit_standardize_smiles", rdkit.standardize_smiles)
    registry.register("rdkit_calc_properties", rdkit.calc_properties)
    registry.register("rdkit_calc_lipinski", rdkit.calc_lipinski)
    registry.register("rdkit_convert_format", rdkit.convert_format)
    registry.register("rdkit_extract_scaffold", rdkit.extract_scaffold)
    
    # Register UniProt tools
    registry.register("uniprot_get_protein", uniprot.get_protein)
    registry.register("uniprot_search", uniprot.search)
    
    # Register utility tools
    registry.register("filter_by_properties", utility.filter_by_properties)
