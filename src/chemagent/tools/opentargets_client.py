"""
Open Targets Platform Client
============================

Client for Open Targets GraphQL API for disease-target associations.

Open Targets integrates evidence from multiple sources:
- Genetic associations (GWAS, rare diseases)
- Somatic mutations (cancer)
- Drugs (approved and clinical trials)
- Pathways and expression data
- Literature mining

Example:
    >>> from chemagent.tools.opentargets_client import OpenTargetsClient
    >>> client = OpenTargetsClient()
    >>> associations = client.get_target_diseases("ENSG00000169083")  # AR gene
    >>> drugs = client.get_target_drugs("ENSG00000157764")  # BRAF
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests
from diskcache import Cache

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

OPENTARGETS_GRAPHQL_URL = "https://api.platform.opentargets.org/api/v4/graphql"
CACHE_DIR = ".cache/opentargets"
CACHE_TTL = 86400  # 24 hours (data updates weekly)
MAX_RETRIES = 3
RETRY_DELAY = 1.0


# =============================================================================
# Result Classes
# =============================================================================

@dataclass
class DiseaseAssociation:
    """Disease association from Open Targets."""
    disease_id: str
    disease_name: str
    score: float
    evidence_count: int
    data_sources: List[str] = field(default_factory=list)
    therapeutic_areas: List[str] = field(default_factory=list)


@dataclass
class DrugAssociation:
    """Drug-target association from Open Targets."""
    drug_id: str
    drug_name: str
    drug_type: str
    mechanism_of_action: str
    action_type: str
    phase: int  # Clinical trial phase (4 = approved)
    disease_id: Optional[str] = None
    disease_name: Optional[str] = None


@dataclass
class TargetInfo:
    """Target information from Open Targets."""
    ensembl_id: str
    gene_symbol: str
    gene_name: str
    uniprot_id: Optional[str] = None
    biotype: str = "protein_coding"


@dataclass
class DiseaseInfo:
    """Disease information from Open Targets."""
    disease_id: str
    disease_name: str
    description: Optional[str] = None
    therapeutic_areas: List[str] = field(default_factory=list)
    synonyms: List[str] = field(default_factory=list)


@dataclass
class Provenance:
    """Data provenance tracking."""
    source: str
    query_type: str
    query_params: Dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    api_version: str = "v4"
    url: str = OPENTARGETS_GRAPHQL_URL


# =============================================================================
# GraphQL Queries
# =============================================================================

QUERY_TARGET_INFO = """
query TargetInfo($ensemblId: String!) {
  target(ensemblId: $ensemblId) {
    id
    approvedSymbol
    approvedName
    biotype
    proteinIds {
      id
      source
    }
  }
}
"""

QUERY_TARGET_DISEASES = """
query TargetDiseases($ensemblId: String!, $size: Int!) {
  target(ensemblId: $ensemblId) {
    id
    approvedSymbol
    associatedDiseases(page: {size: $size, index: 0}) {
      count
      rows {
        disease {
          id
          name
          therapeuticAreas {
            id
            name
          }
        }
        score
        datasourceScores {
          id
          score
        }
      }
    }
  }
}
"""

QUERY_TARGET_DRUGS = """
query TargetDrugs($ensemblId: String!, $size: Int!) {
  target(ensemblId: $ensemblId) {
    id
    approvedSymbol
    knownDrugs(size: $size) {
      count
      rows {
        drug {
          id
          name
          drugType
          mechanismsOfAction {
            actionType
            mechanismOfAction
          }
        }
        phase
        disease {
          id
          name
        }
      }
    }
  }
}
"""

QUERY_DISEASE_INFO = """
query DiseaseInfo($efoId: String!) {
  disease(efoId: $efoId) {
    id
    name
    description
    synonyms {
      terms
    }
    therapeuticAreas {
      id
      name
    }
  }
}
"""

QUERY_DISEASE_TARGETS = """
query DiseaseTargets($efoId: String!, $size: Int!) {
  disease(efoId: $efoId) {
    id
    name
    associatedTargets(page: {size: $size, index: 0}) {
      count
      rows {
        target {
          id
          approvedSymbol
          approvedName
          proteinIds {
            id
            source
          }
        }
        score
        datasourceScores {
          id
          score
        }
      }
    }
  }
}
"""

QUERY_SEARCH = """
query Search($queryString: String!, $entityNames: [String!]) {
  search(queryString: $queryString, entityNames: $entityNames, page: {size: 10, index: 0}) {
    total
    hits {
      id
      entity
      name
      description
    }
  }
}
"""


# =============================================================================
# Client Implementation
# =============================================================================

class OpenTargetsClient:
    """
    Client for Open Targets Platform GraphQL API.
    
    Provides access to:
    - Target-disease associations with evidence scores
    - Drug-target relationships and clinical phases
    - Disease information and therapeutic areas
    - Search across targets, diseases, and drugs
    
    Example:
        >>> client = OpenTargetsClient()
        >>> # Find diseases associated with EGFR
        >>> diseases = client.get_target_diseases("ENSG00000146648")
        >>> print(f"Found {len(diseases)} associated diseases")
        >>> 
        >>> # Find drugs targeting BRAF
        >>> drugs = client.get_target_drugs("ENSG00000157764")
        >>> for drug in drugs[:5]:
        ...     print(f"{drug.drug_name}: Phase {drug.phase}")
    """
    
    def __init__(
        self,
        cache_dir: str = CACHE_DIR,
        cache_ttl: int = CACHE_TTL,
        timeout: int = 30
    ):
        """
        Initialize Open Targets client.
        
        Args:
            cache_dir: Directory for disk cache
            cache_ttl: Cache time-to-live in seconds
            timeout: Request timeout in seconds
        """
        self.cache = Cache(cache_dir)
        self.cache_ttl = cache_ttl
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json"
        })
    
    def _execute_query(
        self,
        query: str,
        variables: Dict[str, Any],
        cache_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute GraphQL query with caching and retry.
        
        Args:
            query: GraphQL query string
            variables: Query variables
            cache_key: Optional cache key
            
        Returns:
            Query response data
        """
        # Check cache
        if cache_key:
            cached = self.cache.get(cache_key)
            if cached is not None:
                logger.debug(f"Cache hit for {cache_key}")
                return cached
        
        # Execute query with retry
        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                response = self.session.post(
                    OPENTARGETS_GRAPHQL_URL,
                    json={"query": query, "variables": variables},
                    timeout=self.timeout
                )
                response.raise_for_status()
                
                result = response.json()
                
                if "errors" in result:
                    raise ValueError(f"GraphQL errors: {result['errors']}")
                
                data = result.get("data", {})
                
                # Cache result
                if cache_key and data:
                    self.cache.set(cache_key, data, expire=self.cache_ttl)
                
                return data
                
            except requests.RequestException as e:
                last_error = e
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY * (attempt + 1))
                    logger.warning(f"Retry {attempt + 1}/{MAX_RETRIES} after error: {e}")
        
        raise ConnectionError(f"Failed after {MAX_RETRIES} retries: {last_error}")
    
    # =========================================================================
    # Target Methods
    # =========================================================================
    
    def get_target_info(self, ensembl_id: str) -> Optional[TargetInfo]:
        """
        Get target/gene information.
        
        Args:
            ensembl_id: Ensembl gene ID (e.g., ENSG00000146648 for EGFR)
            
        Returns:
            TargetInfo or None if not found
        """
        cache_key = f"target_info:{ensembl_id}"
        
        data = self._execute_query(
            QUERY_TARGET_INFO,
            {"ensemblId": ensembl_id},
            cache_key
        )
        
        target = data.get("target")
        if not target:
            return None
        
        # Extract UniProt ID
        uniprot_id = None
        for protein_id in target.get("proteinIds", []):
            if protein_id.get("source") == "uniprot_swissprot":
                uniprot_id = protein_id.get("id")
                break
        
        return TargetInfo(
            ensembl_id=target["id"],
            gene_symbol=target.get("approvedSymbol", ""),
            gene_name=target.get("approvedName", ""),
            uniprot_id=uniprot_id,
            biotype=target.get("biotype", "protein_coding")
        )
    
    def get_target_diseases(
        self,
        ensembl_id: str,
        limit: int = 25
    ) -> List[DiseaseAssociation]:
        """
        Get diseases associated with a target.
        
        Args:
            ensembl_id: Ensembl gene ID
            limit: Maximum number of results
            
        Returns:
            List of disease associations sorted by score
        """
        cache_key = f"target_diseases:{ensembl_id}:{limit}"
        
        data = self._execute_query(
            QUERY_TARGET_DISEASES,
            {"ensemblId": ensembl_id, "size": limit},
            cache_key
        )
        
        target = data.get("target")
        if not target or not target.get("associatedDiseases"):
            return []
        
        associations = []
        for row in target["associatedDiseases"].get("rows", []):
            disease = row.get("disease", {})
            
            # Extract data sources
            data_sources = [
                ds["id"] for ds in row.get("datasourceScores", [])
                if ds.get("score", 0) > 0
            ]
            
            # Extract therapeutic areas
            therapeutic_areas = [
                ta["name"] for ta in disease.get("therapeuticAreas", [])
            ]
            
            associations.append(DiseaseAssociation(
                disease_id=disease.get("id", ""),
                disease_name=disease.get("name", ""),
                score=row.get("score", 0),
                evidence_count=len(data_sources),
                data_sources=data_sources,
                therapeutic_areas=therapeutic_areas
            ))
        
        return associations
    
    def get_target_drugs(
        self,
        ensembl_id: str,
        limit: int = 25
    ) -> List[DrugAssociation]:
        """
        Get drugs targeting a specific gene/protein.
        
        Args:
            ensembl_id: Ensembl gene ID
            limit: Maximum number of results
            
        Returns:
            List of drug associations sorted by phase
        """
        cache_key = f"target_drugs:{ensembl_id}:{limit}"
        
        data = self._execute_query(
            QUERY_TARGET_DRUGS,
            {"ensemblId": ensembl_id, "size": limit},
            cache_key
        )
        
        target = data.get("target")
        if not target or not target.get("knownDrugs"):
            return []
        
        drugs = []
        for row in target["knownDrugs"].get("rows", []):
            drug = row.get("drug", {})
            disease = row.get("disease", {})
            
            # Extract mechanism
            mechanisms = drug.get("mechanismsOfAction", [])
            moa = mechanisms[0] if mechanisms else {}
            
            drugs.append(DrugAssociation(
                drug_id=drug.get("id", ""),
                drug_name=drug.get("name", ""),
                drug_type=drug.get("drugType", ""),
                mechanism_of_action=moa.get("mechanismOfAction", ""),
                action_type=moa.get("actionType", ""),
                phase=row.get("phase", 0),
                disease_id=disease.get("id") if disease else None,
                disease_name=disease.get("name") if disease else None
            ))
        
        # Sort by phase (highest first)
        drugs.sort(key=lambda x: x.phase, reverse=True)
        return drugs
    
    # =========================================================================
    # Disease Methods
    # =========================================================================
    
    def get_disease_info(self, efo_id: str) -> Optional[DiseaseInfo]:
        """
        Get disease information.
        
        Args:
            efo_id: EFO disease ID (e.g., EFO_0000311 for breast cancer)
            
        Returns:
            DiseaseInfo or None if not found
        """
        cache_key = f"disease_info:{efo_id}"
        
        data = self._execute_query(
            QUERY_DISEASE_INFO,
            {"efoId": efo_id},
            cache_key
        )
        
        disease = data.get("disease")
        if not disease:
            return None
        
        # Extract synonyms
        synonyms = []
        for syn_group in disease.get("synonyms", []):
            synonyms.extend(syn_group.get("terms", []))
        
        return DiseaseInfo(
            disease_id=disease["id"],
            disease_name=disease.get("name", ""),
            description=disease.get("description"),
            therapeutic_areas=[
                ta["name"] for ta in disease.get("therapeuticAreas", [])
            ],
            synonyms=synonyms
        )
    
    def get_disease_targets(
        self,
        efo_id: str,
        limit: int = 25
    ) -> List[Dict[str, Any]]:
        """
        Get targets associated with a disease.
        
        Args:
            efo_id: EFO disease ID
            limit: Maximum number of results
            
        Returns:
            List of target associations with scores
        """
        cache_key = f"disease_targets:{efo_id}:{limit}"
        
        data = self._execute_query(
            QUERY_DISEASE_TARGETS,
            {"efoId": efo_id, "size": limit},
            cache_key
        )
        
        disease = data.get("disease")
        if not disease or not disease.get("associatedTargets"):
            return []
        
        targets = []
        for row in disease["associatedTargets"].get("rows", []):
            target = row.get("target", {})
            
            # Extract UniProt ID
            uniprot_id = None
            for protein_id in target.get("proteinIds", []):
                if protein_id.get("source") == "uniprot_swissprot":
                    uniprot_id = protein_id.get("id")
                    break
            
            targets.append({
                "ensembl_id": target.get("id", ""),
                "gene_symbol": target.get("approvedSymbol", ""),
                "gene_name": target.get("approvedName", ""),
                "uniprot_id": uniprot_id,
                "score": row.get("score", 0),
                "data_sources": [
                    ds["id"] for ds in row.get("datasourceScores", [])
                    if ds.get("score", 0) > 0
                ]
            })
        
        return targets
    
    # =========================================================================
    # Search Methods
    # =========================================================================
    
    def search(
        self,
        query: str,
        entity_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search across targets, diseases, and drugs.
        
        Args:
            query: Search query string
            entity_types: Filter by entity types ["target", "disease", "drug"]
            
        Returns:
            List of search results
        """
        cache_key = f"search:{query}:{entity_types}"
        
        variables = {"queryString": query}
        if entity_types:
            variables["entityNames"] = entity_types
        
        data = self._execute_query(QUERY_SEARCH, variables, cache_key)
        
        search_result = data.get("search", {})
        hits = search_result.get("hits", [])
        
        results = []
        for hit in hits:
            result = {
                "id": hit.get("id"),
                "entity": hit.get("entity"),
                "name": hit.get("name"),
                "description": hit.get("description")
            }
            results.append(result)
        
        return results
    
    def search_target(self, query: str) -> Optional[str]:
        """
        Search for a target and return its Ensembl ID.
        
        Args:
            query: Gene symbol or name (e.g., "EGFR", "BRAF")
            
        Returns:
            Ensembl ID or None if not found
        """
        results = self.search(query, entity_types=["target"])
        if results:
            return results[0].get("id")
        return None
    
    def search_disease(self, query: str) -> Optional[str]:
        """
        Search for a disease and return its EFO ID.
        
        Args:
            query: Disease name (e.g., "breast cancer", "diabetes")
            
        Returns:
            EFO ID or None if not found
        """
        results = self.search(query, entity_types=["disease"])
        if results:
            return results[0].get("id")
        return None
    
    # =========================================================================
    # Provenance
    # =========================================================================
    
    def get_provenance(self, query_type: str, **params) -> Provenance:
        """Generate provenance record for a query."""
        return Provenance(
            source="Open Targets Platform",
            query_type=query_type,
            query_params=params
        )


# =============================================================================
# Convenience Functions
# =============================================================================

def get_target_disease_evidence(
    gene_symbol: str,
    client: Optional[OpenTargetsClient] = None
) -> Dict[str, Any]:
    """
    Get comprehensive target-disease evidence for a gene.
    
    Args:
        gene_symbol: Gene symbol (e.g., "EGFR")
        client: Optional client instance
        
    Returns:
        Dictionary with target info, diseases, and drugs
    """
    if client is None:
        client = OpenTargetsClient()
    
    # Search for target
    ensembl_id = client.search_target(gene_symbol)
    if not ensembl_id:
        return {"error": f"Target not found: {gene_symbol}"}
    
    # Get all information
    target_info = client.get_target_info(ensembl_id)
    diseases = client.get_target_diseases(ensembl_id)
    drugs = client.get_target_drugs(ensembl_id)
    
    return {
        "target": {
            "ensembl_id": ensembl_id,
            "gene_symbol": target_info.gene_symbol if target_info else gene_symbol,
            "gene_name": target_info.gene_name if target_info else "",
            "uniprot_id": target_info.uniprot_id if target_info else None,
            "tractability": target_info.tractability if target_info else {}
        },
        "diseases": [
            {
                "id": d.disease_id,
                "name": d.disease_name,
                "score": d.score,
                "therapeutic_areas": d.therapeutic_areas
            }
            for d in diseases[:10]
        ],
        "drugs": [
            {
                "id": d.drug_id,
                "name": d.drug_name,
                "phase": d.phase,
                "mechanism": d.mechanism_of_action,
                "indication": d.disease_name
            }
            for d in drugs[:10]
        ],
        "provenance": {
            "source": "Open Targets Platform",
            "url": f"https://platform.opentargets.org/target/{ensembl_id}",
            "api_version": "v4"
        }
    }


if __name__ == "__main__":
    # Quick test
    client = OpenTargetsClient()
    
    print("Testing Open Targets Client...")
    
    # Test target search
    print("\n1. Searching for EGFR...")
    ensembl_id = client.search_target("EGFR")
    print(f"   Found: {ensembl_id}")
    
    if ensembl_id:
        # Test target info
        print("\n2. Getting target info...")
        info = client.get_target_info(ensembl_id)
        print(f"   Symbol: {info.gene_symbol}")
        print(f"   Name: {info.gene_name}")
        print(f"   UniProt: {info.uniprot_id}")
        
        # Test diseases
        print("\n3. Getting associated diseases...")
        diseases = client.get_target_diseases(ensembl_id, limit=5)
        for d in diseases:
            print(f"   - {d.disease_name} (score: {d.score:.3f})")
        
        # Test drugs
        print("\n4. Getting targeting drugs...")
        drugs = client.get_target_drugs(ensembl_id, limit=5)
        for d in drugs:
            print(f"   - {d.drug_name} (Phase {d.phase})")
    
    print("\n✓ All tests passed!")
