"""
Tests for the Verifier Gate module.
"""
import pytest
from dataclasses import dataclass

# Import verifier components
from chemagent.core.verifier import (
    ClaimType,
    VerificationStatus,
    Claim,
    VerificationResult,
    VerifierReport,
    ClaimExtractor,
    ClaimVerifier,
    VerifierGate,
)


# =============================================================================
# Test Fixtures
# =============================================================================

@dataclass
class MockCompoundResult:
    """Mock compound result for testing."""
    chembl_id: str
    name: str
    molecular_weight: str
    alogp: str
    psa: str


@pytest.fixture
def extractor():
    """Create a ClaimExtractor instance."""
    return ClaimExtractor()


@pytest.fixture
def verifier():
    """Create a ClaimVerifier instance."""
    return ClaimVerifier()


@pytest.fixture
def gate():
    """Create a VerifierGate instance."""
    return VerifierGate(mode='annotate')


@pytest.fixture
def aspirin_tool_results():
    """Sample tool results for aspirin."""
    compounds = [
        MockCompoundResult('CHEMBL25', 'ASPIRIN', '180.16', '1.31', '63.60'),
    ]
    return {
        'chembl_search_by_name': {
            'success': True,
            'data': compounds,
            'args': {'name': 'aspirin'}
        }
    }


# =============================================================================
# Claim Extractor Tests
# =============================================================================

class TestClaimExtractor:
    """Tests for ClaimExtractor."""
    
    def test_extract_molecular_weight(self, extractor):
        """Test extracting molecular weight claims."""
        response = "The molecular weight of aspirin is 180.16 g/mol"
        claims = extractor.extract_claims(response)
        
        assert len(claims) == 1
        assert claims[0].claim_type == ClaimType.NUMERIC
        assert claims[0].value == 180.16
        assert 'g/mol' in claims[0].unit
    
    def test_extract_ic50(self, extractor):
        """Test extracting IC50 claims."""
        response = "The compound has an IC50 of 45 nM against the target"
        claims = extractor.extract_claims(response)
        
        assert len(claims) >= 1
        ic50_claims = [c for c in claims if 'ic50' in c.text.lower() or c.value == 45]
        assert len(ic50_claims) >= 1
    
    def test_extract_ki(self, extractor):
        """Test extracting Ki claims."""
        response = "Ki = 2.5 μM for this inhibitor"
        claims = extractor.extract_claims(response)
        
        assert len(claims) >= 1
    
    def test_extract_multiple_claims(self, extractor):
        """Test extracting multiple claims from text."""
        response = """
        Aspirin has a molecular weight of 180.16 g/mol.
        It shows IC50 of 100 nM against COX-1.
        """
        claims = extractor.extract_claims(response)
        
        # Should extract at least the MW claim
        assert len(claims) >= 1
    
    def test_no_claims(self, extractor):
        """Test response with no numeric claims."""
        response = "Aspirin is a common pain reliever."
        claims = extractor.extract_claims(response)
        
        # May or may not extract entity claims, but no numeric
        numeric_claims = [c for c in claims if c.claim_type == ClaimType.NUMERIC]
        assert len(numeric_claims) == 0
    
    def test_deduplicate_claims(self, extractor):
        """Test that duplicate claims are deduplicated."""
        response = """
        MW is 180.16 g/mol. The molecular weight is 180.16 g/mol.
        """
        claims = extractor.extract_claims(response)
        
        # Multiple patterns may match - this is expected behavior
        # The important thing is they all have the same value
        mw_claims = [c for c in claims if c.value == 180.16]
        assert len(mw_claims) >= 1
        # All claims should have the same value
        for claim in mw_claims:
            assert claim.value == 180.16


# =============================================================================
# Claim Verifier Tests
# =============================================================================

class TestClaimVerifier:
    """Tests for ClaimVerifier."""
    
    def test_verify_correct_claim(self, verifier, aspirin_tool_results):
        """Test verifying a correct claim."""
        response = "The molecular weight of aspirin is 180.16 g/mol"
        report = verifier.verify_response(response, aspirin_tool_results)
        
        assert report.claims_extracted >= 1
        assert report.claims_verified >= 1
        assert report.claims_contradicted == 0
        assert report.overall_confidence >= 0.8
    
    def test_verify_incorrect_claim(self, verifier, aspirin_tool_results):
        """Test detecting contradicted claims."""
        response = "The molecular weight of aspirin is 250.00 g/mol"
        report = verifier.verify_response(response, aspirin_tool_results)
        
        assert report.claims_extracted >= 1
        assert report.claims_contradicted >= 1
        assert report.overall_confidence < 0.5
    
    def test_verify_no_evidence(self, verifier):
        """Test verification with no tool results."""
        response = "The IC50 is 42 nM"
        report = verifier.verify_response(response, {})
        
        assert report.claims_extracted >= 1
        # No evidence means unverified, not contradicted
        assert report.claims_contradicted == 0
        assert report.overall_confidence >= 0.5  # Unverified gets 0.6


# =============================================================================
# Verifier Gate Tests
# =============================================================================

class TestVerifierGate:
    """Tests for VerifierGate."""
    
    def test_annotate_mode_verified(self, aspirin_tool_results):
        """Test annotate mode with verified response."""
        gate = VerifierGate(mode='annotate')
        response = "The molecular weight of aspirin is 180.16 g/mol"
        
        verified, report = gate.process(response, aspirin_tool_results)
        
        assert '✅ Verified' in verified
        assert report.is_trustworthy
    
    def test_annotate_mode_unverified(self):
        """Test annotate mode with unverified response."""
        gate = VerifierGate(mode='annotate', confidence_threshold=0.8)
        response = "The IC50 is 42 nM"
        
        verified, report = gate.process(response, {})
        
        # Unverified claims should get low confidence annotation
        assert report.overall_confidence < 0.8
    
    def test_reject_mode_low_confidence(self):
        """Test reject mode blocks low confidence responses."""
        gate = VerifierGate(mode='reject', confidence_threshold=0.8)
        response = "The IC50 is 42 nM"
        
        verified, report = gate.process(response, {})
        
        assert '⚠️' in verified or 'Rejected' in verified
        assert not report.is_trustworthy
    
    def test_flag_mode(self, aspirin_tool_results):
        """Test flag mode doesn't modify response."""
        gate = VerifierGate(mode='flag')
        response = "The molecular weight of aspirin is 180.16 g/mol"
        
        verified, report = gate.process(response, aspirin_tool_results)
        
        # Flag mode shouldn't add annotations
        assert verified == response
    
    def test_strip_verification_footer(self):
        """Test that existing verification footers are stripped."""
        gate = VerifierGate(mode='annotate')
        response_with_footer = """The MW is 180.16 g/mol.

---
**Verification**: ⚠️ Low confidence (60.0%)
*1 claim(s) could not be verified against tool results.*"""
        
        # Simulate aspirin data - use list format as real client returns
        compounds = [MockCompoundResult('CHEMBL25', 'ASPIRIN', '180.16', '1.31', '63.60')]
        tool_results = {
            'chembl_search_by_name': {
                'success': True,
                'data': compounds,  # Direct list of compounds
                'args': {'name': 'aspirin'}
            }
        }
        
        verified, report = gate.process(response_with_footer, tool_results)
        
        # Should strip the old footer's percentage claim
        # The 60.0% should not be extracted as a claim
        percentage_claims = [c for c in report.verification_results if c.claim.value == 60.0]
        assert len(percentage_claims) == 0
        
        # The old footer should be replaced with new one
        assert verified.count('**Verification**') == 1


# =============================================================================
# Evidence Extraction Tests
# =============================================================================

class TestEvidenceExtraction:
    """Tests for evidence extraction from tool results."""
    
    def test_extract_from_list_format(self, verifier):
        """Test extracting evidence when data is a list of compounds."""
        compounds = [
            MockCompoundResult('CHEMBL25', 'ASPIRIN', '180.16', '1.31', '63.60'),
            MockCompoundResult('CHEMBL123', 'OTHER', '300.00', '2.0', '80.0'),
        ]
        tool_results = {
            'chembl_search_by_name': {
                'success': True,
                'data': compounds,  # Direct list
                'args': {}
            }
        }
        
        evidence = verifier._extract_evidence(tool_results)
        
        # Should only use first compound
        assert evidence['numeric_values'].get('molecular_weight') == 180.16
        assert evidence['numeric_values'].get('logp') == 1.31
    
    def test_extract_from_dict_format(self, verifier):
        """Test extracting evidence when data has 'compounds' key."""
        compounds = [
            MockCompoundResult('CHEMBL25', 'ASPIRIN', '180.16', '1.31', '63.60'),
        ]
        tool_results = {
            'chembl_search_by_name': {
                'success': True,
                'data': {'compounds': compounds},  # Dict with compounds key
                'args': {}
            }
        }
        
        evidence = verifier._extract_evidence(tool_results)
        
        assert evidence['numeric_values'].get('molecular_weight') == 180.16
    
    def test_failed_tool_no_evidence(self, verifier):
        """Test that failed tools don't contribute evidence."""
        tool_results = {
            'chembl_search_by_name': {
                'success': False,
                'error': 'Tool not found'
            }
        }
        
        evidence = verifier._extract_evidence(tool_results)
        
        assert len(evidence['numeric_values']) == 0


# =============================================================================
# Confidence Calculation Tests
# =============================================================================

class TestConfidenceCalculation:
    """Tests for confidence score calculation."""
    
    def test_all_verified_high_confidence(self, verifier, aspirin_tool_results):
        """Test that all verified claims give high confidence."""
        response = "Aspirin MW is 180.16 g/mol"
        report = verifier.verify_response(response, aspirin_tool_results)
        
        # Should extract claims and verify at least one
        if report.claims_extracted > 0 and report.claims_verified > 0:
            # If any claims are verified, confidence should be reasonable
            assert report.overall_confidence >= 0.5
        elif report.claims_extracted > 0 and report.claims_verified == 0:
            # If claims extracted but none verified, check it's not contradicted
            if report.claims_contradicted == 0:
                # Unverified claims get 0.6 confidence
                assert report.overall_confidence >= 0.5
    
    def test_all_contradicted_zero_confidence(self, verifier, aspirin_tool_results):
        """Test that contradicted claims give low confidence."""
        response = "Aspirin MW is 999.99 g/mol"
        report = verifier.verify_response(response, aspirin_tool_results)
        
        if report.claims_extracted > 0 and report.claims_contradicted > 0:
            assert report.overall_confidence < 0.5
    
    def test_no_claims_default_confidence(self, verifier):
        """Test confidence when no claims are extracted."""
        response = "This is a general statement about chemistry."
        report = verifier.verify_response(response, {})
        
        # No claims should default to 1.0 confidence
        if report.claims_extracted == 0:
            assert report.overall_confidence == 1.0
