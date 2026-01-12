"""
Provenance Tracking for ChemAgent.

Every tool result carries provenance information:
- Source database (ChEMBL, UniProt, Open Targets, etc.)
- Record ID (CHEMBL25, P00533, etc.)
- Direct URL to source
- Query parameters used
- Timestamp and dataset version

This enables:
1. Trust: Users can verify any claim
2. Reproducibility: Re-run the same query later
3. Auditing: Track what data was accessed
4. Citations: Generate proper references
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from enum import Enum
import json
import hashlib


class DataSource(Enum):
    """Supported data sources with their base URLs."""
    CHEMBL = "ChEMBL"
    UNIPROT = "UniProt"
    PUBCHEM = "PubChem"
    OPENTARGETS = "Open Targets"
    BINDINGDB = "BindingDB"
    RDKIT = "RDKit (local)"
    PDB = "Protein Data Bank"
    ALPHAFOLD = "AlphaFold DB"
    UNKNOWN = "Unknown"


@dataclass
class ProvenanceRecord:
    """
    Provenance information for a single data point.
    
    Example:
        record = ProvenanceRecord(
            source=DataSource.CHEMBL,
            record_id="CHEMBL25",
            record_type="compound",
            url="https://www.ebi.ac.uk/chembl/compound_report_card/CHEMBL25/",
            query_params={"query": "aspirin"},
            dataset_version="ChEMBL 34"
        )
    """
    source: DataSource
    record_id: str
    record_type: str  # "compound", "activity", "target", "protein", etc.
    url: Optional[str] = None
    query_params: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    dataset_version: Optional[str] = None
    confidence: Optional[float] = None  # 0-1 score if applicable
    notes: Optional[str] = None
    
    def __post_init__(self):
        """Generate URL if not provided."""
        if self.url is None:
            self.url = self._generate_url()
    
    def _generate_url(self) -> str:
        """Generate source URL based on record type and ID."""
        url_templates = {
            DataSource.CHEMBL: {
                "compound": "https://www.ebi.ac.uk/chembl/compound_report_card/{id}/",
                "target": "https://www.ebi.ac.uk/chembl/target_report_card/{id}/",
                "assay": "https://www.ebi.ac.uk/chembl/assay_report_card/{id}/",
                "activity": "https://www.ebi.ac.uk/chembl/activity/{id}/"
            },
            DataSource.UNIPROT: {
                "protein": "https://www.uniprot.org/uniprotkb/{id}"
            },
            DataSource.PUBCHEM: {
                "compound": "https://pubchem.ncbi.nlm.nih.gov/compound/{id}"
            },
            DataSource.OPENTARGETS: {
                "target": "https://platform.opentargets.org/target/{id}",
                "disease": "https://platform.opentargets.org/disease/{id}",
                "evidence": "https://platform.opentargets.org/evidence/{id}"
            },
            DataSource.BINDINGDB: {
                "binding": "https://www.bindingdb.org/bind/chemsearch/marvin/MolStructure.jsp?monession={id}"
            },
            DataSource.PDB: {
                "structure": "https://www.rcsb.org/structure/{id}"
            },
            DataSource.ALPHAFOLD: {
                "structure": "https://alphafold.ebi.ac.uk/entry/{id}"
            }
        }
        
        templates = url_templates.get(self.source, {})
        template = templates.get(self.record_type, "")
        
        if template:
            return template.format(id=self.record_id)
        return ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "source": self.source.value,
            "record_id": self.record_id,
            "record_type": self.record_type,
            "url": self.url,
            "query_params": self.query_params,
            "timestamp": self.timestamp.isoformat(),
            "dataset_version": self.dataset_version,
            "confidence": self.confidence,
            "notes": self.notes
        }
    
    def to_citation(self) -> str:
        """Generate a citation string."""
        return f"[{self.source.value}: {self.record_id}]({self.url})"


@dataclass
class ProvenanceValue:
    """
    A value with provenance information.
    
    Example:
        ic50 = ProvenanceValue(
            value=45.2,
            unit="nM",
            provenance=ProvenanceRecord(
                source=DataSource.CHEMBL,
                record_id="CHEMBL12345",
                record_type="activity"
            )
        )
    """
    value: Any
    unit: Optional[str] = None
    provenance: Optional[ProvenanceRecord] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "value": self.value,
            "unit": self.unit,
            "provenance": self.provenance.to_dict() if self.provenance else None
        }
    
    def __str__(self) -> str:
        if self.unit:
            return f"{self.value} {self.unit}"
        return str(self.value)
    
    def with_citation(self) -> str:
        """Return value string with inline citation."""
        base = str(self)
        if self.provenance:
            return f"{base} {self.provenance.to_citation()}"
        return base


@dataclass
class EvidenceRecord:
    """
    A single piece of evidence with full provenance.
    
    Used for target-disease associations, activity measurements, etc.
    """
    evidence_type: str  # "literature", "genetic", "expression", "activity"
    description: str
    value: Optional[Any] = None
    unit: Optional[str] = None
    confidence: Optional[float] = None  # 0-1
    provenance: Optional[ProvenanceRecord] = None
    supporting_records: List[ProvenanceRecord] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "evidence_type": self.evidence_type,
            "description": self.description,
            "value": self.value,
            "unit": self.unit,
            "confidence": self.confidence,
            "provenance": self.provenance.to_dict() if self.provenance else None,
            "supporting_records": [r.to_dict() for r in self.supporting_records]
        }


@dataclass
class ProvenanceToolResult:
    """
    A tool result with comprehensive provenance.
    
    Every tool in ChemAgent should return this instead of raw data.
    """
    tool_name: str
    query: str
    success: bool
    data: Any
    provenance_records: List[ProvenanceRecord] = field(default_factory=list)
    evidence: List[EvidenceRecord] = field(default_factory=list)
    execution_time_ms: float = 0.0
    error: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    
    # Metadata
    timestamp: datetime = field(default_factory=datetime.utcnow)
    query_hash: Optional[str] = None
    
    def __post_init__(self):
        """Generate query hash for reproducibility."""
        if self.query_hash is None:
            self.query_hash = hashlib.sha256(
                f"{self.tool_name}:{self.query}".encode()
            ).hexdigest()[:12]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "query": self.query,
            "success": self.success,
            "data": self.data,
            "provenance_records": [r.to_dict() for r in self.provenance_records],
            "evidence": [e.to_dict() for e in self.evidence],
            "execution_time_ms": self.execution_time_ms,
            "error": self.error,
            "warnings": self.warnings,
            "timestamp": self.timestamp.isoformat(),
            "query_hash": self.query_hash
        }
    
    def has_provenance(self) -> bool:
        """Check if result has any provenance records."""
        return len(self.provenance_records) > 0
    
    def get_citations(self) -> List[str]:
        """Get all citations from this result."""
        return [r.to_citation() for r in self.provenance_records]
    
    def get_source_summary(self) -> Dict[str, int]:
        """Get count of records by source."""
        summary = {}
        for record in self.provenance_records:
            source = record.source.value
            summary[source] = summary.get(source, 0) + 1
        return summary


class EvidenceTable:
    """
    Generate evidence tables for responses.
    
    Creates formatted tables showing provenance for all claims.
    """
    
    def __init__(self, title: str = "Evidence"):
        self.title = title
        self.rows: List[Dict[str, Any]] = []
    
    def add_row(
        self,
        claim: str,
        value: Any,
        source: str,
        record_id: str,
        url: str,
        confidence: Optional[float] = None
    ):
        """Add an evidence row."""
        self.rows.append({
            "claim": claim,
            "value": value,
            "source": source,
            "record_id": record_id,
            "url": url,
            "confidence": confidence
        })
    
    def add_from_provenance_value(self, claim: str, pv: ProvenanceValue):
        """Add row from a ProvenanceValue."""
        if pv.provenance:
            self.add_row(
                claim=claim,
                value=str(pv),
                source=pv.provenance.source.value,
                record_id=pv.provenance.record_id,
                url=pv.provenance.url or "",
                confidence=pv.provenance.confidence
            )
    
    def to_markdown(self) -> str:
        """Generate markdown table."""
        if not self.rows:
            return ""
        
        lines = [
            f"### {self.title}",
            "",
            "| Claim | Value | Source | Record ID | Link |",
            "|-------|-------|--------|-----------|------|"
        ]
        
        for row in self.rows:
            link = f"[{row['record_id']}]({row['url']})" if row['url'] else row['record_id']
            lines.append(
                f"| {row['claim']} | {row['value']} | {row['source']} | {link} |"
            )
        
        return "\n".join(lines)
    
    def to_json(self) -> str:
        """Generate JSON for machine consumption."""
        return json.dumps(self.rows, indent=2)


class ProvenanceAggregator:
    """
    Aggregate provenance from multiple tool results.
    
    Used by the response synthesizer to collect all evidence.
    """
    
    def __init__(self):
        self.tool_results: List[ProvenanceToolResult] = []
    
    def add_result(self, result: ProvenanceToolResult):
        """Add a tool result."""
        self.tool_results.append(result)
    
    def get_all_provenance(self) -> List[ProvenanceRecord]:
        """Get all provenance records."""
        records = []
        for result in self.tool_results:
            records.extend(result.provenance_records)
        return records
    
    def get_all_evidence(self) -> List[EvidenceRecord]:
        """Get all evidence records."""
        evidence = []
        for result in self.tool_results:
            evidence.extend(result.evidence)
        return evidence
    
    def generate_evidence_table(self) -> EvidenceTable:
        """Generate evidence table from all results."""
        table = EvidenceTable("Sources & Evidence")
        
        for result in self.tool_results:
            for record in result.provenance_records:
                table.add_row(
                    claim=f"{result.tool_name} result",
                    value=f"{record.record_type}",
                    source=record.source.value,
                    record_id=record.record_id,
                    url=record.url or "",
                    confidence=record.confidence
                )
        
        return table
    
    def has_sufficient_provenance(self, min_records: int = 1) -> bool:
        """Check if we have enough provenance to support claims."""
        return len(self.get_all_provenance()) >= min_records
    
    def get_source_coverage(self) -> Dict[str, List[str]]:
        """Get which sources were used and what records."""
        coverage = {}
        for record in self.get_all_provenance():
            source = record.source.value
            if source not in coverage:
                coverage[source] = []
            coverage[source].append(record.record_id)
        return coverage


# =============================================================================
# Helper Functions for Tools
# =============================================================================

def create_chembl_provenance(
    record_id: str,
    record_type: str = "compound",
    query_params: Dict[str, Any] = None
) -> ProvenanceRecord:
    """Create provenance record for ChEMBL data."""
    return ProvenanceRecord(
        source=DataSource.CHEMBL,
        record_id=record_id,
        record_type=record_type,
        query_params=query_params or {},
        dataset_version="ChEMBL 34"  # Should be configurable
    )


def create_uniprot_provenance(
    accession: str,
    query_params: Dict[str, Any] = None
) -> ProvenanceRecord:
    """Create provenance record for UniProt data."""
    return ProvenanceRecord(
        source=DataSource.UNIPROT,
        record_id=accession,
        record_type="protein",
        query_params=query_params or {}
    )


def create_rdkit_provenance(
    operation: str,
    input_smiles: str
) -> ProvenanceRecord:
    """Create provenance record for RDKit calculations."""
    return ProvenanceRecord(
        source=DataSource.RDKIT,
        record_id=f"rdkit_{operation}",
        record_type="calculation",
        query_params={"smiles": input_smiles, "operation": operation},
        notes="Local calculation using RDKit"
    )


def wrap_with_provenance(
    tool_name: str,
    query: str,
    data: Any,
    provenance_records: List[ProvenanceRecord],
    execution_time_ms: float = 0.0
) -> ProvenanceToolResult:
    """Wrap raw tool output with provenance information."""
    return ProvenanceToolResult(
        tool_name=tool_name,
        query=query,
        success=True,
        data=data,
        provenance_records=provenance_records,
        execution_time_ms=execution_time_ms
    )
