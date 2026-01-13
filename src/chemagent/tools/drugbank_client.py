"""
DrugBank client for drug interactions, FDA status, and clinical information.

This module provides access to drug data through multiple sources:
1. DrugBank API (requires license for full access)
2. Open source alternatives (RxNav, OpenFDA)
3. Local caching for performance

Note: Full DrugBank API requires commercial license. This implementation
uses open-source alternatives where possible and provides a framework
for licensed DrugBank access.
"""

import json
import logging
import hashlib
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Any, Tuple
from pathlib import Path
import time

import requests

logger = logging.getLogger(__name__)


# =============================================================================
# Data Models
# =============================================================================

class ApprovalStatus(Enum):
    """FDA approval status categories."""
    APPROVED = "approved"
    INVESTIGATIONAL = "investigational"
    WITHDRAWN = "withdrawn"
    DISCONTINUED = "discontinued"
    UNKNOWN = "unknown"


class InteractionSeverity(Enum):
    """Drug interaction severity levels."""
    MAJOR = "major"        # May cause serious clinical consequences
    MODERATE = "moderate"  # May cause clinical consequences
    MINOR = "minor"        # Limited clinical effect
    UNKNOWN = "unknown"


@dataclass
class DrugInteraction:
    """A drug-drug interaction record."""
    drug_a: str
    drug_b: str
    severity: InteractionSeverity
    description: str
    mechanism: Optional[str] = None
    management: Optional[str] = None
    references: List[str] = field(default_factory=list)


@dataclass
class DrugInfo:
    """Comprehensive drug information."""
    name: str
    generic_name: Optional[str] = None
    brand_names: List[str] = field(default_factory=list)
    
    # Identifiers
    drugbank_id: Optional[str] = None
    rxcui: Optional[str] = None  # RxNorm Concept Unique Identifier
    chembl_id: Optional[str] = None
    pubchem_cid: Optional[str] = None
    cas_number: Optional[str] = None
    
    # Chemical info
    smiles: Optional[str] = None
    inchi: Optional[str] = None
    molecular_formula: Optional[str] = None
    molecular_weight: Optional[float] = None
    
    # Clinical info
    description: Optional[str] = None
    indication: Optional[str] = None
    pharmacodynamics: Optional[str] = None
    mechanism_of_action: Optional[str] = None
    
    # Regulatory
    approval_status: ApprovalStatus = ApprovalStatus.UNKNOWN
    fda_labels: List[str] = field(default_factory=list)
    
    # Categories
    drug_categories: List[str] = field(default_factory=list)
    atc_codes: List[str] = field(default_factory=list)  # Anatomical Therapeutic Chemical
    
    # Interactions
    known_interactions: List[DrugInteraction] = field(default_factory=list)


@dataclass
class InteractionReport:
    """Report for drug interaction check."""
    drug_a: str
    drug_b: str
    interactions_found: bool
    interaction_count: int
    interactions: List[DrugInteraction]
    severity_summary: Dict[str, int]  # {"major": 1, "moderate": 2, "minor": 0}
    warnings: List[str]
    recommendations: List[str]


# =============================================================================
# DrugBank Client
# =============================================================================

class DrugBankClient:
    """
    Client for drug information and interaction data.
    
    Uses multiple data sources:
    - RxNav (NIH) for drug interactions
    - OpenFDA for FDA labeling and adverse events
    - Local cache for performance
    
    For full DrugBank API access, set the DRUGBANK_API_KEY environment variable.
    """
    
    # API endpoints
    RXNAV_BASE = "https://rxnav.nlm.nih.gov/REST"
    OPENFDA_BASE = "https://api.fda.gov"
    
    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        cache_ttl: int = 86400 * 7,  # 7 days
        drugbank_api_key: Optional[str] = None
    ):
        """
        Initialize DrugBank client.
        
        Args:
            cache_dir: Directory for caching API responses
            cache_ttl: Cache time-to-live in seconds
            drugbank_api_key: Optional DrugBank API key for licensed access
        """
        self.cache_dir = cache_dir or Path.home() / ".chemagent" / "drugbank_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_ttl = cache_ttl
        self.drugbank_api_key = drugbank_api_key
        
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "User-Agent": "ChemAgent/1.0"
        })
        
        # Rate limiting
        self._last_request_time = 0
        self._min_request_interval = 0.1  # 10 requests/second max
    
    # =========================================================================
    # Cache Management
    # =========================================================================
    
    def _get_cache_key(self, endpoint: str, params: dict) -> str:
        """Generate cache key from endpoint and parameters."""
        param_str = json.dumps(params, sort_keys=True)
        key_str = f"{endpoint}:{param_str}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _get_cached(self, cache_key: str) -> Optional[Any]:
        """Retrieve cached response if valid."""
        cache_file = self.cache_dir / f"{cache_key}.json"
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, "r") as f:
                cached = json.load(f)
            
            if time.time() - cached["timestamp"] > self.cache_ttl:
                cache_file.unlink()  # Expired
                return None
            
            return cached["data"]
        except (json.JSONDecodeError, KeyError):
            return None
    
    def _set_cached(self, cache_key: str, data: Any) -> None:
        """Cache response data."""
        cache_file = self.cache_dir / f"{cache_key}.json"
        with open(cache_file, "w") as f:
            json.dump({
                "timestamp": time.time(),
                "data": data
            }, f)
    
    # =========================================================================
    # API Request Helpers
    # =========================================================================
    
    def _rate_limit(self) -> None:
        """Apply rate limiting between requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_request_interval:
            time.sleep(self._min_request_interval - elapsed)
        self._last_request_time = time.time()
    
    def _request(
        self,
        url: str,
        params: Optional[dict] = None,
        use_cache: bool = True
    ) -> Optional[dict]:
        """
        Make API request with caching and rate limiting.
        
        Args:
            url: Full URL for request
            params: Query parameters
            use_cache: Whether to use cache
            
        Returns:
            JSON response or None if failed
        """
        params = params or {}
        cache_key = self._get_cache_key(url, params)
        
        if use_cache:
            cached = self._get_cached(cache_key)
            if cached is not None:
                return cached
        
        self._rate_limit()
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if use_cache:
                self._set_cached(cache_key, data)
            
            return data
        except requests.RequestException as e:
            logger.warning(f"API request failed: {url} - {e}")
            return None
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON response from: {url}")
            return None
    
    # =========================================================================
    # RxNav API Methods (NIH Drug Interaction Database)
    # =========================================================================
    
    def get_rxcui_by_name(self, drug_name: str) -> Optional[str]:
        """
        Get RxNorm Concept Unique Identifier (RXCUI) for a drug name.
        
        Args:
            drug_name: Drug name (generic or brand)
            
        Returns:
            RXCUI string or None
        """
        url = f"{self.RXNAV_BASE}/rxcui.json"
        params = {"name": drug_name, "search": 1}
        
        result = self._request(url, params)
        if not result:
            return None
        
        try:
            id_group = result.get("idGroup", {})
            rxnorm_ids = id_group.get("rxnormId", [])
            return rxnorm_ids[0] if rxnorm_ids else None
        except (KeyError, IndexError):
            return None
    
    def get_drug_interactions_rxnav(
        self,
        drug_name: str
    ) -> List[DrugInteraction]:
        """
        Get drug interactions from RxNav for a single drug.
        
        Args:
            drug_name: Drug name to check
            
        Returns:
            List of known drug interactions
        """
        rxcui = self.get_rxcui_by_name(drug_name)
        if not rxcui:
            logger.warning(f"Could not find RXCUI for: {drug_name}")
            return []
        
        # Use the correct RxNav interaction API endpoint
        url = f"{self.RXNAV_BASE}/interaction/interaction.json"
        params = {"rxcui": rxcui, "sources": "DrugBank"}
        
        result = self._request(url, params)
        if not result:
            return []
        
        interactions = []
        try:
            interaction_groups = result.get("interactionTypeGroup", [])
            for group in interaction_groups:
                for interaction_type in group.get("interactionType", []):
                    for pair in interaction_type.get("interactionPair", []):
                        concepts = pair.get("interactionConcept", [])
                        if len(concepts) >= 2:
                            drug_b_name = concepts[1].get("minConceptItem", {}).get("name", "Unknown")
                            severity_str = pair.get("severity", "N/A").lower()
                            
                            # Map severity
                            if "high" in severity_str or "major" in severity_str:
                                severity = InteractionSeverity.MAJOR
                            elif "moderate" in severity_str:
                                severity = InteractionSeverity.MODERATE
                            elif "low" in severity_str or "minor" in severity_str:
                                severity = InteractionSeverity.MINOR
                            else:
                                severity = InteractionSeverity.UNKNOWN
                            
                            interactions.append(DrugInteraction(
                                drug_a=drug_name,
                                drug_b=drug_b_name,
                                severity=severity,
                                description=pair.get("description", "")
                            ))
        except (KeyError, TypeError) as e:
            logger.warning(f"Error parsing interactions: {e}")
        
        return interactions
    
    def check_drug_pair_interaction(
        self,
        drug_a: str,
        drug_b: str
    ) -> InteractionReport:
        """
        Check for interactions between two specific drugs.
        
        Uses multiple sources:
        1. RxNav interaction API (if available)
        2. OpenFDA label drug_interactions section
        
        Args:
            drug_a: First drug name
            drug_b: Second drug name
            
        Returns:
            InteractionReport with findings
        """
        interactions = []
        warnings = []
        recommendations = []
        severity_summary = {"major": 0, "moderate": 0, "minor": 0, "unknown": 0}
        
        # Method 1: Check FDA labels for both drugs
        for primary, secondary in [(drug_a, drug_b), (drug_b, drug_a)]:
            interaction = self.check_interaction_from_fda(primary, secondary)
            if interaction:
                # Avoid duplicates
                if not any(
                    i.drug_a == interaction.drug_a and i.drug_b == interaction.drug_b
                    for i in interactions
                ):
                    interactions.append(interaction)
                    severity_summary[interaction.severity.value] += 1
        
        # Generate warnings and recommendations
        if severity_summary["major"] > 0:
            warnings.append(f"MAJOR interaction detected between {drug_a} and {drug_b}")
            recommendations.append("Consult healthcare provider before co-administration")
            recommendations.append("Avoid combination if possible")
        elif severity_summary["moderate"] > 0:
            warnings.append(f"Moderate interaction detected between {drug_a} and {drug_b}")
            recommendations.append("Monitor for potential adverse effects")
            recommendations.append("Adjust dosing if needed")
        elif len(interactions) > 0:
            warnings.append(f"Potential interaction between {drug_a} and {drug_b}")
            recommendations.append("Review FDA labels for specific guidance")
        
        return InteractionReport(
            drug_a=drug_a,
            drug_b=drug_b,
            interactions_found=len(interactions) > 0,
            interaction_count=len(interactions),
            interactions=interactions,
            severity_summary=severity_summary,
            warnings=warnings,
            recommendations=recommendations
        )
    
    # =========================================================================
    # OpenFDA Methods
    # =========================================================================
    
    def get_fda_label_info(self, drug_name: str) -> Optional[Dict[str, Any]]:
        """
        Get FDA drug label information from OpenFDA.
        
        Args:
            drug_name: Drug name to search
            
        Returns:
            Dictionary with label information or None
        """
        url = f"{self.OPENFDA_BASE}/drug/label.json"
        params = {
            "search": f'openfda.brand_name:"{drug_name}" OR openfda.generic_name:"{drug_name}"',
            "limit": 1
        }
        
        result = self._request(url, params)
        if not result or "results" not in result:
            return None
        
        try:
            label = result["results"][0]
            return {
                "brand_name": label.get("openfda", {}).get("brand_name", []),
                "generic_name": label.get("openfda", {}).get("generic_name", []),
                "manufacturer": label.get("openfda", {}).get("manufacturer_name", []),
                "indications": label.get("indications_and_usage", []),
                "warnings": label.get("warnings", []),
                "contraindications": label.get("contraindications", []),
                "drug_interactions": label.get("drug_interactions", []),
                "adverse_reactions": label.get("adverse_reactions", []),
                "dosage": label.get("dosage_and_administration", []),
                "description": label.get("description", []),
            }
        except (KeyError, IndexError):
            return None
    
    def get_fda_drug_interactions(self, drug_name: str) -> List[str]:
        """
        Extract drug interaction information from FDA label.
        
        Args:
            drug_name: Drug name to search
            
        Returns:
            List of interaction descriptions from FDA label
        """
        label_info = self.get_fda_label_info(drug_name)
        if not label_info:
            return []
        
        interactions = label_info.get("drug_interactions", [])
        if interactions and isinstance(interactions[0], str):
            return interactions[:3]  # Return first 3 interaction sections
        return []
    
    def check_interaction_from_fda(
        self,
        drug_a: str,
        drug_b: str
    ) -> Optional[DrugInteraction]:
        """
        Check if drug_b is mentioned in drug_a's FDA interaction section.
        
        Args:
            drug_a: Primary drug
            drug_b: Drug to check interaction with
            
        Returns:
            DrugInteraction if found, None otherwise
        """
        interactions_text = self.get_fda_drug_interactions(drug_a)
        if not interactions_text:
            return None
        
        # Check if drug_b is mentioned
        drug_b_lower = drug_b.lower()
        full_text = " ".join(interactions_text).lower()
        
        if drug_b_lower in full_text:
            # Extract the relevant sentence/section
            description = f"FDA label for {drug_a} mentions interaction with {drug_b}. "
            
            # Simple severity heuristic based on keywords
            severity = InteractionSeverity.UNKNOWN
            if any(w in full_text for w in ["fatal", "death", "contraindicated", "avoid"]):
                severity = InteractionSeverity.MAJOR
            elif any(w in full_text for w in ["caution", "monitor", "adjust"]):
                severity = InteractionSeverity.MODERATE
            elif any(w in full_text for w in ["minor", "unlikely"]):
                severity = InteractionSeverity.MINOR
            else:
                severity = InteractionSeverity.MODERATE  # Default to moderate
            
            return DrugInteraction(
                drug_a=drug_a,
                drug_b=drug_b,
                severity=severity,
                description=description + "Consult full FDA label for details."
            )
        
        return None
    
    def get_adverse_events(
        self,
        drug_name: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get adverse event reports from OpenFDA.
        
        Args:
            drug_name: Drug name to search
            limit: Maximum number of events
            
        Returns:
            List of adverse event summaries
        """
        url = f"{self.OPENFDA_BASE}/drug/event.json"
        params = {
            "search": f'patient.drug.openfda.brand_name:"{drug_name}" OR patient.drug.openfda.generic_name:"{drug_name}"',
            "limit": limit
        }
        
        result = self._request(url, params)
        if not result or "results" not in result:
            return []
        
        events = []
        for event in result.get("results", []):
            patient = event.get("patient", {})
            reactions = [r.get("reactionmeddrapt", "") for r in patient.get("reaction", [])]
            
            events.append({
                "receive_date": event.get("receivedate"),
                "serious": event.get("serious"),
                "reactions": reactions[:5],  # Top 5 reactions
                "outcome": patient.get("patientdeathdate") is not None
            })
        
        return events
    
    # =========================================================================
    # High-Level Methods
    # =========================================================================
    
    def get_drug_info(self, drug_name: str) -> DrugInfo:
        """
        Get comprehensive drug information from multiple sources.
        
        Args:
            drug_name: Drug name (generic or brand)
            
        Returns:
            DrugInfo object with available information
        """
        info = DrugInfo(name=drug_name)
        
        # Get RXCUI
        rxcui = self.get_rxcui_by_name(drug_name)
        if rxcui:
            info.rxcui = rxcui
        
        # Get FDA label info
        fda_info = self.get_fda_label_info(drug_name)
        if fda_info:
            if fda_info.get("generic_name"):
                info.generic_name = fda_info["generic_name"][0]
            if fda_info.get("brand_name"):
                info.brand_names = fda_info["brand_name"]
            if fda_info.get("indications"):
                info.indication = fda_info["indications"][0][:500]  # Truncate
            if fda_info.get("description"):
                info.description = fda_info["description"][0][:500]
            
            # If we have FDA info, it's likely approved
            info.approval_status = ApprovalStatus.APPROVED
        
        # Get interactions
        interactions = self.get_drug_interactions_rxnav(drug_name)
        info.known_interactions = interactions[:20]  # Limit for memory
        
        return info
    
    def check_interaction_list(
        self,
        drug_list: List[str]
    ) -> List[InteractionReport]:
        """
        Check interactions among a list of drugs.
        
        Args:
            drug_list: List of drug names to check
            
        Returns:
            List of InteractionReports for all pairs
        """
        reports = []
        checked_pairs = set()
        
        for i, drug_a in enumerate(drug_list):
            for drug_b in drug_list[i + 1:]:
                pair_key = tuple(sorted([drug_a.lower(), drug_b.lower()]))
                if pair_key in checked_pairs:
                    continue
                checked_pairs.add(pair_key)
                
                report = self.check_drug_pair_interaction(drug_a, drug_b)
                if report.interactions_found:
                    reports.append(report)
        
        return reports
    
    def get_interaction_summary(
        self,
        drug_list: List[str]
    ) -> Dict[str, Any]:
        """
        Get a summary of all interactions in a drug list.
        
        Args:
            drug_list: List of drug names
            
        Returns:
            Summary dictionary
        """
        reports = self.check_interaction_list(drug_list)
        
        total_interactions = sum(r.interaction_count for r in reports)
        major_count = sum(r.severity_summary["major"] for r in reports)
        moderate_count = sum(r.severity_summary["moderate"] for r in reports)
        
        major_pairs = [
            f"{r.drug_a} + {r.drug_b}"
            for r in reports if r.severity_summary["major"] > 0
        ]
        
        return {
            "drugs_checked": len(drug_list),
            "pairs_checked": len(reports) + len(drug_list) * (len(drug_list) - 1) // 2 - len(reports),
            "interactions_found": total_interactions,
            "severity_breakdown": {
                "major": major_count,
                "moderate": moderate_count,
                "minor": sum(r.severity_summary["minor"] for r in reports),
            },
            "major_interaction_pairs": major_pairs,
            "warnings": [w for r in reports for w in r.warnings],
            "recommendations": list(set(rec for r in reports for rec in r.recommendations)),
        }


# =============================================================================
# Convenience Functions
# =============================================================================

def check_drug_interactions(
    drugs: List[str],
    verbose: bool = False
) -> Dict[str, Any]:
    """
    Check for drug interactions in a list of medications.
    
    Args:
        drugs: List of drug names
        verbose: Whether to include full interaction details
        
    Returns:
        Interaction summary dictionary
    """
    client = DrugBankClient()
    summary = client.get_interaction_summary(drugs)
    
    if verbose:
        reports = client.check_interaction_list(drugs)
        summary["detailed_interactions"] = [
            {
                "drugs": [r.drug_a, r.drug_b],
                "count": r.interaction_count,
                "severity": r.severity_summary,
                "descriptions": [i.description for i in r.interactions]
            }
            for r in reports
        ]
    
    return summary


def get_drug_safety_info(drug_name: str) -> Dict[str, Any]:
    """
    Get safety information for a drug.
    
    Args:
        drug_name: Name of the drug
        
    Returns:
        Safety information dictionary
    """
    client = DrugBankClient()
    
    fda_info = client.get_fda_label_info(drug_name)
    adverse_events = client.get_adverse_events(drug_name, limit=10)
    
    return {
        "drug": drug_name,
        "fda_label": fda_info,
        "adverse_events_sample": adverse_events,
        "warnings": fda_info.get("warnings", []) if fda_info else [],
        "contraindications": fda_info.get("contraindications", []) if fda_info else [],
    }


# =============================================================================
# CLI Entry Point
# =============================================================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python drugbank_client.py <drug_name> [drug_name2 ...]")
        print("\nExamples:")
        print("  python drugbank_client.py aspirin")
        print("  python drugbank_client.py warfarin aspirin ibuprofen")
        sys.exit(1)
    
    drugs = sys.argv[1:]
    
    if len(drugs) == 1:
        # Single drug info
        client = DrugBankClient()
        info = client.get_drug_info(drugs[0])
        print(f"\n{'='*60}")
        print(f"Drug Information: {info.name}")
        print(f"{'='*60}")
        if info.generic_name:
            print(f"Generic Name: {info.generic_name}")
        if info.brand_names:
            print(f"Brand Names: {', '.join(info.brand_names[:3])}")
        if info.rxcui:
            print(f"RXCUI: {info.rxcui}")
        if info.indication:
            print(f"Indication: {info.indication[:200]}...")
        print(f"Approval Status: {info.approval_status.value}")
        print(f"Known Interactions: {len(info.known_interactions)}")
    else:
        # Multiple drugs - check interactions
        summary = check_drug_interactions(drugs, verbose=True)
        print(f"\n{'='*60}")
        print(f"Drug Interaction Check")
        print(f"{'='*60}")
        print(f"Drugs: {', '.join(drugs)}")
        print(f"Total interactions found: {summary['interactions_found']}")
        print(f"\nSeverity breakdown:")
        print(f"  Major: {summary['severity_breakdown']['major']}")
        print(f"  Moderate: {summary['severity_breakdown']['moderate']}")
        print(f"  Minor: {summary['severity_breakdown']['minor']}")
        
        if summary['major_interaction_pairs']:
            print(f"\n⚠️  MAJOR INTERACTIONS:")
            for pair in summary['major_interaction_pairs']:
                print(f"    - {pair}")
        
        if summary['warnings']:
            print(f"\nWarnings:")
            for w in summary['warnings'][:3]:
                print(f"  - {w}")
