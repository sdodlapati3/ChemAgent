"""
PDB and AlphaFold Structure Client
==================================

Client for protein structure data from:
- RCSB PDB (experimental structures)
- AlphaFold DB (predicted structures)

Features:
- Fetch structure metadata and files
- Search by UniProt ID or gene symbol
- Get binding site information
- AlphaFold confidence scores

Example:
    >>> from chemagent.tools.structure_client import StructureClient
    >>> client = StructureClient()
    >>> structures = client.get_structures_for_uniprot("P00533")  # EGFR
    >>> alphafold = client.get_alphafold_structure("P00533")
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import requests
from diskcache import Cache

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

PDB_SEARCH_URL = "https://search.rcsb.org/rcsbsearch/v2/query"
PDB_DATA_URL = "https://data.rcsb.org/rest/v1/core"
PDB_DOWNLOAD_URL = "https://files.rcsb.org/download"

ALPHAFOLD_API_URL = "https://alphafold.ebi.ac.uk/api"
ALPHAFOLD_FILES_URL = "https://alphafold.ebi.ac.uk/files"

CACHE_DIR = ".cache/structures"
CACHE_TTL = 604800  # 7 days
MAX_RETRIES = 3
RETRY_DELAY = 1.0


# =============================================================================
# Result Classes
# =============================================================================

@dataclass
class PDBStructure:
    """PDB structure metadata."""
    pdb_id: str
    title: str
    method: str  # X-RAY DIFFRACTION, NMR, CRYO-EM
    resolution: Optional[float]
    release_date: str
    uniprot_ids: List[str] = field(default_factory=list)
    ligands: List[str] = field(default_factory=list)
    organism: str = ""
    chains: int = 1
    
    @property
    def url(self) -> str:
        """URL to PDB page."""
        return f"https://www.rcsb.org/structure/{self.pdb_id}"
    
    @property
    def structure_url(self) -> str:
        """URL to download structure file."""
        return f"{PDB_DOWNLOAD_URL}/{self.pdb_id}.cif"


@dataclass
class AlphaFoldStructure:
    """AlphaFold predicted structure."""
    uniprot_id: str
    gene_name: str
    organism: str
    model_url: str
    pae_url: str  # Predicted Aligned Error
    mean_plddt: float  # Model confidence (0-100)
    sequence_length: int
    model_version: str = "v4"
    
    @property
    def confidence_category(self) -> str:
        """Confidence category based on pLDDT."""
        if self.mean_plddt >= 90:
            return "very_high"
        elif self.mean_plddt >= 70:
            return "confident"
        elif self.mean_plddt >= 50:
            return "low"
        else:
            return "very_low"


@dataclass
class BindingSite:
    """Binding site information."""
    site_id: str
    pdb_id: str
    ligand_id: str
    residues: List[str]
    chain: str


@dataclass
class Provenance:
    """Data provenance tracking."""
    source: str
    query_type: str
    query_params: Dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


# =============================================================================
# Client Implementation
# =============================================================================

class StructureClient:
    """
    Client for protein structure databases.
    
    Provides unified access to:
    - RCSB PDB: Experimental structures (X-ray, NMR, Cryo-EM)
    - AlphaFold DB: AI-predicted structures
    
    Example:
        >>> client = StructureClient()
        >>> 
        >>> # Get experimental structures for EGFR
        >>> pdb_structures = client.get_structures_for_uniprot("P00533")
        >>> for s in pdb_structures[:3]:
        ...     print(f"{s.pdb_id}: {s.resolution}Å ({s.method})")
        >>> 
        >>> # Get AlphaFold prediction
        >>> af = client.get_alphafold_structure("P00533")
        >>> print(f"Confidence: {af.mean_plddt:.1f} ({af.confidence_category})")
    """
    
    def __init__(
        self,
        cache_dir: str = CACHE_DIR,
        cache_ttl: int = CACHE_TTL,
        timeout: int = 30
    ):
        """
        Initialize structure client.
        
        Args:
            cache_dir: Directory for disk cache
            cache_ttl: Cache time-to-live in seconds
            timeout: Request timeout in seconds
        """
        self.cache = Cache(cache_dir)
        self.cache_ttl = cache_ttl
        self.timeout = timeout
        self.session = requests.Session()
    
    def _get(self, url: str, cache_key: Optional[str] = None) -> Dict[str, Any]:
        """
        GET request with caching and retry.
        """
        if cache_key:
            cached = self.cache.get(cache_key)
            if cached is not None:
                return cached
        
        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                response = self.session.get(url, timeout=self.timeout)
                response.raise_for_status()
                data = response.json()
                
                if cache_key:
                    self.cache.set(cache_key, data, expire=self.cache_ttl)
                
                return data
                
            except requests.RequestException as e:
                last_error = e
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY * (attempt + 1))
        
        raise ConnectionError(f"Failed after {MAX_RETRIES} retries: {last_error}")
    
    def _post(
        self,
        url: str,
        json_data: Dict[str, Any],
        cache_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        POST request with caching and retry.
        """
        if cache_key:
            cached = self.cache.get(cache_key)
            if cached is not None:
                return cached
        
        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                response = self.session.post(
                    url,
                    json=json_data,
                    timeout=self.timeout
                )
                response.raise_for_status()
                data = response.json()
                
                if cache_key:
                    self.cache.set(cache_key, data, expire=self.cache_ttl)
                
                return data
                
            except requests.RequestException as e:
                last_error = e
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY * (attempt + 1))
        
        raise ConnectionError(f"Failed after {MAX_RETRIES} retries: {last_error}")
    
    # =========================================================================
    # PDB Methods
    # =========================================================================
    
    def search_pdb(
        self,
        uniprot_id: Optional[str] = None,
        gene_name: Optional[str] = None,
        ligand: Optional[str] = None,
        limit: int = 25
    ) -> List[str]:
        """
        Search PDB for structures.
        
        Args:
            uniprot_id: UniProt accession (e.g., P00533)
            gene_name: Gene symbol (e.g., EGFR)
            ligand: Ligand ID (e.g., ATP)
            limit: Maximum results
            
        Returns:
            List of PDB IDs
        """
        # Build query
        query_nodes = []
        
        if uniprot_id:
            query_nodes.append({
                "type": "terminal",
                "service": "text",
                "parameters": {
                    "attribute": "rcsb_polymer_entity_container_identifiers.reference_sequence_identifiers.database_accession",
                    "operator": "exact_match",
                    "value": uniprot_id
                }
            })
        
        if gene_name:
            query_nodes.append({
                "type": "terminal",
                "service": "text",
                "parameters": {
                    "attribute": "rcsb_entity_source_organism.rcsb_gene_name.value",
                    "operator": "exact_match",
                    "value": gene_name.upper()
                }
            })
        
        if ligand:
            query_nodes.append({
                "type": "terminal",
                "service": "text",
                "parameters": {
                    "attribute": "rcsb_nonpolymer_instance_container_identifiers.comp_id",
                    "operator": "exact_match",
                    "value": ligand.upper()
                }
            })
        
        if not query_nodes:
            return []
        
        # Combine with AND
        if len(query_nodes) == 1:
            query = query_nodes[0]
        else:
            query = {
                "type": "group",
                "logical_operator": "and",
                "nodes": query_nodes
            }
        
        search_request = {
            "query": query,
            "return_type": "entry",
            "request_options": {
                "results_content_type": ["experimental"],
                "sort": [{"sort_by": "rcsb_accession_info.initial_release_date", "direction": "desc"}],
                "paginate": {"start": 0, "rows": limit}
            }
        }
        
        cache_key = f"pdb_search:{uniprot_id}:{gene_name}:{ligand}:{limit}"
        
        try:
            data = self._post(PDB_SEARCH_URL, search_request, cache_key)
            return [hit["identifier"] for hit in data.get("result_set", [])]
        except Exception as e:
            logger.error(f"PDB search failed: {e}")
            return []
    
    def get_pdb_info(self, pdb_id: str) -> Optional[PDBStructure]:
        """
        Get PDB structure metadata.
        
        Args:
            pdb_id: PDB ID (e.g., 1M17)
            
        Returns:
            PDBStructure or None if not found
        """
        pdb_id = pdb_id.upper()
        cache_key = f"pdb_info:{pdb_id}"
        
        try:
            url = f"{PDB_DATA_URL}/entry/{pdb_id}"
            data = self._get(url, cache_key)
            
            # Extract resolution
            resolution = None
            if data.get("rcsb_entry_info", {}).get("resolution_combined"):
                resolution = data["rcsb_entry_info"]["resolution_combined"][0]
            
            # Get polymer entities for UniProt mapping
            uniprot_ids = []
            try:
                entities_url = f"{PDB_DATA_URL}/entry/{pdb_id}/polymer_entities"
                entities = self._get(entities_url)
                for entity in entities:
                    refs = entity.get("rcsb_polymer_entity_container_identifiers", {})
                    for ref in refs.get("reference_sequence_identifiers", []):
                        if ref.get("database_name") == "UniProt":
                            uniprot_ids.append(ref.get("database_accession"))
            except:
                pass
            
            # Get ligands
            ligands = []
            try:
                ligands_url = f"{PDB_DATA_URL}/entry/{pdb_id}/nonpolymer_entities"
                ligands_data = self._get(ligands_url)
                for lig in ligands_data:
                    comp_id = lig.get("pdbx_entity_nonpoly", {}).get("comp_id")
                    if comp_id and comp_id not in ["HOH", "NA", "CL", "MG", "ZN", "CA"]:
                        ligands.append(comp_id)
            except:
                pass
            
            return PDBStructure(
                pdb_id=pdb_id,
                title=data.get("struct", {}).get("title", ""),
                method=data.get("exptl", [{}])[0].get("method", ""),
                resolution=resolution,
                release_date=data.get("rcsb_accession_info", {}).get("initial_release_date", ""),
                uniprot_ids=list(set(uniprot_ids)),
                ligands=ligands,
                organism=data.get("rcsb_entry_info", {}).get("polymer_entity_count_protein", 0)
            )
            
        except Exception as e:
            logger.error(f"Failed to get PDB info for {pdb_id}: {e}")
            return None
    
    def get_structures_for_uniprot(
        self,
        uniprot_id: str,
        limit: int = 10
    ) -> List[PDBStructure]:
        """
        Get all PDB structures for a UniProt accession.
        
        Args:
            uniprot_id: UniProt accession (e.g., P00533)
            limit: Maximum structures to return
            
        Returns:
            List of PDBStructure sorted by resolution
        """
        pdb_ids = self.search_pdb(uniprot_id=uniprot_id, limit=limit * 2)
        
        structures = []
        for pdb_id in pdb_ids[:limit]:
            info = self.get_pdb_info(pdb_id)
            if info:
                structures.append(info)
        
        # Sort by resolution (best first)
        structures.sort(key=lambda x: x.resolution or 999)
        return structures[:limit]
    
    # =========================================================================
    # AlphaFold Methods
    # =========================================================================
    
    def get_alphafold_structure(
        self,
        uniprot_id: str
    ) -> Optional[AlphaFoldStructure]:
        """
        Get AlphaFold predicted structure for a protein.
        
        Args:
            uniprot_id: UniProt accession (e.g., P00533)
            
        Returns:
            AlphaFoldStructure or None if not available
        """
        cache_key = f"alphafold:{uniprot_id}"
        
        try:
            url = f"{ALPHAFOLD_API_URL}/prediction/{uniprot_id}"
            data = self._get(url, cache_key)
            
            if not data:
                return None
            
            # API returns a list, get first entry
            if isinstance(data, list):
                data = data[0] if data else None
            
            if not data:
                return None
            
            return AlphaFoldStructure(
                uniprot_id=data.get("uniprotAccession", uniprot_id),
                gene_name=data.get("gene", ""),
                organism=data.get("organismScientificName", ""),
                model_url=data.get("pdbUrl", ""),
                pae_url=data.get("paeImageUrl", ""),
                mean_plddt=data.get("globalMetricValue", 0),
                sequence_length=data.get("uniprotEnd", 0) - data.get("uniprotStart", 0) + 1,
                model_version=data.get("latestVersion", "v4")
            )
            
        except Exception as e:
            logger.error(f"Failed to get AlphaFold structure for {uniprot_id}: {e}")
            return None
    
    def has_alphafold_structure(self, uniprot_id: str) -> bool:
        """Check if AlphaFold prediction exists for UniProt ID."""
        return self.get_alphafold_structure(uniprot_id) is not None
    
    # =========================================================================
    # Combined Methods
    # =========================================================================
    
    def get_all_structures(
        self,
        uniprot_id: str,
        max_pdb: int = 5
    ) -> Dict[str, Any]:
        """
        Get both experimental and predicted structures.
        
        Args:
            uniprot_id: UniProt accession
            max_pdb: Maximum PDB structures
            
        Returns:
            Dictionary with PDB and AlphaFold structures
        """
        pdb_structures = self.get_structures_for_uniprot(uniprot_id, limit=max_pdb)
        alphafold = self.get_alphafold_structure(uniprot_id)
        
        return {
            "uniprot_id": uniprot_id,
            "experimental": {
                "count": len(pdb_structures),
                "best_resolution": pdb_structures[0].resolution if pdb_structures else None,
                "structures": [
                    {
                        "pdb_id": s.pdb_id,
                        "title": s.title,
                        "method": s.method,
                        "resolution": s.resolution,
                        "ligands": s.ligands,
                        "url": s.url
                    }
                    for s in pdb_structures
                ]
            },
            "predicted": {
                "available": alphafold is not None,
                "confidence": alphafold.mean_plddt if alphafold else None,
                "confidence_category": alphafold.confidence_category if alphafold else None,
                "model_url": alphafold.model_url if alphafold else None,
                "version": alphafold.model_version if alphafold else None
            } if alphafold else None,
            "provenance": {
                "pdb_source": "RCSB PDB",
                "alphafold_source": "AlphaFold DB",
                "retrieved": datetime.now().isoformat()
            }
        }


# =============================================================================
# Convenience Functions
# =============================================================================

def get_structure_summary(uniprot_id: str) -> str:
    """
    Get a text summary of available structures.
    
    Args:
        uniprot_id: UniProt accession
        
    Returns:
        Human-readable summary
    """
    client = StructureClient()
    data = client.get_all_structures(uniprot_id)
    
    lines = [f"Structure Summary for {uniprot_id}", "=" * 40]
    
    # Experimental structures
    exp = data["experimental"]
    if exp["count"] > 0:
        lines.append(f"\nExperimental Structures: {exp['count']}")
        lines.append(f"Best Resolution: {exp['best_resolution']:.2f}Å" if exp['best_resolution'] else "")
        for s in exp["structures"][:3]:
            lines.append(f"  - {s['pdb_id']}: {s['method']} ({s['resolution']}Å)")
            if s['ligands']:
                lines.append(f"    Ligands: {', '.join(s['ligands'][:5])}")
    else:
        lines.append("\nNo experimental structures available")
    
    # Predicted structure
    pred = data.get("predicted")
    if pred and pred.get("available"):
        lines.append(f"\nAlphaFold Prediction:")
        lines.append(f"  Confidence: {pred['confidence']:.1f} ({pred['confidence_category']})")
        lines.append(f"  Model URL: {pred['model_url']}")
    else:
        lines.append("\nNo AlphaFold prediction available")
    
    return "\n".join(lines)


if __name__ == "__main__":
    # Quick test
    client = StructureClient()
    
    print("Testing Structure Client...")
    
    # Test PDB search
    print("\n1. Searching PDB for EGFR structures...")
    pdb_ids = client.search_pdb(uniprot_id="P00533", limit=5)
    print(f"   Found: {pdb_ids}")
    
    if pdb_ids:
        # Test PDB info
        print(f"\n2. Getting info for {pdb_ids[0]}...")
        info = client.get_pdb_info(pdb_ids[0])
        if info:
            print(f"   Title: {info.title[:60]}...")
            print(f"   Method: {info.method}")
            print(f"   Resolution: {info.resolution}Å")
            print(f"   Ligands: {info.ligands}")
    
    # Test AlphaFold
    print("\n3. Getting AlphaFold structure for P00533...")
    af = client.get_alphafold_structure("P00533")
    if af:
        print(f"   Gene: {af.gene_name}")
        print(f"   Confidence: {af.mean_plddt:.1f} ({af.confidence_category})")
        print(f"   Model URL: {af.model_url[:60]}...")
    
    # Test combined
    print("\n4. Getting all structures...")
    summary = get_structure_summary("P00533")
    print(summary)
    
    print("\n✓ All tests passed!")
