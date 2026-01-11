"""
Evidence Verification System
============================

Implements the "verifier gate" from the original architecture:
- Every numeric claim must carry provenance
- System refuses to answer if it can't attach evidence records
- Tracks source credibility and recency

This module ensures ChemAgent provides evidence-grounded answers
where every claim can be traced back to its source.

Example:
    >>> from chemagent.core.evidence import EvidenceVerifier, Evidence
    >>> verifier = EvidenceVerifier()
    >>> 
    >>> # Verify a claim
    >>> evidence = Evidence(
    ...     claim="Aspirin has IC50 of 280 nM",
    ...     value=280,
    ...     unit="nM",
    ...     source="ChEMBL",
    ...     source_id="CHEMBL25",
    ...     assay_id="CHEMBL1234567"
    ... )
    >>> result = verifier.verify(evidence)
    >>> print(result.is_valid, result.confidence)
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================

class SourceCredibility(Enum):
    """Source credibility levels."""
    HIGH = "high"          # Curated databases (ChEMBL, UniProt)
    MEDIUM = "medium"      # Aggregated databases (PubChem, BindingDB)
    LOW = "low"            # Predicted/computed values
    UNKNOWN = "unknown"    # Unverified source


class EvidenceType(Enum):
    """Types of evidence."""
    EXPERIMENTAL = "experimental"      # Lab measurement
    COMPUTATIONAL = "computational"    # Computed/predicted
    CURATED = "curated"               # Expert-curated
    AGGREGATED = "aggregated"         # Aggregated from multiple sources
    LITERATURE = "literature"         # From publications


class ClaimType(Enum):
    """Types of claims that require evidence."""
    ACTIVITY = "activity"             # IC50, Ki, EC50, etc.
    PROPERTY = "property"             # MW, LogP, TPSA, etc.
    STRUCTURE = "structure"           # SMILES, InChI
    ASSOCIATION = "association"       # Target-disease, drug-target
    IDENTITY = "identity"             # Compound/protein identification


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class Evidence:
    """
    Evidence record supporting a claim.
    
    Every numeric or factual claim in ChemAgent must be backed
    by an Evidence record that can be traced to its source.
    """
    claim: str                           # The claim being made
    claim_type: ClaimType = ClaimType.PROPERTY
    
    # Value information
    value: Optional[Any] = None          # The value (number, string, etc.)
    unit: Optional[str] = None           # Unit of measurement
    value_type: str = "exact"            # exact, approximate, range
    
    # Source information
    source: str = ""                     # Database/source name
    source_id: Optional[str] = None      # ID in source (e.g., CHEMBL25)
    source_url: Optional[str] = None     # URL to source record
    source_version: Optional[str] = None # Version/release date
    
    # Assay/method information (for activity data)
    assay_id: Optional[str] = None       # Assay identifier
    assay_type: Optional[str] = None     # Binding, functional, etc.
    target_id: Optional[str] = None      # Target identifier
    
    # Quality indicators
    evidence_type: EvidenceType = EvidenceType.CURATED
    credibility: SourceCredibility = SourceCredibility.UNKNOWN
    confidence: float = 0.0              # 0-1 confidence score
    
    # Timestamps
    measurement_date: Optional[str] = None
    retrieved_date: str = field(default_factory=lambda: datetime.now().isoformat())
    
    # Additional context
    context: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "claim": self.claim,
            "claim_type": self.claim_type.value,
            "value": self.value,
            "unit": self.unit,
            "source": self.source,
            "source_id": self.source_id,
            "source_url": self.source_url,
            "assay_id": self.assay_id,
            "evidence_type": self.evidence_type.value,
            "credibility": self.credibility.value,
            "confidence": self.confidence,
            "retrieved_date": self.retrieved_date
        }


@dataclass
class VerificationResult:
    """Result of evidence verification."""
    is_valid: bool
    confidence: float               # 0-1 confidence
    evidence: Optional[Evidence]
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    @property
    def status(self) -> str:
        """Human-readable status."""
        if self.is_valid:
            if self.confidence >= 0.9:
                return "verified_high"
            elif self.confidence >= 0.7:
                return "verified"
            else:
                return "verified_low"
        else:
            return "unverified"


@dataclass
class EvidenceBlock:
    """
    Machine-readable evidence block for an answer.
    
    This is the "evidence table" that accompanies every answer,
    allowing users to trace claims back to sources.
    """
    query: str
    answer_summary: str
    evidence_items: List[Evidence] = field(default_factory=list)
    verification_status: str = "pending"
    overall_confidence: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def add_evidence(self, evidence: Evidence):
        """Add evidence item."""
        self.evidence_items.append(evidence)
        self._update_confidence()
    
    def _update_confidence(self):
        """Update overall confidence based on evidence."""
        if not self.evidence_items:
            self.overall_confidence = 0.0
            return
        
        # Weight by credibility
        weights = {
            SourceCredibility.HIGH: 1.0,
            SourceCredibility.MEDIUM: 0.7,
            SourceCredibility.LOW: 0.4,
            SourceCredibility.UNKNOWN: 0.2
        }
        
        total_weight = 0
        weighted_conf = 0
        
        for e in self.evidence_items:
            w = weights.get(e.credibility, 0.2)
            weighted_conf += e.confidence * w
            total_weight += w
        
        self.overall_confidence = weighted_conf / total_weight if total_weight > 0 else 0
        
        # Update verification status
        if self.overall_confidence >= 0.8:
            self.verification_status = "verified"
        elif self.overall_confidence >= 0.5:
            self.verification_status = "partial"
        else:
            self.verification_status = "unverified"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "query": self.query,
            "answer_summary": self.answer_summary,
            "verification_status": self.verification_status,
            "overall_confidence": round(self.overall_confidence, 3),
            "evidence_count": len(self.evidence_items),
            "evidence": [e.to_dict() for e in self.evidence_items],
            "timestamp": self.timestamp
        }
    
    def to_markdown(self) -> str:
        """Generate markdown evidence table."""
        lines = [
            "## Evidence Summary",
            "",
            f"**Status**: {self.verification_status.title()}",
            f"**Confidence**: {self.overall_confidence:.0%}",
            f"**Evidence Items**: {len(self.evidence_items)}",
            "",
            "### Sources",
            ""
        ]
        
        for i, e in enumerate(self.evidence_items, 1):
            lines.append(f"{i}. **{e.claim}**")
            lines.append(f"   - Source: {e.source} ({e.credibility.value} credibility)")
            if e.source_id:
                lines.append(f"   - ID: `{e.source_id}`")
            if e.source_url:
                lines.append(f"   - URL: [{e.source_url}]({e.source_url})")
            lines.append("")
        
        return "\n".join(lines)


# =============================================================================
# Source Registry
# =============================================================================

# Source credibility ratings
SOURCE_CREDIBILITY = {
    # High credibility - curated databases
    "ChEMBL": SourceCredibility.HIGH,
    "UniProt": SourceCredibility.HIGH,
    "DrugBank": SourceCredibility.HIGH,
    "RCSB PDB": SourceCredibility.HIGH,
    "Open Targets": SourceCredibility.HIGH,
    
    # Medium credibility - aggregated databases
    "PubChem": SourceCredibility.MEDIUM,
    "BindingDB": SourceCredibility.MEDIUM,
    "AlphaFold": SourceCredibility.MEDIUM,  # Predicted but high quality
    "ZINC": SourceCredibility.MEDIUM,
    
    # Low credibility - computed values
    "RDKit": SourceCredibility.LOW,
    "Computed": SourceCredibility.LOW,
    "Predicted": SourceCredibility.LOW,
    
    # Unknown
    "Unknown": SourceCredibility.UNKNOWN,
    "User": SourceCredibility.UNKNOWN,
}

# Source URLs for linking
SOURCE_URLS = {
    "ChEMBL": "https://www.ebi.ac.uk/chembl/compound_report_card/{id}",
    "UniProt": "https://www.uniprot.org/uniprotkb/{id}",
    "PubChem": "https://pubchem.ncbi.nlm.nih.gov/compound/{id}",
    "BindingDB": "https://www.bindingdb.org/bind/chemsearch/marvin/MolStructure.jsp?monession={id}",
    "RCSB PDB": "https://www.rcsb.org/structure/{id}",
    "Open Targets": "https://platform.opentargets.org/target/{id}",
    "AlphaFold": "https://alphafold.ebi.ac.uk/entry/{id}",
}


# =============================================================================
# Evidence Verifier
# =============================================================================

class EvidenceVerifier:
    """
    Verifies evidence and ensures claims are properly sourced.
    
    This is the "verifier gate" that ensures ChemAgent only
    provides answers that can be traced to credible sources.
    
    Example:
        >>> verifier = EvidenceVerifier()
        >>> 
        >>> # Check if we can make a claim
        >>> evidence = create_evidence_from_chembl_result(result)
        >>> verification = verifier.verify(evidence)
        >>> 
        >>> if not verification.is_valid:
        ...     return "Cannot answer - insufficient evidence"
    """
    
    def __init__(
        self,
        min_confidence: float = 0.5,
        require_source_id: bool = True,
        allow_computed: bool = True
    ):
        """
        Initialize verifier.
        
        Args:
            min_confidence: Minimum confidence to accept evidence
            require_source_id: Require source IDs for verification
            allow_computed: Allow computed/predicted values
        """
        self.min_confidence = min_confidence
        self.require_source_id = require_source_id
        self.allow_computed = allow_computed
    
    def verify(self, evidence: Evidence) -> VerificationResult:
        """
        Verify a single evidence item.
        
        Args:
            evidence: Evidence to verify
            
        Returns:
            VerificationResult with validation status
        """
        issues = []
        warnings = []
        confidence = 1.0
        
        # Check source credibility
        credibility = SOURCE_CREDIBILITY.get(evidence.source, SourceCredibility.UNKNOWN)
        evidence.credibility = credibility
        
        if credibility == SourceCredibility.UNKNOWN:
            issues.append(f"Unknown source: {evidence.source}")
            confidence *= 0.3
        elif credibility == SourceCredibility.LOW:
            if not self.allow_computed:
                issues.append("Computed values not allowed")
            else:
                warnings.append("Value is computed/predicted, not experimental")
                confidence *= 0.6
        
        # Check source ID
        if self.require_source_id and not evidence.source_id:
            issues.append("Missing source identifier")
            confidence *= 0.5
        
        # Check value
        if evidence.value is None and evidence.claim_type != ClaimType.IDENTITY:
            warnings.append("No value provided for claim")
            confidence *= 0.8
        
        # Check for experimental activity data
        if evidence.claim_type == ClaimType.ACTIVITY:
            if not evidence.assay_id:
                warnings.append("Activity claim without assay reference")
                confidence *= 0.7
        
        # Generate source URL if possible
        if evidence.source in SOURCE_URLS and evidence.source_id:
            evidence.source_url = SOURCE_URLS[evidence.source].format(id=evidence.source_id)
        
        # Set evidence confidence
        evidence.confidence = confidence
        
        # Determine validity
        is_valid = len(issues) == 0 and confidence >= self.min_confidence
        
        return VerificationResult(
            is_valid=is_valid,
            confidence=confidence,
            evidence=evidence,
            issues=issues,
            warnings=warnings
        )
    
    def verify_block(self, block: EvidenceBlock) -> Tuple[bool, List[str]]:
        """
        Verify an evidence block.
        
        Args:
            block: Evidence block to verify
            
        Returns:
            Tuple of (is_valid, list of issues)
        """
        all_issues = []
        
        if not block.evidence_items:
            return False, ["No evidence provided"]
        
        for evidence in block.evidence_items:
            result = self.verify(evidence)
            all_issues.extend(result.issues)
        
        block._update_confidence()
        
        is_valid = block.overall_confidence >= self.min_confidence
        return is_valid, all_issues
    
    def can_answer(self, block: EvidenceBlock) -> Tuple[bool, str]:
        """
        Check if we have sufficient evidence to answer.
        
        This is the "verifier gate" - if this returns False,
        the system should refuse to provide an answer.
        
        Args:
            block: Evidence block
            
        Returns:
            Tuple of (can_answer, reason)
        """
        is_valid, issues = self.verify_block(block)
        
        if not is_valid:
            if not block.evidence_items:
                return False, "Cannot answer: no supporting evidence found"
            else:
                return False, f"Cannot answer: insufficient evidence ({', '.join(issues[:2])})"
        
        return True, "Evidence verified"


# =============================================================================
# Evidence Factory
# =============================================================================

class EvidenceFactory:
    """
    Factory for creating evidence records from various sources.
    """
    
    @staticmethod
    def from_chembl(data: Dict[str, Any], claim_type: ClaimType = ClaimType.PROPERTY) -> Evidence:
        """Create evidence from ChEMBL data."""
        return Evidence(
            claim=f"ChEMBL compound {data.get('molecule_chembl_id', 'unknown')}",
            claim_type=claim_type,
            source="ChEMBL",
            source_id=data.get("molecule_chembl_id"),
            evidence_type=EvidenceType.CURATED,
            credibility=SourceCredibility.HIGH,
            confidence=0.95,
            context=data
        )
    
    @staticmethod
    def from_pubchem(data: Dict[str, Any], claim_type: ClaimType = ClaimType.PROPERTY) -> Evidence:
        """Create evidence from PubChem data."""
        return Evidence(
            claim=f"PubChem compound CID {data.get('cid', 'unknown')}",
            claim_type=claim_type,
            source="PubChem",
            source_id=str(data.get("cid")) if data.get("cid") else None,
            evidence_type=EvidenceType.AGGREGATED,
            credibility=SourceCredibility.MEDIUM,
            confidence=0.85,
            context=data
        )
    
    @staticmethod
    def from_uniprot(data: Dict[str, Any]) -> Evidence:
        """Create evidence from UniProt data."""
        return Evidence(
            claim=f"UniProt protein {data.get('accession', 'unknown')}",
            claim_type=ClaimType.IDENTITY,
            source="UniProt",
            source_id=data.get("accession"),
            evidence_type=EvidenceType.CURATED,
            credibility=SourceCredibility.HIGH,
            confidence=0.98,
            context=data
        )
    
    @staticmethod
    def from_rdkit(calculation: str, value: Any, smiles: str) -> Evidence:
        """Create evidence from RDKit calculation."""
        return Evidence(
            claim=f"Computed {calculation} for {smiles[:30]}...",
            claim_type=ClaimType.PROPERTY,
            value=value,
            source="RDKit",
            evidence_type=EvidenceType.COMPUTATIONAL,
            credibility=SourceCredibility.LOW,
            confidence=0.7,
            context={"smiles": smiles, "calculation": calculation}
        )
    
    @staticmethod
    def from_activity(
        value: float,
        unit: str,
        compound_id: str,
        target_id: str,
        assay_id: str,
        source: str = "ChEMBL"
    ) -> Evidence:
        """Create evidence for activity measurement."""
        return Evidence(
            claim=f"{compound_id} activity on {target_id}: {value} {unit}",
            claim_type=ClaimType.ACTIVITY,
            value=value,
            unit=unit,
            source=source,
            source_id=compound_id,
            assay_id=assay_id,
            target_id=target_id,
            evidence_type=EvidenceType.EXPERIMENTAL,
            credibility=SOURCE_CREDIBILITY.get(source, SourceCredibility.UNKNOWN),
            confidence=0.9
        )


# =============================================================================
# Convenience Functions
# =============================================================================

def create_evidence_block(
    query: str,
    answer: str,
    sources: List[Dict[str, Any]]
) -> EvidenceBlock:
    """
    Create an evidence block from query results.
    
    Args:
        query: Original query
        answer: Generated answer
        sources: List of source data dictionaries
        
    Returns:
        EvidenceBlock ready for verification
    """
    block = EvidenceBlock(
        query=query,
        answer_summary=answer[:200]
    )
    
    factory = EvidenceFactory()
    
    for source in sources:
        source_name = source.get("source", "Unknown")
        
        if source_name == "ChEMBL":
            evidence = factory.from_chembl(source)
        elif source_name == "PubChem":
            evidence = factory.from_pubchem(source)
        elif source_name == "UniProt":
            evidence = factory.from_uniprot(source)
        elif source_name == "RDKit":
            evidence = factory.from_rdkit(
                source.get("calculation", "unknown"),
                source.get("value"),
                source.get("smiles", "")
            )
        else:
            evidence = Evidence(
                claim=source.get("claim", "Unknown claim"),
                source=source_name,
                source_id=source.get("id"),
                credibility=SOURCE_CREDIBILITY.get(source_name, SourceCredibility.UNKNOWN)
            )
        
        block.add_evidence(evidence)
    
    return block


def verify_and_format(
    query: str,
    answer: str,
    sources: List[Dict[str, Any]],
    min_confidence: float = 0.5
) -> Tuple[str, EvidenceBlock]:
    """
    Verify evidence and format answer with evidence block.
    
    Args:
        query: Original query
        answer: Generated answer
        sources: Source data
        min_confidence: Minimum confidence threshold
        
    Returns:
        Tuple of (formatted_answer, evidence_block)
    """
    block = create_evidence_block(query, answer, sources)
    verifier = EvidenceVerifier(min_confidence=min_confidence)
    
    can_answer, reason = verifier.can_answer(block)
    
    if not can_answer:
        formatted = f"⚠️ {reason}\n\nPartial information available:\n{answer}"
    else:
        formatted = f"{answer}\n\n{block.to_markdown()}"
    
    return formatted, block


if __name__ == "__main__":
    # Quick test
    print("Testing Evidence Verification System...")
    
    # Create test evidence
    evidence = Evidence(
        claim="Aspirin (CHEMBL25) IC50 = 280 nM against COX-2",
        claim_type=ClaimType.ACTIVITY,
        value=280,
        unit="nM",
        source="ChEMBL",
        source_id="CHEMBL25",
        assay_id="CHEMBL1234567",
        target_id="P35354"
    )
    
    # Verify
    verifier = EvidenceVerifier()
    result = verifier.verify(evidence)
    
    print(f"\n1. Single evidence verification:")
    print(f"   Valid: {result.is_valid}")
    print(f"   Confidence: {result.confidence:.2f}")
    print(f"   Status: {result.status}")
    print(f"   Issues: {result.issues}")
    print(f"   Warnings: {result.warnings}")
    
    # Create evidence block
    print(f"\n2. Evidence block:")
    block = EvidenceBlock(
        query="What is the IC50 of aspirin against COX-2?",
        answer_summary="Aspirin has IC50 of 280 nM"
    )
    block.add_evidence(evidence)
    
    # Add computed evidence
    computed = EvidenceFactory.from_rdkit("molecular_weight", 180.16, "CC(=O)Oc1ccccc1C(=O)O")
    block.add_evidence(computed)
    
    print(f"   Status: {block.verification_status}")
    print(f"   Overall confidence: {block.overall_confidence:.2f}")
    print(f"   Evidence count: {len(block.evidence_items)}")
    
    # Test verifier gate
    print(f"\n3. Verifier gate:")
    can_answer, reason = verifier.can_answer(block)
    print(f"   Can answer: {can_answer}")
    print(f"   Reason: {reason}")
    
    # Print markdown
    print(f"\n4. Evidence markdown:")
    print(block.to_markdown())
    
    print("\n✓ All tests passed!")
