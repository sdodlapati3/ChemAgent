"""
Real tool implementations for ChemAgent.

Integrates actual ChEMBL, RDKit, BindingDB, UniProt, Open Targets,
PubChem, and Structure (PDB/AlphaFold) clients with the query
executor's tool registry.
"""

from typing import Any, Dict, List, Optional

from rdkit import Chem

from chemagent.tools.bindingdb_client import BindingDBClient
from chemagent.tools.chembl_client import ChEMBLClient
from chemagent.tools.rdkit_tools import RDKitTools
from chemagent.tools.uniprot_client import UniProtClient
from chemagent.tools.opentargets_client import OpenTargetsClient
from chemagent.tools.pubchem_client import PubChemClient
from chemagent.tools.structure_client import StructureClient


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
            activities = self.client.get_activities(chembl_id, target_type=target)
            
            # Convert ActivityResult objects to dicts for JSON serialization
            activity_dicts = []
            for act in activities:
                activity_dicts.append({
                    "activity_id": act.activity_id,
                    "chembl_id": act.chembl_id,
                    "target_chembl_id": act.target_chembl_id,
                    "target_name": act.target_name,
                    "target_pref_name": act.target_name,  # Alias for compatibility
                    "assay_type": act.assay_type,
                    "standard_type": act.standard_type,
                    "standard_value": act.standard_value,
                    "standard_units": act.standard_units,
                    "pchembl_value": act.pchembl_value,
                })
            
            return {
                "status": "success",
                "chembl_id": chembl_id,
                "target": target,
                "activities": activity_dicts,
                "count": len(activity_dicts)
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
                "details": result.details,  # Add violation details list
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


class OpenTargetsTools:
    """Open Targets tool implementations for disease-target associations."""
    
    def __init__(self):
        """Initialize Open Targets client."""
        self.client = OpenTargetsClient()
    
    def search(
        self,
        query: str,
        entity_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Search across targets, diseases, and drugs.
        
        Args:
            query: Search query string
            entity_types: Filter by entity types ["target", "disease", "drug"]
            
        Returns:
            Search results with entities
        """
        try:
            results = self.client.search(query, entity_types)
            return {
                "status": "success",
                "results": results,
                "count": len(results)
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def get_target_info(self, ensembl_id: str) -> Dict[str, Any]:
        """
        Get target/gene information.
        
        Args:
            ensembl_id: Ensembl gene ID (e.g., ENSG00000146648 for EGFR)
            
        Returns:
            Target information including gene symbol, name, UniProt ID
        """
        try:
            target = self.client.get_target_info(ensembl_id)
            if not target:
                return {
                    "status": "not_found",
                    "ensembl_id": ensembl_id
                }
            return {
                "status": "success",
                "ensembl_id": target.ensembl_id,
                "gene_symbol": target.gene_symbol,
                "gene_name": target.gene_name,
                "uniprot_id": target.uniprot_id,
                "biotype": target.biotype
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def get_disease_targets(
        self,
        efo_id: str,
        limit: int = 25
    ) -> Dict[str, Any]:
        """
        Get targets associated with a disease.
        
        Args:
            efo_id: EFO disease ID
            limit: Maximum number of results
            
        Returns:
            Target associations with scores
        """
        try:
            targets = self.client.get_disease_targets(efo_id, limit)
            return {
                "status": "success",
                "disease_id": efo_id,
                "targets": targets,
                "count": len(targets)
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def get_target_diseases(
        self,
        ensembl_id: str,
        limit: int = 25
    ) -> Dict[str, Any]:
        """
        Get diseases associated with a target.
        
        Args:
            ensembl_id: Ensembl gene ID
            limit: Maximum number of results
            
        Returns:
            Disease associations with scores
        """
        try:
            diseases = self.client.get_target_diseases(ensembl_id, limit)
            return {
                "status": "success",
                "target_id": ensembl_id,
                "diseases": [
                    {
                        "efo_id": d.efo_id,
                        "name": d.name,
                        "score": d.score,
                        "therapeutic_areas": d.therapeutic_areas
                    }
                    for d in diseases
                ],
                "count": len(diseases)
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def get_target_drugs(
        self,
        ensembl_id: str,
        limit: int = 25
    ) -> Dict[str, Any]:
        """
        Get drugs targeting a specific gene.
        
        Args:
            ensembl_id: Ensembl gene ID
            limit: Maximum number of results
            
        Returns:
            Drug associations with mechanism of action
        """
        try:
            drugs = self.client.get_target_drugs(ensembl_id, limit)
            return {
                "status": "success",
                "target_id": ensembl_id,
                "drugs": [
                    {
                        "drug_id": d.drug_id,
                        "drug_name": d.drug_name,
                        "drug_type": d.drug_type,
                        "mechanism": d.mechanism_of_action,
                        "action_type": d.action_type,
                        "phase": d.phase
                    }
                    for d in drugs
                ],
                "count": len(drugs)
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }


class PubChemTools:
    """PubChem tool implementations for compound data."""
    
    def __init__(self):
        """Initialize PubChem client."""
        self.client = PubChemClient()
    
    def get_compound_by_name(self, name: str) -> Dict[str, Any]:
        """
        Get compound by name.
        
        Args:
            name: Compound name
            
        Returns:
            Compound data including CID, SMILES, properties
        """
        try:
            compound = self.client.get_compound_by_name(name)
            if not compound:
                return {
                    "status": "not_found",
                    "name": name
                }
            return {
                "status": "success",
                "cid": compound.cid,
                "name": compound.iupac_name,
                "smiles": compound.canonical_smiles,
                "molecular_weight": compound.molecular_weight,
                "molecular_formula": compound.molecular_formula,
                "xlogp": compound.xlogp,
                "hbd_count": compound.hbd_count,
                "hba_count": compound.hba_count,
                "rotatable_bonds": compound.rotatable_bond_count,
                "lipinski_violations": compound.lipinski_violations
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def get_compound_by_cid(self, cid: int) -> Dict[str, Any]:
        """
        Get compound by PubChem CID.
        
        Args:
            cid: PubChem compound ID
            
        Returns:
            Compound data
        """
        try:
            compound = self.client.get_compound(cid)
            if not compound:
                return {
                    "status": "not_found",
                    "cid": cid
                }
            return {
                "status": "success",
                "cid": compound.cid,
                "name": compound.iupac_name,
                "smiles": compound.canonical_smiles,
                "molecular_weight": compound.molecular_weight,
                "molecular_formula": compound.molecular_formula,
                "xlogp": compound.xlogp,
                "hbd_count": compound.hbd_count,
                "hba_count": compound.hba_count,
                "rotatable_bonds": compound.rotatable_bond_count,
                "lipinski_violations": compound.lipinski_violations
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def similarity_search(
        self,
        smiles: str,
        threshold: float = 0.9,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Find similar compounds in PubChem.
        
        Args:
            smiles: Query SMILES
            threshold: Similarity threshold (0-1)
            limit: Maximum results
            
        Returns:
            Similar compounds with properties
        """
        try:
            results = self.client.similarity_search(smiles, threshold, limit)
            return {
                "status": "success",
                "query_smiles": smiles,
                "threshold": threshold,
                "compounds": [
                    {
                        "cid": c.cid,
                        "smiles": c.smiles,
                        "similarity": c.similarity,
                        "molecular_weight": c.molecular_weight
                    }
                    for c in results
                ],
                "count": len(results)
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def get_bioassays(
        self,
        cid: int,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Get bioassay data for a compound.
        
        Args:
            cid: PubChem compound ID
            limit: Maximum results
            
        Returns:
            Bioassay results
        """
        try:
            assays = self.client.get_bioassays(cid, limit)
            return {
                "status": "success",
                "cid": cid,
                "assays": assays,
                "count": len(assays)
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }


class StructureTools:
    """Structure tool implementations for PDB and AlphaFold."""
    
    def __init__(self):
        """Initialize structure client."""
        self.client = StructureClient()
    
    def get_alphafold_structure(self, uniprot_id: str) -> Dict[str, Any]:
        """
        Get AlphaFold structure prediction.
        
        Args:
            uniprot_id: UniProt accession ID
            
        Returns:
            AlphaFold structure with confidence scores
        """
        try:
            structure = self.client.get_alphafold_structure(uniprot_id)
            if not structure:
                return {
                    "status": "not_found",
                    "uniprot_id": uniprot_id
                }
            return {
                "status": "success",
                "uniprot_id": structure.uniprot_id,
                "gene_name": structure.gene_name,
                "organism": structure.organism,
                "mean_plddt": structure.mean_plddt,
                "confidence_category": structure.confidence_category,
                "model_url": structure.model_url,
                "pdb_url": structure.pdb_url
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def search_pdb_by_uniprot(
        self,
        uniprot_id: str,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Search PDB for structures by UniProt ID.
        
        Args:
            uniprot_id: UniProt accession ID
            limit: Maximum results
            
        Returns:
            PDB structures with resolution and method
        """
        try:
            structures = self.client.search_by_uniprot(uniprot_id, limit)
            return {
                "status": "success",
                "uniprot_id": uniprot_id,
                "structures": [
                    {
                        "pdb_id": s.pdb_id,
                        "title": s.title,
                        "resolution": s.resolution,
                        "method": s.method,
                        "release_date": s.release_date,
                        "chain_ids": s.chain_ids
                    }
                    for s in structures
                ],
                "count": len(structures)
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def get_pdb_structure(self, pdb_id: str) -> Dict[str, Any]:
        """
        Get PDB structure details.
        
        Args:
            pdb_id: PDB ID (e.g., "1ABC")
            
        Returns:
            Structure details
        """
        try:
            structure = self.client.get_pdb_structure(pdb_id)
            if not structure:
                return {
                    "status": "not_found",
                    "pdb_id": pdb_id
                }
            return {
                "status": "success",
                "pdb_id": structure.pdb_id,
                "title": structure.title,
                "resolution": structure.resolution,
                "method": structure.method,
                "release_date": structure.release_date,
                "organism": structure.organism,
                "chain_ids": structure.chain_ids
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def search_pdb_by_ligand(
        self,
        ligand_id: str,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Search PDB for structures containing a ligand.
        
        Args:
            ligand_id: Ligand ID (e.g., "ATP", "HEM")
            limit: Maximum results
            
        Returns:
            PDB structures containing the ligand
        """
        try:
            structures = self.client.search_by_ligand(ligand_id, limit)
            return {
                "status": "success",
                "ligand_id": ligand_id,
                "structures": [
                    {
                        "pdb_id": s.pdb_id,
                        "title": s.title,
                        "resolution": s.resolution,
                        "method": s.method
                    }
                    for s in structures
                ],
                "count": len(structures)
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
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
    opentargets = OpenTargetsTools()
    pubchem = PubChemTools()
    structure = StructureTools()
    
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
    
    # Register Open Targets tools (disease-target associations)
    registry.register("opentargets_search", opentargets.search)
    registry.register("opentargets_get_target", opentargets.get_target_info)
    registry.register("opentargets_disease_targets", opentargets.get_disease_targets)
    registry.register("opentargets_target_diseases", opentargets.get_target_diseases)
    registry.register("opentargets_target_drugs", opentargets.get_target_drugs)
    
    # Register PubChem tools (115M+ compounds)
    registry.register("pubchem_get_by_name", pubchem.get_compound_by_name)
    registry.register("pubchem_get_by_cid", pubchem.get_compound_by_cid)
    registry.register("pubchem_similarity_search", pubchem.similarity_search)
    registry.register("pubchem_get_bioassays", pubchem.get_bioassays)
    
    # Register Structure tools (PDB + AlphaFold)
    registry.register("structure_alphafold", structure.get_alphafold_structure)
    registry.register("structure_pdb_by_uniprot", structure.search_pdb_by_uniprot)
    registry.register("structure_pdb_detail", structure.get_pdb_structure)
    registry.register("structure_pdb_by_ligand", structure.search_pdb_by_ligand)
    
    # Register utility tools
    registry.register("filter_by_properties", utility.filter_by_properties)
