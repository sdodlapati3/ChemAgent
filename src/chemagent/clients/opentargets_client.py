"""
Open Targets Platform Client.

Provides access to target-disease evidence data via GraphQL API.

Key Features:
- Target validation evidence (genetic, literature, expression)
- Disease associations with scores
- Known drugs per target
- Full provenance tracking

API Documentation: https://platform-docs.opentargets.org/data-access/graphql-api
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import time

logger = logging.getLogger(__name__)

# Check for httpx (async HTTP client)
try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
    logger.warning("httpx not installed. Open Targets client will use requests fallback.")

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

from chemagent.core.provenance import (
    DataSource,
    ProvenanceRecord,
    ProvenanceToolResult,
    EvidenceRecord,
)


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class TargetInfo:
    """Target (gene/protein) information from Open Targets."""
    ensembl_id: str  # e.g., ENSG00000146648 (EGFR)
    symbol: str      # e.g., EGFR
    name: str        # e.g., Epidermal growth factor receptor
    description: Optional[str] = None
    uniprot_ids: List[str] = field(default_factory=list)
    tractability: Optional[Dict[str, Any]] = None


@dataclass
class DiseaseInfo:
    """Disease information from Open Targets."""
    disease_id: str   # e.g., EFO_0001378 (lung adenocarcinoma)
    name: str
    description: Optional[str] = None
    therapeutic_areas: List[str] = field(default_factory=list)


@dataclass
class AssociationScore:
    """Target-disease association score with evidence breakdown."""
    overall_score: float  # 0-1
    data_sources: Dict[str, float] = field(default_factory=dict)
    # Breakdown by evidence type
    literature_score: float = 0.0
    genetic_association_score: float = 0.0
    somatic_mutation_score: float = 0.0
    known_drug_score: float = 0.0
    affected_pathway_score: float = 0.0
    rna_expression_score: float = 0.0
    animal_model_score: float = 0.0


@dataclass
class TargetDiseaseEvidence:
    """Evidence linking a target to a disease."""
    target: TargetInfo
    disease: DiseaseInfo
    association: AssociationScore
    evidence_count: int
    evidence_by_type: Dict[str, int] = field(default_factory=dict)
    top_publications: List[Dict[str, Any]] = field(default_factory=list)
    known_drugs: List[Dict[str, Any]] = field(default_factory=list)


# =============================================================================
# GraphQL Queries
# =============================================================================

SEARCH_TARGET_QUERY = """
query SearchTarget($queryString: String!) {
  search(queryString: $queryString, entityNames: ["target"], page: {size: 5, index: 0}) {
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

SEARCH_DISEASE_QUERY = """
query SearchDisease($queryString: String!) {
  search(queryString: $queryString, entityNames: ["disease"], page: {size: 5, index: 0}) {
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

TARGET_INFO_QUERY = """
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
    tractability {
      antibody {
        topCategory
      }
      smallmolecule {
        topCategory
      }
    }
  }
}
"""

ASSOCIATION_QUERY = """
query AssociationQuery($ensemblId: String!, $efoId: String!) {
  disease(efoId: $efoId) {
    id
    name
    description
    associatedTargets(
      page: {size: 1, index: 0}
      Bs: [$ensemblId]
    ) {
      rows {
        target {
          id
          approvedSymbol
          approvedName
        }
        score
        datatypeScores {
          id
          score
        }
      }
    }
  }
}
"""

EVIDENCE_QUERY = """
query EvidenceQuery($ensemblId: String!, $efoId: String!) {
  target(ensemblId: $ensemblId) {
    id
    approvedSymbol
    evidences(
      efoIds: [$efoId]
      size: 100
    ) {
      count
      rows {
        id
        score
        datasourceId
        datatypeId
        literature
        diseaseFromSource
        targetFromSourceId
      }
    }
    knownDrugs(
      freeTextQuery: ""
      size: 10
    ) {
      uniqueDrugs
      rows {
        drug {
          id
          name
          maximumClinicalTrialPhase
        }
        phase
        status
        diseaseId
        disease {
          id
          name
        }
      }
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
    
    Usage:
        client = OpenTargetsClient()
        
        # Search for a target
        targets = client.search_target("EGFR")
        
        # Get target-disease evidence
        evidence = client.get_target_disease_evidence("ENSG00000146648", "EFO_0001378")
    """
    
    BASE_URL = "https://api.platform.opentargets.org/api/v4/graphql"
    
    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout
        self._session = None
    
    def _get_session(self):
        """Get or create HTTP session."""
        if self._session is None:
            if HTTPX_AVAILABLE:
                self._session = httpx.Client(timeout=self.timeout)
            elif REQUESTS_AVAILABLE:
                self._session = requests.Session()
            else:
                raise RuntimeError("Neither httpx nor requests available")
        return self._session
    
    def _execute_query(
        self, 
        query: str, 
        variables: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a GraphQL query."""
        session = self._get_session()
        
        payload = {
            "query": query,
            "variables": variables
        }
        
        try:
            if HTTPX_AVAILABLE:
                response = session.post(self.BASE_URL, json=payload)
                response.raise_for_status()
                return response.json()
            else:
                response = session.post(
                    self.BASE_URL, 
                    json=payload,
                    timeout=self.timeout
                )
                response.raise_for_status()
                return response.json()
                
        except Exception as e:
            logger.error(f"Open Targets query failed: {e}")
            raise
    
    def search_target(self, query: str) -> ProvenanceToolResult:
        """
        Search for targets by name or symbol.
        
        Args:
            query: Search term (e.g., "EGFR", "epidermal growth factor")
        
        Returns:
            ProvenanceToolResult with list of matching targets
        """
        start_time = time.time()
        
        try:
            result = self._execute_query(SEARCH_TARGET_QUERY, {"queryString": query})
            
            hits = result.get("data", {}).get("search", {}).get("hits", [])
            
            targets = []
            provenance_records = []
            
            for hit in hits:
                if hit.get("entity") == "target":
                    target = {
                        "ensembl_id": hit["id"],
                        "name": hit.get("name", ""),
                        "description": hit.get("description", "")
                    }
                    targets.append(target)
                    
                    provenance_records.append(ProvenanceRecord(
                        source=DataSource.OPENTARGETS,
                        record_id=hit["id"],
                        record_type="target",
                        query_params={"search": query}
                    ))
            
            execution_time = (time.time() - start_time) * 1000
            
            return ProvenanceToolResult(
                tool_name="open_targets_search_target",
                query=query,
                success=True,
                data={"targets": targets, "total": len(targets)},
                provenance_records=provenance_records,
                execution_time_ms=execution_time
            )
            
        except Exception as e:
            return ProvenanceToolResult(
                tool_name="open_targets_search_target",
                query=query,
                success=False,
                data=None,
                error=str(e),
                execution_time_ms=(time.time() - start_time) * 1000
            )
    
    def search_disease(self, query: str) -> ProvenanceToolResult:
        """
        Search for diseases by name.
        
        Args:
            query: Search term (e.g., "lung cancer", "diabetes")
        
        Returns:
            ProvenanceToolResult with list of matching diseases
        """
        start_time = time.time()
        
        try:
            result = self._execute_query(SEARCH_DISEASE_QUERY, {"queryString": query})
            
            hits = result.get("data", {}).get("search", {}).get("hits", [])
            
            diseases = []
            provenance_records = []
            
            for hit in hits:
                if hit.get("entity") == "disease":
                    disease = {
                        "efo_id": hit["id"],
                        "name": hit.get("name", ""),
                        "description": hit.get("description", "")
                    }
                    diseases.append(disease)
                    
                    provenance_records.append(ProvenanceRecord(
                        source=DataSource.OPENTARGETS,
                        record_id=hit["id"],
                        record_type="disease",
                        query_params={"search": query}
                    ))
            
            execution_time = (time.time() - start_time) * 1000
            
            return ProvenanceToolResult(
                tool_name="open_targets_search_disease",
                query=query,
                success=True,
                data={"diseases": diseases, "total": len(diseases)},
                provenance_records=provenance_records,
                execution_time_ms=execution_time
            )
            
        except Exception as e:
            return ProvenanceToolResult(
                tool_name="open_targets_search_disease",
                query=query,
                success=False,
                data=None,
                error=str(e),
                execution_time_ms=(time.time() - start_time) * 1000
            )
    
    def get_target_info(self, ensembl_id: str) -> ProvenanceToolResult:
        """
        Get detailed information about a target.
        
        Args:
            ensembl_id: Ensembl gene ID (e.g., ENSG00000146648)
        
        Returns:
            ProvenanceToolResult with target details
        """
        start_time = time.time()
        
        try:
            result = self._execute_query(TARGET_INFO_QUERY, {"ensemblId": ensembl_id})
            
            target_data = result.get("data", {}).get("target")
            
            if not target_data:
                return ProvenanceToolResult(
                    tool_name="open_targets_get_target",
                    query=ensembl_id,
                    success=False,
                    data=None,
                    error=f"Target not found: {ensembl_id}",
                    execution_time_ms=(time.time() - start_time) * 1000
                )
            
            # Extract UniProt IDs
            uniprot_ids = [
                p["id"] for p in target_data.get("proteinIds", [])
                if p.get("source") == "uniprot_swissprot"
            ]
            
            target = {
                "ensembl_id": target_data["id"],
                "symbol": target_data.get("approvedSymbol", ""),
                "name": target_data.get("approvedName", ""),
                "biotype": target_data.get("biotype", ""),
                "uniprot_ids": uniprot_ids,
                "tractability": target_data.get("tractability")
            }
            
            provenance = ProvenanceRecord(
                source=DataSource.OPENTARGETS,
                record_id=ensembl_id,
                record_type="target",
                query_params={"ensembl_id": ensembl_id}
            )
            
            return ProvenanceToolResult(
                tool_name="open_targets_get_target",
                query=ensembl_id,
                success=True,
                data=target,
                provenance_records=[provenance],
                execution_time_ms=(time.time() - start_time) * 1000
            )
            
        except Exception as e:
            return ProvenanceToolResult(
                tool_name="open_targets_get_target",
                query=ensembl_id,
                success=False,
                data=None,
                error=str(e),
                execution_time_ms=(time.time() - start_time) * 1000
            )
    
    def get_target_disease_evidence(
        self, 
        ensembl_id: str, 
        efo_id: str
    ) -> ProvenanceToolResult:
        """
        Get evidence linking a target to a disease.
        
        This is the key function for target validation queries like:
        "What's the evidence that EGFR is implicated in lung cancer?"
        
        Args:
            ensembl_id: Ensembl gene ID (e.g., ENSG00000146648 for EGFR)
            efo_id: EFO disease ID (e.g., EFO_0001378 for lung adenocarcinoma)
        
        Returns:
            ProvenanceToolResult with association scores and evidence
        """
        start_time = time.time()
        query_desc = f"{ensembl_id} - {efo_id}"
        
        try:
            # Get association data
            assoc_result = self._execute_query(ASSOCIATION_QUERY, {
                "ensemblId": ensembl_id,
                "efoId": efo_id
            })
            
            # Get detailed evidence
            evidence_result = self._execute_query(EVIDENCE_QUERY, {
                "ensemblId": ensembl_id,
                "efoId": efo_id
            })
            
            # Parse association
            disease_data = assoc_result.get("data", {}).get("disease", {})
            association_rows = disease_data.get("associatedTargets", {}).get("rows", [])
            
            if not association_rows:
                return ProvenanceToolResult(
                    tool_name="open_targets_get_evidence",
                    query=query_desc,
                    success=True,
                    data={
                        "association_found": False,
                        "message": f"No association found between {ensembl_id} and {efo_id}"
                    },
                    provenance_records=[],
                    execution_time_ms=(time.time() - start_time) * 1000
                )
            
            assoc = association_rows[0]
            overall_score = assoc.get("score", 0)
            
            # Parse datatype scores
            datatype_scores = {}
            for ds in assoc.get("datatypeScores", []):
                datatype_scores[ds["id"]] = ds["score"]
            
            # Parse evidence
            target_evidence = evidence_result.get("data", {}).get("target", {})
            evidences = target_evidence.get("evidences", {})
            evidence_count = evidences.get("count", 0)
            
            # Count evidence by type
            evidence_by_type = {}
            for row in evidences.get("rows", []):
                dtype = row.get("datatypeId", "unknown")
                evidence_by_type[dtype] = evidence_by_type.get(dtype, 0) + 1
            
            # Get known drugs
            known_drugs_data = target_evidence.get("knownDrugs", {})
            unique_drugs = known_drugs_data.get("uniqueDrugs", 0)
            drugs = []
            for row in known_drugs_data.get("rows", [])[:5]:
                drug = row.get("drug", {})
                drugs.append({
                    "id": drug.get("id"),
                    "name": drug.get("name"),
                    "phase": drug.get("maximumClinicalTrialPhase"),
                    "indication": row.get("disease", {}).get("name")
                })
            
            # Build evidence records for provenance
            evidence_records = []
            
            if datatype_scores.get("literature", 0) > 0:
                evidence_records.append(EvidenceRecord(
                    evidence_type="literature",
                    description=f"Literature evidence linking {ensembl_id} to {efo_id}",
                    value=datatype_scores.get("literature"),
                    confidence=datatype_scores.get("literature"),
                    provenance=ProvenanceRecord(
                        source=DataSource.OPENTARGETS,
                        record_id=f"{ensembl_id}_{efo_id}_literature",
                        record_type="evidence"
                    )
                ))
            
            if datatype_scores.get("genetic_association", 0) > 0:
                evidence_records.append(EvidenceRecord(
                    evidence_type="genetic",
                    description=f"Genetic association evidence (GWAS, etc.)",
                    value=datatype_scores.get("genetic_association"),
                    confidence=datatype_scores.get("genetic_association"),
                    provenance=ProvenanceRecord(
                        source=DataSource.OPENTARGETS,
                        record_id=f"{ensembl_id}_{efo_id}_genetic",
                        record_type="evidence"
                    )
                ))
            
            # Build result
            data = {
                "association_found": True,
                "target": {
                    "ensembl_id": ensembl_id,
                    "symbol": assoc.get("target", {}).get("approvedSymbol"),
                    "name": assoc.get("target", {}).get("approvedName")
                },
                "disease": {
                    "efo_id": efo_id,
                    "name": disease_data.get("name")
                },
                "association_score": overall_score,
                "datatype_scores": datatype_scores,
                "evidence_count": evidence_count,
                "evidence_by_type": evidence_by_type,
                "known_drugs": {
                    "count": unique_drugs,
                    "examples": drugs
                }
            }
            
            provenance = ProvenanceRecord(
                source=DataSource.OPENTARGETS,
                record_id=f"{ensembl_id}_{efo_id}",
                record_type="evidence",
                query_params={"target": ensembl_id, "disease": efo_id},
                confidence=overall_score
            )
            
            return ProvenanceToolResult(
                tool_name="open_targets_get_evidence",
                query=query_desc,
                success=True,
                data=data,
                provenance_records=[provenance],
                evidence=evidence_records,
                execution_time_ms=(time.time() - start_time) * 1000
            )
            
        except Exception as e:
            logger.error(f"Open Targets evidence query failed: {e}")
            return ProvenanceToolResult(
                tool_name="open_targets_get_evidence",
                query=query_desc,
                success=False,
                data=None,
                error=str(e),
                execution_time_ms=(time.time() - start_time) * 1000
            )
    
    def get_target_associations(
        self,
        ensembl_id: str,
        limit: int = 10
    ) -> ProvenanceToolResult:
        """
        Get all disease associations for a target.
        
        Args:
            ensembl_id: Ensembl gene ID
            limit: Maximum number of associations to return
        
        Returns:
            ProvenanceToolResult with list of associated diseases
        """
        query = f"""
        query TargetAssociations($ensemblId: String!) {{
          target(ensemblId: $ensemblId) {{
            id
            approvedSymbol
            associatedDiseases(page: {{size: {limit}, index: 0}}) {{
              count
              rows {{
                disease {{
                  id
                  name
                }}
                score
                datatypeScores {{
                  id
                  score
                }}
              }}
            }}
          }}
        }}
        """
        
        start_time = time.time()
        
        try:
            result = self._execute_query(query, {"ensemblId": ensembl_id})
            
            target_data = result.get("data", {}).get("target", {})
            associations = target_data.get("associatedDiseases", {})
            
            diseases = []
            provenance_records = []
            
            for row in associations.get("rows", []):
                disease = row.get("disease", {})
                diseases.append({
                    "efo_id": disease.get("id"),
                    "name": disease.get("name"),
                    "association_score": row.get("score"),
                    "datatype_scores": {
                        ds["id"]: ds["score"] 
                        for ds in row.get("datatypeScores", [])
                    }
                })
                
                provenance_records.append(ProvenanceRecord(
                    source=DataSource.OPENTARGETS,
                    record_id=f"{ensembl_id}_{disease.get('id')}",
                    record_type="association",
                    confidence=row.get("score")
                ))
            
            return ProvenanceToolResult(
                tool_name="open_targets_get_associations",
                query=ensembl_id,
                success=True,
                data={
                    "target": {
                        "ensembl_id": ensembl_id,
                        "symbol": target_data.get("approvedSymbol")
                    },
                    "total_associations": associations.get("count", 0),
                    "diseases": diseases
                },
                provenance_records=provenance_records,
                execution_time_ms=(time.time() - start_time) * 1000
            )
            
        except Exception as e:
            return ProvenanceToolResult(
                tool_name="open_targets_get_associations",
                query=ensembl_id,
                success=False,
                data=None,
                error=str(e),
                execution_time_ms=(time.time() - start_time) * 1000
            )


# =============================================================================
# Singleton
# =============================================================================

_client: Optional[OpenTargetsClient] = None

def get_open_targets_client() -> OpenTargetsClient:
    """Get or create Open Targets client singleton."""
    global _client
    if _client is None:
        _client = OpenTargetsClient()
    return _client
