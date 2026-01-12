"""
Verifier Gate for ChemAgent.

Extracts claims from LLM responses and verifies them against tool results.
Rejects responses with unsupported claims to prevent hallucination.

Key Components:
- ClaimExtractor: Extracts numeric and factual claims from text
- ClaimVerifier: Cross-references claims against tool evidence
- VerifierGate: Gatekeeps responses, only passing verified ones
"""

import re
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


# =============================================================================
# Data Classes
# =============================================================================

class ClaimType(Enum):
    """Types of claims that can be extracted."""
    NUMERIC = "numeric"           # "IC50 of 45 nM"
    ENTITY = "entity"             # "Aspirin is a COX inhibitor"
    ASSOCIATION = "association"   # "EGFR is associated with lung cancer"
    PROPERTY = "property"         # "Molecular weight is 180.16 g/mol"
    SOURCE = "source"             # "According to ChEMBL..."


class VerificationStatus(Enum):
    """Status of claim verification."""
    VERIFIED = "verified"         # Claim matches tool data
    UNVERIFIED = "unverified"     # No supporting evidence found
    CONTRADICTED = "contradicted" # Claim contradicts tool data
    UNCERTAIN = "uncertain"       # Partial match or unclear


@dataclass
class Claim:
    """A single claim extracted from response."""
    claim_type: ClaimType
    text: str                     # Original text containing claim
    value: Any                    # Extracted value (number, entity, etc.)
    unit: Optional[str] = None    # Unit if numeric (nM, g/mol, etc.)
    context: str = ""             # Surrounding context
    confidence: float = 1.0       # Extraction confidence


@dataclass
class VerificationResult:
    """Result of verifying a single claim."""
    claim: Claim
    status: VerificationStatus
    evidence: Optional[Dict[str, Any]] = None  # Supporting evidence
    source: Optional[str] = None               # Data source
    message: str = ""
    confidence: float = 0.0      # Verification confidence (0-1)


@dataclass
class VerifierReport:
    """Complete verification report for a response."""
    response: str
    claims_extracted: int
    claims_verified: int
    claims_unverified: int
    claims_contradicted: int
    verification_results: List[VerificationResult]
    overall_confidence: float    # Weighted confidence score
    is_trustworthy: bool         # True if passes verification threshold
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "claims_extracted": self.claims_extracted,
            "claims_verified": self.claims_verified,
            "claims_unverified": self.claims_unverified,
            "claims_contradicted": self.claims_contradicted,
            "overall_confidence": round(self.overall_confidence, 3),
            "is_trustworthy": self.is_trustworthy,
            "verification_details": [
                {
                    "claim_type": vr.claim.claim_type.value,
                    "claim_text": vr.claim.text[:100],
                    "status": vr.status.value,
                    "confidence": round(vr.confidence, 3),
                    "source": vr.source,
                    "message": vr.message
                }
                for vr in self.verification_results
            ]
        }


# =============================================================================
# Claim Extractor
# =============================================================================

class ClaimExtractor:
    """
    Extract verifiable claims from LLM responses.
    
    Focuses on:
    - Numeric claims (values with units)
    - Entity assertions (compound names, targets)
    - Association claims (X is related to Y)
    - Source attributions
    """
    
    # Patterns for numeric values with common units
    NUMERIC_PATTERNS = [
        # IC50, Ki, Kd values
        (r'(?:IC50|IC₅₀|Ki|Kd|EC50)\s*(?:of|is|=|:)?\s*(\d+(?:\.\d+)?)\s*(nM|µM|μM|uM|pM|mM)',
         'bioactivity'),
        # Molecular weight
        (r'(?:molecular weight|MW|mol\.?\s*wt\.?)\s*(?:of|is|=|:)?\s*(\d+(?:\.\d+)?)\s*(?:g/mol|Da|g·mol⁻¹)?',
         'molecular_weight'),
        # LogP
        (r'(?:LogP|log\s*P|logP)\s*(?:of|is|=|:)?\s*(-?\d+(?:\.\d+)?)',
         'logp'),
        # Association scores
        (r'(?:association|evidence)\s*score\s*(?:of|is|=|:)?\s*(\d+(?:\.\d+)?)',
         'association_score'),
        # Percentages
        (r'(\d+(?:\.\d+)?)\s*%',
         'percentage'),
        # Generic numeric with context
        (r'(\d+(?:\.\d+)?)\s*(nM|µM|μM|uM|pM|mM|ng/mL|mg/mL|g/mol|Da|Å|kDa)',
         'generic_numeric'),
    ]
    
    # Patterns for entity claims
    ENTITY_PATTERNS = [
        # Drug/compound identification
        (r'([A-Z][a-z]+(?:inib|mab|zumab|tinib|ciclib)?)\s+is\s+(?:a|an)\s+(\w+(?:\s+\w+)?)',
         'drug_class'),
        # Target associations
        (r'([A-Z][A-Z0-9]+)\s+(?:is\s+)?(?:a\s+)?(?:target|receptor|enzyme|kinase)',
         'target_type'),
        # Disease associations
        (r'(?:associated with|implicated in|linked to)\s+([A-Za-z\s]+(?:cancer|disease|syndrome|disorder))',
         'disease_association'),
    ]
    
    # Known units and their normalization
    UNIT_NORMALIZATION = {
        'µM': 'uM', 'μM': 'uM',
        'g·mol⁻¹': 'g/mol',
        'Da': 'g/mol',
    }
    
    def extract_claims(self, response: str) -> List[Claim]:
        """Extract all verifiable claims from response."""
        claims = []
        
        # Extract numeric claims
        claims.extend(self._extract_numeric_claims(response))
        
        # Extract entity claims
        claims.extend(self._extract_entity_claims(response))
        
        # Extract source attributions
        claims.extend(self._extract_source_claims(response))
        
        return claims
    
    def _extract_numeric_claims(self, text: str) -> List[Claim]:
        """Extract numeric claims with units."""
        claims = []
        
        for pattern, claim_context in self.NUMERIC_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                try:
                    value = float(match.group(1))
                    unit = match.group(2) if len(match.groups()) > 1 else None
                    
                    # Normalize unit
                    if unit and unit in self.UNIT_NORMALIZATION:
                        unit = self.UNIT_NORMALIZATION[unit]
                    
                    # Get context (surrounding text)
                    start = max(0, match.start() - 50)
                    end = min(len(text), match.end() + 50)
                    context = text[start:end]
                    
                    claims.append(Claim(
                        claim_type=ClaimType.NUMERIC,
                        text=match.group(0),
                        value=value,
                        unit=unit,
                        context=context,
                        confidence=0.9  # High confidence for clear patterns
                    ))
                except (ValueError, IndexError):
                    continue
        
        return claims
    
    def _extract_entity_claims(self, text: str) -> List[Claim]:
        """Extract entity-related claims."""
        claims = []
        
        for pattern, claim_context in self.ENTITY_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                try:
                    entity = match.group(1)
                    
                    # Get context
                    start = max(0, match.start() - 30)
                    end = min(len(text), match.end() + 30)
                    context = text[start:end]
                    
                    claims.append(Claim(
                        claim_type=ClaimType.ENTITY,
                        text=match.group(0),
                        value=entity,
                        context=context,
                        confidence=0.8
                    ))
                except IndexError:
                    continue
        
        return claims
    
    def _extract_source_claims(self, text: str) -> List[Claim]:
        """Extract source attribution claims."""
        claims = []
        
        source_patterns = [
            r'(?:according to|from|source[d]?\s*(?:from)?|data from)\s+([A-Za-z]+(?:\s+[A-Za-z]+)?)',
            r'([A-Za-z]+)\s+(?:database|platform|reports?|shows?)',
            r'\(([A-Za-z]+)\s+ID:?\s*\w+\)',
        ]
        
        known_sources = {
            'chembl', 'pubchem', 'uniprot', 'bindingdb', 'open targets',
            'opentargets', 'drugbank', 'kegg', 'pdb', 'alphafold'
        }
        
        for pattern in source_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                source = match.group(1).lower()
                if any(ks in source for ks in known_sources):
                    claims.append(Claim(
                        claim_type=ClaimType.SOURCE,
                        text=match.group(0),
                        value=match.group(1),
                        context=text[max(0, match.start()-20):match.end()+20],
                        confidence=0.95
                    ))
        
        return claims


# =============================================================================
# Claim Verifier
# =============================================================================

class ClaimVerifier:
    """
    Verify claims against tool results.
    
    Cross-references extracted claims with the data returned by tools
    to ensure the LLM response is grounded in evidence.
    """
    
    # Tolerance for numeric comparisons
    NUMERIC_TOLERANCE = 0.05  # 5% tolerance
    
    def __init__(self):
        self.extractor = ClaimExtractor()
    
    def verify_response(
        self,
        response: str,
        tool_results: Dict[str, Any],
        threshold: float = 0.7
    ) -> VerifierReport:
        """
        Verify all claims in a response against tool results.
        
        Args:
            response: The LLM response text
            tool_results: Results from tool execution
            threshold: Minimum confidence for trustworthy response
            
        Returns:
            VerifierReport with verification details
        """
        # Extract claims
        claims = self.extractor.extract_claims(response)
        
        if not claims:
            # No verifiable claims found - consider trustworthy but uncertain
            return VerifierReport(
                response=response,
                claims_extracted=0,
                claims_verified=0,
                claims_unverified=0,
                claims_contradicted=0,
                verification_results=[],
                overall_confidence=0.5,  # Neutral confidence
                is_trustworthy=True
            )
        
        # Extract evidence from tool results
        evidence = self._extract_evidence(tool_results)
        
        # Verify each claim
        verification_results = []
        for claim in claims:
            result = self._verify_claim(claim, evidence)
            verification_results.append(result)
        
        # Calculate statistics
        verified = sum(1 for vr in verification_results 
                      if vr.status == VerificationStatus.VERIFIED)
        unverified = sum(1 for vr in verification_results 
                        if vr.status == VerificationStatus.UNVERIFIED)
        contradicted = sum(1 for vr in verification_results 
                         if vr.status == VerificationStatus.CONTRADICTED)
        
        # Calculate overall confidence with weighted scoring
        # Verified = 1.0, Unverified = 0.5 (neutral), Contradicted = 0.0
        if verification_results:
            weighted_sum = 0.0
            for vr in verification_results:
                if vr.status == VerificationStatus.VERIFIED:
                    weighted_sum += 1.0
                elif vr.status == VerificationStatus.UNVERIFIED:
                    weighted_sum += 0.6  # Slightly positive - claims without evidence aren't necessarily wrong
                elif vr.status == VerificationStatus.UNCERTAIN:
                    weighted_sum += 0.5
                else:  # CONTRADICTED
                    weighted_sum += 0.0
            overall_confidence = weighted_sum / len(verification_results)
        else:
            overall_confidence = 0.5
        
        # Determine trustworthiness
        # Trustworthy if: few contradictions relative to total AND confidence above threshold
        contradiction_ratio = contradicted / len(verification_results) if verification_results else 0
        is_trustworthy = (contradiction_ratio < 0.3) and (overall_confidence >= threshold)
        
        return VerifierReport(
            response=response,
            claims_extracted=len(claims),
            claims_verified=verified,
            claims_unverified=unverified,
            claims_contradicted=contradicted,
            verification_results=verification_results,
            overall_confidence=overall_confidence,
            is_trustworthy=is_trustworthy
        )
    
    def _extract_evidence(self, tool_results: Dict[str, Any]) -> Dict[str, Any]:
        """Extract verifiable evidence from tool results."""
        evidence = {
            'numeric_values': {},     # {context: value}
            'entities': set(),        # Set of entity names
            'sources': set(),         # Set of source names
            'associations': [],       # List of (entity1, entity2, score)
            'raw_data': tool_results  # Keep raw for deep inspection
        }
        
        for tool_name, result in tool_results.items():
            if not isinstance(result, dict):
                continue
            
            data = result.get('data', result)
            
            # Extract from different tool result formats
            self._extract_from_chembl(data, evidence)
            self._extract_from_opentargets(data, evidence)
            self._extract_from_rdkit(data, evidence)
            self._extract_from_compounds(data, evidence)
        
        return evidence
    
    def _extract_from_chembl(self, data: Any, evidence: Dict) -> None:
        """Extract evidence from ChEMBL results."""
        # Handle data being a list directly (from tool result) or dict with 'compounds' key
        compounds = None
        
        if isinstance(data, list) and len(data) > 0:
            # Direct list of CompoundResult objects
            compounds = data
        elif isinstance(data, dict) and 'compounds' in data and data['compounds']:
            # Dict with 'compounds' key
            compounds = data['compounds']
        
        if not compounds:
            # Also check for bioactivity data without compounds
            if isinstance(data, dict) and 'activities' in data:
                self._extract_bioactivities(data, evidence)
            return
            
        # Only use first compound (primary match)
        comp = compounds[0]
        
        # Handle both dataclass and dict for entity extraction
        if hasattr(comp, 'name') and comp.name:
            evidence['entities'].add(comp.name.lower())
        if hasattr(comp, 'chembl_id') and comp.chembl_id:
            evidence['entities'].add(comp.chembl_id.lower())
        
        if isinstance(comp, dict):
            name = comp.get('name') or comp.get('chembl_id')
            if name:
                evidence['entities'].add(name.lower())
        
        # Extract properties from dataclass
        if hasattr(comp, 'molecular_weight') and comp.molecular_weight:
            try:
                evidence['numeric_values']['molecular_weight'] = float(comp.molecular_weight)
            except (TypeError, ValueError):
                pass
                    
        if hasattr(comp, 'alogp') and comp.alogp:
            try:
                evidence['numeric_values']['logp'] = float(comp.alogp)
            except (TypeError, ValueError):
                pass
                    
        if hasattr(comp, 'psa') and comp.psa:
            try:
                evidence['numeric_values']['psa'] = float(comp.psa)
            except (TypeError, ValueError):
                pass
        
        # Also handle dict format
        if isinstance(comp, dict):
            for key in ['molecular_weight', 'alogp', 'logp', 'psa']:
                if key in comp and comp[key]:
                    try:
                        # Normalize key name
                        norm_key = 'logp' if key == 'alogp' else key
                        evidence['numeric_values'][norm_key] = float(comp[key])
                    except (TypeError, ValueError):
                        pass
        
        # Also check for bioactivity data
        if isinstance(data, dict):
            self._extract_bioactivities(data, evidence)
        
        evidence['sources'].add('chembl')
    
    def _extract_bioactivities(self, data: Dict, evidence: Dict) -> None:
        """Extract bioactivity data from ChEMBL results."""
        if 'activities' in data:
            for act in data['activities']:
                if isinstance(act, dict):
                    value = act.get('value') or act.get('standard_value')
                    unit = act.get('unit') or act.get('standard_units')
                    act_type = act.get('type') or act.get('standard_type')
                    if value and act_type:
                        key = f"{act_type.lower()}_{unit}" if unit else act_type.lower()
                        try:
                            evidence['numeric_values'][key] = float(value)
                        except (TypeError, ValueError):
                            pass
    
    def _extract_from_opentargets(self, data: Dict, evidence: Dict) -> None:
        """Extract evidence from Open Targets results."""
        if not isinstance(data, dict):
            return
            
        # Disease associations
        if 'associations' in data:
            for assoc in data['associations']:
                if isinstance(assoc, dict):
                    disease = assoc.get('disease_name', assoc.get('disease', ''))
                    score = assoc.get('score', assoc.get('association_score'))
                    if disease:
                        evidence['entities'].add(disease.lower())
                    if score:
                        try:
                            evidence['numeric_values']['association_score'] = float(score)
                            evidence['associations'].append(('target', disease, score))
                        except (TypeError, ValueError):
                            pass
        
        # Target info
        if 'target' in data:
            target = data['target']
            if isinstance(target, dict):
                name = target.get('name') or target.get('approved_symbol')
                if name:
                    evidence['entities'].add(name.lower())
        
        evidence['sources'].add('open targets')
        evidence['sources'].add('opentargets')
    
    def _extract_from_rdkit(self, data: Dict, evidence: Dict) -> None:
        """Extract evidence from RDKit calculation results."""
        if not isinstance(data, dict):
            return
            
        # Molecular properties
        property_keys = ['molecular_weight', 'logp', 'tpsa', 'hbd', 'hba', 
                        'rotatable_bonds', 'num_atoms', 'num_rings']
        
        for key in property_keys:
            if key in data:
                try:
                    evidence['numeric_values'][key] = float(data[key])
                except (TypeError, ValueError):
                    pass
        
        # Lipinski properties
        if 'lipinski' in data:
            lip = data['lipinski']
            if isinstance(lip, dict):
                for k, v in lip.items():
                    try:
                        evidence['numeric_values'][f'lipinski_{k}'] = float(v)
                    except (TypeError, ValueError):
                        pass
    
    def _extract_from_compounds(self, data: Dict, evidence: Dict) -> None:
        """Extract evidence from compound lookup results."""
        if not isinstance(data, dict):
            return
            
        # Direct properties in result
        for key in ['molecular_weight', 'logp', 'psa', 'hbd', 'hba']:
            if key in data:
                try:
                    evidence['numeric_values'][key] = float(data[key])
                except (TypeError, ValueError):
                    pass
    
    def _verify_claim(
        self, 
        claim: Claim, 
        evidence: Dict[str, Any]
    ) -> VerificationResult:
        """Verify a single claim against evidence."""
        
        if claim.claim_type == ClaimType.NUMERIC:
            return self._verify_numeric_claim(claim, evidence)
        elif claim.claim_type == ClaimType.ENTITY:
            return self._verify_entity_claim(claim, evidence)
        elif claim.claim_type == ClaimType.SOURCE:
            return self._verify_source_claim(claim, evidence)
        else:
            # Unknown claim type - uncertain
            return VerificationResult(
                claim=claim,
                status=VerificationStatus.UNCERTAIN,
                message="Unknown claim type",
                confidence=0.5
            )
    
    def _verify_numeric_claim(
        self, 
        claim: Claim, 
        evidence: Dict[str, Any]
    ) -> VerificationResult:
        """Verify a numeric claim against evidence."""
        claim_value = claim.value
        
        # Look for matching numeric values in evidence
        for key, ev_value in evidence['numeric_values'].items():
            # Check if claim context matches evidence key
            context_lower = claim.context.lower()
            key_words = key.replace('_', ' ').split()
            
            context_match = any(word in context_lower for word in key_words)
            
            if context_match:
                # Check if values match within tolerance
                if ev_value == 0:
                    value_match = claim_value == 0
                else:
                    relative_diff = abs(claim_value - ev_value) / abs(ev_value)
                    value_match = relative_diff <= self.NUMERIC_TOLERANCE
                
                if value_match:
                    return VerificationResult(
                        claim=claim,
                        status=VerificationStatus.VERIFIED,
                        evidence={'key': key, 'value': ev_value},
                        message=f"Matches {key}: {ev_value}",
                        confidence=0.95
                    )
                else:
                    return VerificationResult(
                        claim=claim,
                        status=VerificationStatus.CONTRADICTED,
                        evidence={'key': key, 'value': ev_value},
                        message=f"Contradicts {key}: expected {ev_value}, got {claim_value}",
                        confidence=0.1
                    )
        
        # No matching evidence found
        return VerificationResult(
            claim=claim,
            status=VerificationStatus.UNVERIFIED,
            message="No supporting evidence found for numeric claim",
            confidence=0.3
        )
    
    def _verify_entity_claim(
        self, 
        claim: Claim, 
        evidence: Dict[str, Any]
    ) -> VerificationResult:
        """Verify an entity claim against evidence."""
        entity = str(claim.value).lower()
        
        # Check if entity appears in evidence
        if entity in evidence['entities']:
            return VerificationResult(
                claim=claim,
                status=VerificationStatus.VERIFIED,
                message=f"Entity '{claim.value}' found in tool results",
                confidence=0.9
            )
        
        # Partial match check
        for ev_entity in evidence['entities']:
            if entity in ev_entity or ev_entity in entity:
                return VerificationResult(
                    claim=claim,
                    status=VerificationStatus.VERIFIED,
                    evidence={'matched_entity': ev_entity},
                    message=f"Entity '{claim.value}' partially matches '{ev_entity}'",
                    confidence=0.7
                )
        
        return VerificationResult(
            claim=claim,
            status=VerificationStatus.UNVERIFIED,
            message=f"Entity '{claim.value}' not found in tool results",
            confidence=0.4
        )
    
    def _verify_source_claim(
        self, 
        claim: Claim, 
        evidence: Dict[str, Any]
    ) -> VerificationResult:
        """Verify a source attribution claim."""
        source = str(claim.value).lower()
        
        # Check if claimed source was actually used
        if source in evidence['sources'] or any(source in s for s in evidence['sources']):
            return VerificationResult(
                claim=claim,
                status=VerificationStatus.VERIFIED,
                message=f"Source '{claim.value}' confirmed",
                confidence=0.95
            )
        
        return VerificationResult(
            claim=claim,
            status=VerificationStatus.UNVERIFIED,
            message=f"Source '{claim.value}' not found in tool results",
            confidence=0.3
        )


# =============================================================================
# Verifier Gate
# =============================================================================

class VerifierGate:
    """
    Gatekeeping layer that ensures responses are grounded in evidence.
    
    Can either:
    1. Reject unverified responses entirely
    2. Annotate responses with verification status
    3. Flag potential hallucinations for review
    """
    
    def __init__(
        self,
        mode: str = "annotate",  # "reject", "annotate", or "flag"
        confidence_threshold: float = 0.7,
        allow_no_claims: bool = True
    ):
        """
        Initialize the verifier gate.
        
        Args:
            mode: How to handle unverified responses
                - "reject": Return error for untrustworthy responses
                - "annotate": Add verification info to response
                - "flag": Allow but flag potential issues
            confidence_threshold: Minimum confidence for trustworthy
            allow_no_claims: Whether to allow responses with no verifiable claims
        """
        self.mode = mode
        self.confidence_threshold = confidence_threshold
        self.allow_no_claims = allow_no_claims
        self.verifier = ClaimVerifier()
    
    def _strip_verification_footer(self, response: str) -> str:
        """Remove any existing verification footer to prevent recursive extraction."""
        import re
        # Match footer pattern: ---\n**Verification**: ... to end of string
        pattern = r'\n*---\n\*\*Verification\*\*:.*$'
        return re.sub(pattern, '', response, flags=re.DOTALL)
    
    def process(
        self,
        response: str,
        tool_results: Dict[str, Any]
    ) -> Tuple[str, VerifierReport]:
        """
        Process a response through the verifier gate.
        
        Args:
            response: The LLM response to verify
            tool_results: Tool execution results for verification
            
        Returns:
            Tuple of (processed_response, verification_report)
        """
        # Strip any existing verification footer to avoid recursive extraction
        clean_response = self._strip_verification_footer(response)
        
        # Verify the response
        report = self.verifier.verify_response(
            clean_response, 
            tool_results, 
            self.confidence_threshold
        )
        
        # Handle based on mode
        if self.mode == "reject":
            return self._handle_reject_mode(clean_response, report)
        elif self.mode == "annotate":
            return self._handle_annotate_mode(clean_response, report)
        else:  # flag mode
            return self._handle_flag_mode(response, report)
    
    def _handle_reject_mode(
        self, 
        response: str, 
        report: VerifierReport
    ) -> Tuple[str, VerifierReport]:
        """Reject untrustworthy responses."""
        if not report.is_trustworthy:
            if report.claims_contradicted > 0:
                error_msg = (
                    "⚠️ **Response Rejected**: Contains contradicted claims.\n\n"
                    f"Verification found {report.claims_contradicted} claim(s) that "
                    "contradict the tool results. Please rephrase your question "
                    "or check the raw data."
                )
            else:
                error_msg = (
                    "⚠️ **Response Rejected**: Low confidence.\n\n"
                    f"Verification confidence ({report.overall_confidence:.1%}) "
                    f"is below threshold ({self.confidence_threshold:.1%}). "
                    "The response may contain unverified claims."
                )
            return error_msg, report
        
        return response, report
    
    def _handle_annotate_mode(
        self, 
        response: str, 
        report: VerifierReport
    ) -> Tuple[str, VerifierReport]:
        """Annotate response with verification info."""
        
        # Build verification badge
        if report.is_trustworthy:
            if report.claims_verified > 0:
                badge = f"✅ Verified ({report.claims_verified}/{report.claims_extracted} claims)"
            else:
                badge = "ℹ️ No verifiable claims"
        else:
            if report.claims_contradicted > 0:
                badge = f"⚠️ Contains contradictions ({report.claims_contradicted} claims)"
            else:
                badge = f"⚠️ Low confidence ({report.overall_confidence:.1%})"
        
        # Add verification footer
        footer = f"\n\n---\n**Verification**: {badge}"
        
        if report.claims_unverified > 0:
            footer += f"\n*{report.claims_unverified} claim(s) could not be verified against tool results.*"
        
        return response + footer, report
    
    def _handle_flag_mode(
        self, 
        response: str, 
        report: VerifierReport
    ) -> Tuple[str, VerifierReport]:
        """Flag potential issues but don't modify response."""
        
        if not report.is_trustworthy:
            logger.warning(
                f"Verifier flag: Response has low confidence ({report.overall_confidence:.2f}). "
                f"Claims: {report.claims_extracted} extracted, "
                f"{report.claims_verified} verified, "
                f"{report.claims_contradicted} contradicted."
            )
        
        return response, report
    
    def get_verification_summary(self, report: VerifierReport) -> str:
        """Generate a human-readable verification summary."""
        lines = [
            "## Verification Summary",
            f"- **Claims Extracted**: {report.claims_extracted}",
            f"- **Verified**: {report.claims_verified}",
            f"- **Unverified**: {report.claims_unverified}",
            f"- **Contradicted**: {report.claims_contradicted}",
            f"- **Overall Confidence**: {report.overall_confidence:.1%}",
            f"- **Trustworthy**: {'Yes' if report.is_trustworthy else 'No'}",
        ]
        
        if report.verification_results:
            lines.append("\n### Claim Details")
            for i, vr in enumerate(report.verification_results[:5], 1):
                status_icon = {
                    VerificationStatus.VERIFIED: "✅",
                    VerificationStatus.UNVERIFIED: "❓",
                    VerificationStatus.CONTRADICTED: "❌",
                    VerificationStatus.UNCERTAIN: "🔶"
                }.get(vr.status, "❓")
                
                lines.append(f"{i}. {status_icon} `{vr.claim.text[:50]}...` - {vr.message}")
        
        return "\n".join(lines)


# =============================================================================
# Convenience Functions
# =============================================================================

def verify_response(
    response: str,
    tool_results: Dict[str, Any],
    threshold: float = 0.7
) -> VerifierReport:
    """Quick verification of a response."""
    verifier = ClaimVerifier()
    return verifier.verify_response(response, tool_results, threshold)


def create_verifier_gate(
    mode: str = "annotate",
    threshold: float = 0.7
) -> VerifierGate:
    """Create a configured verifier gate."""
    return VerifierGate(
        mode=mode,
        confidence_threshold=threshold
    )
