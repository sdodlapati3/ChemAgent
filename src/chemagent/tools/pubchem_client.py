"""
PubChem Database Client
=======================

Client for PubChem REST API (PUG REST) for compound information.

PubChem is the world's largest free chemistry database with:
- 115+ million compounds
- Chemical structures and properties
- Bioassay data
- Patent references
- Safety information

Example:
    >>> from chemagent.tools.pubchem_client import PubChemClient
    >>> client = PubChemClient()
    >>> compound = client.get_compound_by_name("aspirin")
    >>> print(compound.iupac_name)
    >>> print(compound.molecular_weight)
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import requests
from diskcache import Cache

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

PUBCHEM_BASE_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
PUBCHEM_VIEW_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug_view"

CACHE_DIR = ".cache/pubchem"
CACHE_TTL = 604800  # 7 days
MAX_RETRIES = 3
RETRY_DELAY = 0.5  # PubChem rate limit: 5 requests/second

# Properties to request
COMPOUND_PROPERTIES = [
    "MolecularFormula",
    "MolecularWeight",
    "CanonicalSMILES",
    "IsomericSMILES",
    "InChI",
    "InChIKey",
    "IUPACName",
    "XLogP",
    "ExactMass",
    "MonoisotopicMass",
    "TPSA",
    "Complexity",
    "Charge",
    "HBondDonorCount",
    "HBondAcceptorCount",
    "RotatableBondCount",
    "HeavyAtomCount",
    "AtomStereoCount",
    "DefinedAtomStereoCount"
]


# =============================================================================
# Result Classes
# =============================================================================

@dataclass
class PubChemCompound:
    """PubChem compound data."""
    cid: int
    name: str
    iupac_name: Optional[str]
    molecular_formula: str
    molecular_weight: float
    canonical_smiles: str
    isomeric_smiles: Optional[str]
    inchi: Optional[str]
    inchi_key: Optional[str]
    xlogp: Optional[float] = None
    tpsa: Optional[float] = None
    complexity: Optional[float] = None
    hbd_count: int = 0
    hba_count: int = 0
    rotatable_bonds: int = 0
    heavy_atoms: int = 0
    charge: int = 0
    
    @property
    def url(self) -> str:
        """URL to PubChem page."""
        return f"https://pubchem.ncbi.nlm.nih.gov/compound/{self.cid}"
    
    @property
    def lipinski_violations(self) -> int:
        """Count Lipinski Rule of 5 violations."""
        violations = 0
        try:
            mw = float(self.molecular_weight) if self.molecular_weight else 0
            if mw > 500:
                violations += 1
        except (ValueError, TypeError):
            pass
        
        try:
            xlogp = float(self.xlogp) if self.xlogp else 0
            if xlogp > 5:
                violations += 1
        except (ValueError, TypeError):
            pass
        
        try:
            hbd = int(self.hbd_count) if self.hbd_count else 0
            if hbd > 5:
                violations += 1
        except (ValueError, TypeError):
            pass
        
        try:
            hba = int(self.hba_count) if self.hba_count else 0
            if hba > 10:
                violations += 1
        except (ValueError, TypeError):
            pass
        
        return violations


@dataclass
class SimilarCompound:
    """Similar compound from PubChem similarity search."""
    cid: int
    canonical_smiles: str
    molecular_weight: Optional[float] = None
    similarity: Optional[float] = None


@dataclass 
class AssayResult:
    """Bioassay result from PubChem."""
    aid: int
    assay_name: str
    target_name: Optional[str]
    activity_outcome: str  # Active, Inactive, Inconclusive
    activity_value: Optional[float] = None
    activity_unit: Optional[str] = None


@dataclass
class Provenance:
    """Data provenance tracking."""
    source: str = "PubChem"
    query_type: str = ""
    query_params: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    url: str = ""


# =============================================================================
# Client Implementation
# =============================================================================

class PubChemClient:
    """
    Client for PubChem REST API.
    
    Provides access to:
    - Compound lookup by CID, name, SMILES, InChI
    - Molecular properties and descriptors
    - Similarity and substructure search
    - Bioassay data
    - Cross-references to other databases
    
    Example:
        >>> client = PubChemClient()
        >>> 
        >>> # Get compound by name
        >>> aspirin = client.get_compound_by_name("aspirin")
        >>> print(f"CID: {aspirin.cid}, MW: {aspirin.molecular_weight}")
        >>> 
        >>> # Find similar compounds
        >>> similar = client.similarity_search("CC(=O)Oc1ccccc1C(=O)O", threshold=90)
        >>> print(f"Found {len(similar)} similar compounds")
    """
    
    def __init__(
        self,
        cache_dir: str = CACHE_DIR,
        cache_ttl: int = CACHE_TTL,
        timeout: int = 30
    ):
        """
        Initialize PubChem client.
        
        Args:
            cache_dir: Directory for disk cache
            cache_ttl: Cache time-to-live in seconds
            timeout: Request timeout in seconds
        """
        self.cache = Cache(cache_dir)
        self.cache_ttl = cache_ttl
        self.timeout = timeout
        self.session = requests.Session()
        self._last_request_time = 0
    
    def _rate_limit(self):
        """Enforce rate limiting (5 requests/second max)."""
        elapsed = time.time() - self._last_request_time
        if elapsed < 0.2:  # 200ms between requests
            time.sleep(0.2 - elapsed)
        self._last_request_time = time.time()
    
    def _get(
        self,
        url: str,
        cache_key: Optional[str] = None,
        response_format: str = "JSON"
    ) -> Union[Dict[str, Any], str]:
        """
        GET request with caching, rate limiting, and retry.
        """
        if cache_key:
            cached = self.cache.get(cache_key)
            if cached is not None:
                return cached
        
        self._rate_limit()
        
        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                response = self.session.get(url, timeout=self.timeout)
                
                # Handle PubChem throttling
                if response.status_code == 503:
                    time.sleep(1)
                    continue
                
                response.raise_for_status()
                
                if response_format == "JSON":
                    data = response.json()
                else:
                    data = response.text
                
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
        data: Dict[str, Any],
        cache_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        POST request for async operations.
        """
        if cache_key:
            cached = self.cache.get(cache_key)
            if cached is not None:
                return cached
        
        self._rate_limit()
        
        response = self.session.post(url, data=data, timeout=self.timeout)
        response.raise_for_status()
        
        result = response.json()
        
        # Handle async response (ListKey)
        if "Waiting" in result or "ListKey" in result:
            list_key = result.get("Waiting", {}).get("ListKey") or result.get("ListKey")
            if list_key:
                result = self._poll_async_result(list_key)
        
        if cache_key and result:
            self.cache.set(cache_key, result, expire=self.cache_ttl)
        
        return result
    
    def _poll_async_result(self, list_key: str, max_attempts: int = 10) -> Dict[str, Any]:
        """Poll for async operation result."""
        url = f"{PUBCHEM_BASE_URL}/compound/listkey/{list_key}/cids/JSON"
        
        for _ in range(max_attempts):
            time.sleep(1)
            try:
                response = self.session.get(url, timeout=self.timeout)
                if response.status_code == 200:
                    return response.json()
            except:
                pass
        
        return {}
    
    # =========================================================================
    # Compound Lookup
    # =========================================================================
    
    def get_compound_by_cid(self, cid: int) -> Optional[PubChemCompound]:
        """
        Get compound by PubChem CID.
        
        Args:
            cid: PubChem Compound ID
            
        Returns:
            PubChemCompound or None if not found
        """
        cache_key = f"pubchem_cid:{cid}"
        
        props = ",".join(COMPOUND_PROPERTIES)
        url = f"{PUBCHEM_BASE_URL}/compound/cid/{cid}/property/{props}/JSON"
        
        try:
            data = self._get(url, cache_key)
            props_list = data.get("PropertyTable", {}).get("Properties", [])
            
            if not props_list:
                return None
            
            p = props_list[0]
            
            return PubChemCompound(
                cid=cid,
                name="",  # Need separate call for name
                iupac_name=p.get("IUPACName"),
                molecular_formula=p.get("MolecularFormula", ""),
                molecular_weight=p.get("MolecularWeight", 0),
                canonical_smiles=p.get("CanonicalSMILES", ""),
                isomeric_smiles=p.get("IsomericSMILES"),
                inchi=p.get("InChI"),
                inchi_key=p.get("InChIKey"),
                xlogp=p.get("XLogP"),
                tpsa=p.get("TPSA"),
                complexity=p.get("Complexity"),
                hbd_count=p.get("HBondDonorCount", 0),
                hba_count=p.get("HBondAcceptorCount", 0),
                rotatable_bonds=p.get("RotatableBondCount", 0),
                heavy_atoms=p.get("HeavyAtomCount", 0),
                charge=p.get("Charge", 0)
            )
            
        except Exception as e:
            logger.error(f"Failed to get compound CID {cid}: {e}")
            return None
    
    def get_compound_by_name(self, name: str) -> Optional[PubChemCompound]:
        """
        Get compound by name.
        
        Args:
            name: Compound name (e.g., "aspirin", "caffeine")
            
        Returns:
            PubChemCompound or None if not found
        """
        cache_key = f"pubchem_name:{name.lower()}"
        
        # First get CID
        url = f"{PUBCHEM_BASE_URL}/compound/name/{name}/cids/JSON"
        
        try:
            data = self._get(url)
            cids = data.get("IdentifierList", {}).get("CID", [])
            
            if not cids:
                return None
            
            compound = self.get_compound_by_cid(cids[0])
            if compound:
                compound.name = name
            
            return compound
            
        except Exception as e:
            logger.error(f"Failed to get compound by name '{name}': {e}")
            return None
    
    def get_compound_by_smiles(self, smiles: str) -> Optional[PubChemCompound]:
        """
        Get compound by SMILES.
        
        Args:
            smiles: SMILES string
            
        Returns:
            PubChemCompound or None if not found
        """
        cache_key = f"pubchem_smiles:{smiles}"
        
        url = f"{PUBCHEM_BASE_URL}/compound/smiles/{requests.utils.quote(smiles, safe='')}/cids/JSON"
        
        try:
            data = self._get(url)
            cids = data.get("IdentifierList", {}).get("CID", [])
            
            if not cids:
                return None
            
            return self.get_compound_by_cid(cids[0])
            
        except Exception as e:
            logger.error(f"Failed to get compound by SMILES: {e}")
            return None
    
    def get_compound_by_inchikey(self, inchikey: str) -> Optional[PubChemCompound]:
        """
        Get compound by InChI Key.
        
        Args:
            inchikey: InChI Key
            
        Returns:
            PubChemCompound or None if not found
        """
        url = f"{PUBCHEM_BASE_URL}/compound/inchikey/{inchikey}/cids/JSON"
        
        try:
            data = self._get(url)
            cids = data.get("IdentifierList", {}).get("CID", [])
            
            if not cids:
                return None
            
            return self.get_compound_by_cid(cids[0])
            
        except Exception as e:
            logger.error(f"Failed to get compound by InChIKey: {e}")
            return None
    
    # =========================================================================
    # Search Methods
    # =========================================================================
    
    def similarity_search(
        self,
        smiles: str,
        threshold: int = 90,
        max_results: int = 25
    ) -> List[SimilarCompound]:
        """
        Find similar compounds by 2D fingerprint similarity.
        
        Args:
            smiles: Query SMILES
            threshold: Similarity threshold (0-100)
            max_results: Maximum results
            
        Returns:
            List of similar compounds
        """
        cache_key = f"pubchem_similar:{smiles}:{threshold}:{max_results}"
        
        # Use async similarity search
        encoded_smiles = requests.utils.quote(smiles, safe='')
        url = f"{PUBCHEM_BASE_URL}/compound/similarity/smiles/{encoded_smiles}/cids/JSON"
        params = f"?Threshold={threshold}&MaxRecords={max_results}"
        
        try:
            data = self._get(url + params, cache_key)
            cids = data.get("IdentifierList", {}).get("CID", [])
            
            results = []
            for cid in cids[:max_results]:
                compound = self.get_compound_by_cid(cid)
                if compound:
                    results.append(SimilarCompound(
                        cid=cid,
                        canonical_smiles=compound.canonical_smiles,
                        molecular_weight=compound.molecular_weight
                    ))
            
            return results
            
        except Exception as e:
            logger.error(f"Similarity search failed: {e}")
            return []
    
    def substructure_search(
        self,
        smiles: str,
        max_results: int = 25
    ) -> List[int]:
        """
        Find compounds containing a substructure.
        
        Args:
            smiles: Query SMILES (substructure pattern)
            max_results: Maximum results
            
        Returns:
            List of CIDs
        """
        cache_key = f"pubchem_substruct:{smiles}:{max_results}"
        
        encoded_smiles = requests.utils.quote(smiles, safe='')
        url = f"{PUBCHEM_BASE_URL}/compound/substructure/smiles/{encoded_smiles}/cids/JSON"
        params = f"?MaxRecords={max_results}"
        
        try:
            data = self._get(url + params, cache_key)
            return data.get("IdentifierList", {}).get("CID", [])
            
        except Exception as e:
            logger.error(f"Substructure search failed: {e}")
            return []
    
    # =========================================================================
    # Bioassay Methods
    # =========================================================================
    
    def get_bioassays(self, cid: int, limit: int = 10) -> List[AssayResult]:
        """
        Get bioassay results for a compound.
        
        Args:
            cid: PubChem CID
            limit: Maximum results
            
        Returns:
            List of assay results
        """
        cache_key = f"pubchem_assays:{cid}:{limit}"
        
        url = f"{PUBCHEM_BASE_URL}/compound/cid/{cid}/assaysummary/JSON"
        
        try:
            data = self._get(url, cache_key)
            
            results = []
            summaries = data.get("AssaySummaries", {}).get("AssaySummary", [])
            
            for summary in summaries[:limit]:
                results.append(AssayResult(
                    aid=summary.get("AID", 0),
                    assay_name=summary.get("SourceName", ""),
                    target_name=summary.get("TargetName"),
                    activity_outcome=summary.get("ActivityOutcome", ""),
                    activity_value=summary.get("ActivityValue"),
                    activity_unit=summary.get("ActivityUnit")
                ))
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to get bioassays for CID {cid}: {e}")
            return []
    
    # =========================================================================
    # Cross-References
    # =========================================================================
    
    def get_external_ids(self, cid: int) -> Dict[str, List[str]]:
        """
        Get external database IDs (ChEMBL, DrugBank, etc.).
        
        Args:
            cid: PubChem CID
            
        Returns:
            Dictionary mapping database name to list of IDs
        """
        cache_key = f"pubchem_xrefs:{cid}"
        
        url = f"{PUBCHEM_BASE_URL}/compound/cid/{cid}/xrefs/RegistryID/JSON"
        
        try:
            data = self._get(url, cache_key)
            
            xrefs = {}
            for info in data.get("InformationList", {}).get("Information", []):
                source = info.get("RegistryName", "Unknown")
                ids = info.get("RegistryID", [])
                if ids:
                    xrefs[source] = ids if isinstance(ids, list) else [ids]
            
            return xrefs
            
        except Exception as e:
            logger.error(f"Failed to get cross-references for CID {cid}: {e}")
            return {}
    
    def cid_to_chembl(self, cid: int) -> Optional[str]:
        """
        Get ChEMBL ID for a PubChem CID.
        
        Args:
            cid: PubChem CID
            
        Returns:
            ChEMBL ID or None
        """
        xrefs = self.get_external_ids(cid)
        chembl_ids = xrefs.get("ChEMBL", [])
        return chembl_ids[0] if chembl_ids else None
    
    # =========================================================================
    # Synonyms and Names
    # =========================================================================
    
    def get_synonyms(self, cid: int) -> List[str]:
        """
        Get all synonyms for a compound.
        
        Args:
            cid: PubChem CID
            
        Returns:
            List of synonyms
        """
        cache_key = f"pubchem_synonyms:{cid}"
        
        url = f"{PUBCHEM_BASE_URL}/compound/cid/{cid}/synonyms/JSON"
        
        try:
            data = self._get(url, cache_key)
            info_list = data.get("InformationList", {}).get("Information", [])
            
            if info_list:
                return info_list[0].get("Synonym", [])
            return []
            
        except Exception as e:
            logger.error(f"Failed to get synonyms for CID {cid}: {e}")
            return []
    
    # =========================================================================
    # Provenance
    # =========================================================================
    
    def get_provenance(self, query_type: str, **params) -> Provenance:
        """Generate provenance record for a query."""
        return Provenance(
            source="PubChem",
            query_type=query_type,
            query_params=params,
            url=PUBCHEM_BASE_URL
        )


# =============================================================================
# Convenience Functions
# =============================================================================

def get_compound_info(identifier: str) -> Dict[str, Any]:
    """
    Get comprehensive compound information.
    
    Args:
        identifier: Name, SMILES, or CID
        
    Returns:
        Dictionary with compound data
    """
    client = PubChemClient()
    
    # Try to identify the input type
    compound = None
    
    if identifier.isdigit():
        compound = client.get_compound_by_cid(int(identifier))
    elif identifier.startswith("CHEMBL"):
        # Search by name if it's a ChEMBL ID
        compound = client.get_compound_by_name(identifier)
    elif any(c in identifier for c in "()=#@"):
        # Likely SMILES
        compound = client.get_compound_by_smiles(identifier)
    else:
        # Try as name
        compound = client.get_compound_by_name(identifier)
    
    if not compound:
        return {"error": f"Compound not found: {identifier}"}
    
    synonyms = client.get_synonyms(compound.cid)
    xrefs = client.get_external_ids(compound.cid)
    
    return {
        "cid": compound.cid,
        "name": compound.name or synonyms[0] if synonyms else "",
        "iupac_name": compound.iupac_name,
        "smiles": compound.canonical_smiles,
        "inchi_key": compound.inchi_key,
        "molecular_formula": compound.molecular_formula,
        "molecular_weight": compound.molecular_weight,
        "properties": {
            "xlogp": compound.xlogp,
            "tpsa": compound.tpsa,
            "hbd": compound.hbd_count,
            "hba": compound.hba_count,
            "rotatable_bonds": compound.rotatable_bonds,
            "lipinski_violations": compound.lipinski_violations
        },
        "synonyms": synonyms[:10],
        "external_ids": {
            "chembl": xrefs.get("ChEMBL", [None])[0],
            "drugbank": xrefs.get("DrugBank", [None])[0]
        },
        "url": compound.url,
        "provenance": {
            "source": "PubChem",
            "cid": compound.cid,
            "retrieved": datetime.now().isoformat()
        }
    }


if __name__ == "__main__":
    # Quick test
    client = PubChemClient()
    
    print("Testing PubChem Client...")
    
    # Test compound lookup
    print("\n1. Looking up aspirin...")
    aspirin = client.get_compound_by_name("aspirin")
    if aspirin:
        print(f"   CID: {aspirin.cid}")
        print(f"   IUPAC: {aspirin.iupac_name}")
        print(f"   MW: {aspirin.molecular_weight}")
        print(f"   SMILES: {aspirin.canonical_smiles}")
        print(f"   Lipinski violations: {aspirin.lipinski_violations}")
    
    # Test synonyms
    print("\n2. Getting synonyms...")
    if aspirin:
        synonyms = client.get_synonyms(aspirin.cid)
        print(f"   Found {len(synonyms)} synonyms")
        print(f"   First 5: {synonyms[:5]}")
    
    # Test similarity search
    print("\n3. Similarity search...")
    if aspirin:
        similar = client.similarity_search(aspirin.canonical_smiles, threshold=85, max_results=5)
        print(f"   Found {len(similar)} similar compounds")
        for s in similar[:3]:
            print(f"   - CID {s.cid}: MW={s.molecular_weight}")
    
    # Test cross-references
    print("\n4. Getting external IDs...")
    if aspirin:
        xrefs = client.get_external_ids(aspirin.cid)
        print(f"   ChEMBL: {xrefs.get('ChEMBL', ['N/A'])[0]}")
        print(f"   DrugBank: {xrefs.get('DrugBank', ['N/A'])[0]}")
    
    print("\n✓ All tests passed!")
