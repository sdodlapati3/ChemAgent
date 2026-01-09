"""
Tests for intent parser.

Validates 50+ chemistry query patterns with entity extraction.
"""

import pytest

from chemagent.core import IntentParser, IntentType, ParsedIntent


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def parser():
    """Create intent parser."""
    return IntentParser()


# =============================================================================
# Test Similarity Search (10 patterns)
# =============================================================================

class TestSimilaritySearch:
    """Test similarity search intent recognition."""
    
    def test_similarity_to_compound(self, parser):
        """Test 'similar to compound'."""
        queries = [
            "Find similar compounds to aspirin",
            "Show me molecules similar to ibuprofen",
            "Get analogs of caffeine",
            "Similar structures to morphine",
        ]
        
        for query in queries:
            result = parser.parse(query)
            assert result.intent_type == IntentType.SIMILARITY_SEARCH
            assert "compound" in result.entities
    
    def test_similarity_to_smiles(self, parser):
        """Test similarity with SMILES."""
        result = parser.parse("Find analogs to CC(=O)Oc1ccccc1C(=O)O")
        assert result.intent_type == IntentType.SIMILARITY_SEARCH
        assert "smiles" in result.entities
        assert result.entities["smiles"] == "CC(=O)Oc1ccccc1C(=O)O"
    
    def test_similarity_to_chembl(self, parser):
        """Test similarity with ChEMBL ID."""
        result = parser.parse("similar structures to CHEMBL25")
        assert result.intent_type == IntentType.SIMILARITY_SEARCH
        assert result.entities.get("chembl_id") == "CHEMBL25"
    
    def test_similarity_with_threshold(self, parser):
        """Test threshold extraction."""
        queries_and_thresholds = [
            ("Find compounds with similarity > 0.7", 0.7),
            ("Search Tanimoto above 0.85", 0.85),
            ("Similarity greater than 0.6", 0.6),
        ]
        
        for query, expected_threshold in queries_and_thresholds:
            result = parser.parse(query)
            assert result.intent_type == IntentType.SIMILARITY_SEARCH
            assert result.entities.get("threshold") == expected_threshold
    
    def test_structural_analogs(self, parser):
        """Test structural analog queries."""
        result = parser.parse("structural analogs")
        assert result.intent_type == IntentType.SIMILARITY_SEARCH
    
    def test_fingerprint_match(self, parser):
        """Test fingerprint matching."""
        result = parser.parse("fingerprint search for CC(C)O")
        assert result.intent_type == IntentType.SIMILARITY_SEARCH
    
    def test_nearest_neighbors(self, parser):
        """Test nearest neighbors."""
        result = parser.parse("find nearest neighbors to aspirin")
        assert result.intent_type == IntentType.SIMILARITY_SEARCH
        assert result.entities.get("compound") == "aspirin"


# =============================================================================
# Test Substructure Search (8 patterns)
# =============================================================================

class TestSubstructureSearch:
    """Test substructure search intent recognition."""
    
    def test_substructure_query(self, parser):
        """Test basic substructure search."""
        result = parser.parse("Find compounds containing benzene")
        assert result.intent_type == IntentType.SUBSTRUCTURE_SEARCH
        assert result.entities.get("functional_group") == "c1ccccc1"
    
    def test_functional_groups(self, parser):
        """Test functional group recognition."""
        groups = [
            ("molecules with carbonyl", "C=O"),
            ("compounds containing hydroxyl", "O"),
            ("structures having amine", "N"),
            ("molecules with amide group", "C(=O)N"),
        ]
        
        for query, expected_smarts in groups:
            result = parser.parse(query)
            assert result.intent_type == IntentType.SUBSTRUCTURE_SEARCH
            assert result.entities.get("functional_group") == expected_smarts
    
    def test_smarts_pattern(self, parser):
        """Test SMARTS pattern matching."""
        result = parser.parse("match smarts pattern [#6]")
        assert result.intent_type == IntentType.SUBSTRUCTURE_SEARCH
    
    def test_ring_search(self, parser):
        """Test ring-based search."""
        result = parser.parse("molecules having aromatic ring")
        assert result.intent_type == IntentType.SUBSTRUCTURE_SEARCH
    
    def test_scaffold_analysis(self, parser):
        """Test scaffold extraction."""
        result = parser.parse("murcko scaffold of CC(=O)O")
        assert result.intent_type == IntentType.SCAFFOLD_ANALYSIS


# =============================================================================
# Test Compound Lookup (8 patterns)
# =============================================================================

class TestCompoundLookup:
    """Test compound lookup intent recognition."""
    
    def test_chembl_lookup(self, parser):
        """Test ChEMBL ID lookup."""
        queries = [
            "What is CHEMBL25",
            "Tell me about compound CHEMBL25",
            "Show me CHEMBL25",
            "Get CHEMBL25 info",
        ]
        
        for query in queries:
            result = parser.parse(query)
            assert result.intent_type == IntentType.COMPOUND_LOOKUP
            assert result.entities.get("chembl_id") == "CHEMBL25"
    
    def test_compound_name_lookup(self, parser):
        """Test lookup by compound name."""
        result = parser.parse("structure of aspirin")
        assert result.intent_type == IntentType.COMPOUND_LOOKUP
        assert result.entities.get("compound") == "aspirin"
    
    def test_drug_name_lookup(self, parser):
        """Test common drug names."""
        drugs = ["aspirin", "ibuprofen", "caffeine", "morphine"]
        
        for drug in drugs:
            result = parser.parse(f"What's the structure of {drug}")
            assert result.intent_type == IntentType.COMPOUND_LOOKUP
            assert result.entities.get("compound") == drug
    
    def test_compound_details(self, parser):
        """Test details request."""
        result = parser.parse("details for aspirin")
        assert result.intent_type == IntentType.COMPOUND_LOOKUP


# =============================================================================
# Test Target Lookup (5 patterns)
# =============================================================================

class TestTargetLookup:
    """Test target/protein lookup intent recognition."""
    
    def test_target_info(self, parser):
        """Test target information queries."""
        result = parser.parse("target information for COX-2")
        assert result.intent_type == IntentType.TARGET_LOOKUP
        assert result.entities.get("target") == "COX-2"
    
    def test_protein_lookup(self, parser):
        """Test protein queries."""
        result = parser.parse("what is EGFR")
        assert result.intent_type == IntentType.TARGET_LOOKUP
        assert result.entities.get("target") == "EGFR"
    
    def test_uniprot_id(self, parser):
        """Test UniProt ID extraction."""
        result = parser.parse("protein P35354")
        assert result.intent_type == IntentType.TARGET_LOOKUP
        assert result.entities.get("uniprot_id") == "P35354"


# =============================================================================
# Test Property Calculation (9 patterns)
# =============================================================================

class TestPropertyCalculation:
    """Test property calculation intent recognition."""
    
    def test_property_calculation(self, parser):
        """Test general property calculation."""
        queries = [
            "calculate properties of CC(=O)O",
            "get molecular descriptors for aspirin",
            "compute properties",
        ]
        
        for query in queries:
            result = parser.parse(query)
            assert result.intent_type == IntentType.PROPERTY_CALCULATION
    
    def test_logp_query(self, parser):
        """Test LogP queries."""
        queries = ["logp of aspirin", "clogp", "partition coefficient"]
        
        for query in queries:
            result = parser.parse(query)
            assert result.intent_type == IntentType.PROPERTY_CALCULATION
            assert result.entities.get("property_name") == "logp"
    
    def test_molecular_weight(self, parser):
        """Test molecular weight queries."""
        result = parser.parse("molecular weight of CC(C)O")
        assert result.intent_type == IntentType.PROPERTY_CALCULATION
        assert result.entities.get("property_name") == "mw"
    
    def test_tpsa_query(self, parser):
        """Test TPSA queries."""
        result = parser.parse("what's the polar surface area")
        assert result.intent_type == IntentType.PROPERTY_CALCULATION
        assert result.entities.get("property_name") == "tpsa"
    
    def test_hbond_query(self, parser):
        """Test H-bond queries."""
        result = parser.parse("hydrogen bond donors")
        assert result.intent_type == IntentType.PROPERTY_CALCULATION
        assert result.entities.get("property_name") == "hbd"


# =============================================================================
# Test Property Filter (7 patterns)
# =============================================================================

class TestPropertyFilter:
    """Test property filtering intent recognition."""
    
    def test_mw_filter(self, parser):
        """Test MW filtering."""
        queries_and_constraints = [
            ("filter MW < 500", {"mw_max": 500}),
            ("compounds with molecular weight below 400", {"mw_max": 400}),
            ("molecules MW > 200", {"mw_min": 200}),
        ]
        
        for query, expected_constraints in queries_and_constraints:
            result = parser.parse(query)
            assert result.intent_type == IntentType.PROPERTY_FILTER
            for key, value in expected_constraints.items():
                assert result.constraints.get(key) == value
    
    def test_logp_filter(self, parser):
        """Test LogP filtering."""
        result = parser.parse("logp < 5")
        assert result.intent_type == IntentType.PROPERTY_FILTER
        assert result.constraints.get("logp_max") == 5.0
    
    def test_general_filter(self, parser):
        """Test general filtering."""
        result = parser.parse("filter by property constraints")
        assert result.intent_type == IntentType.PROPERTY_FILTER


# =============================================================================
# Test Lipinski Check (4 patterns)
# =============================================================================

class TestLipinskiCheck:
    """Test Lipinski rule checking intent recognition."""
    
    def test_lipinski_query(self, parser):
        """Test Lipinski queries."""
        queries = [
            "lipinski rule for aspirin",
            "check rule of five",
            "ro5 compliance",
        ]
        
        for query in queries:
            result = parser.parse(query)
            assert result.intent_type == IntentType.LIPINSKI_CHECK
    
    def test_druglike_query(self, parser):
        """Test drug-like queries."""
        queries = ["drug-like properties", "druglike", "druggable"]
        
        for query in queries:
            result = parser.parse(query)
            assert result.intent_type == IntentType.LIPINSKI_CHECK
    
    def test_lipinski_violation(self, parser):
        """Test violation checking."""
        result = parser.parse("does it pass lipinski")
        assert result.intent_type == IntentType.LIPINSKI_CHECK


# =============================================================================
# Test Activity Lookup (6 patterns)
# =============================================================================

class TestActivityLookup:
    """Test activity/bioactivity lookup intent recognition."""
    
    def test_ic50_query(self, parser):
        """Test IC50 queries."""
        result = parser.parse("IC50 for COX-2")
        assert result.intent_type == IntentType.ACTIVITY_LOOKUP
        assert result.entities.get("target") == "COX-2"
        assert result.entities.get("activity_type") == "IC50"
    
    def test_bioactivity_data(self, parser):
        """Test bioactivity queries."""
        result = parser.parse("bioactivity data for CHEMBL25")
        assert result.intent_type == IntentType.ACTIVITY_LOOKUP
    
    def test_inhibition_query(self, parser):
        """Test inhibition queries."""
        result = parser.parse("inhibition of EGFR")
        assert result.intent_type == IntentType.ACTIVITY_LOOKUP
        assert result.entities.get("target") == "EGFR"
    
    def test_binding_affinity(self, parser):
        """Test binding queries."""
        result = parser.parse("target binding affinity")
        assert result.intent_type == IntentType.ACTIVITY_LOOKUP


# =============================================================================
# Test Structure Conversion (5 patterns)
# =============================================================================

class TestStructureConversion:
    """Test structure conversion intent recognition."""
    
    def test_format_conversion(self, parser):
        """Test format conversion."""
        result = parser.parse("convert smiles to inchi")
        assert result.intent_type == IntentType.STRUCTURE_CONVERSION
        assert result.entities.get("format") == "inchi"
    
    def test_standardization(self, parser):
        """Test standardization queries."""
        queries = ["canonicalize smiles", "standardize structure", "normalize"]
        
        for query in queries:
            result = parser.parse(query)
            assert result.intent_type in [
                IntentType.STANDARDIZATION,
                IntentType.STRUCTURE_CONVERSION
            ]
    
    def test_smiles_conversion(self, parser):
        """Test SMILES conversion."""
        result = parser.parse("smiles to inchikey")
        assert result.intent_type == IntentType.STRUCTURE_CONVERSION


# =============================================================================
# Test Entity Extraction
# =============================================================================

class TestEntityExtraction:
    """Test entity extraction from queries."""
    
    def test_smiles_extraction(self, parser):
        """Test SMILES extraction."""
        result = parser.parse("properties of CC(=O)Oc1ccccc1C(=O)O")
        assert result.entities.get("smiles") == "CC(=O)Oc1ccccc1C(=O)O"
    
    def test_chembl_extraction(self, parser):
        """Test ChEMBL ID extraction."""
        queries = ["CHEMBL25", "chembl25", "CHEMBL123456"]
        
        for query in queries:
            result = parser.parse(f"info on {query}")
            chembl_id = result.entities.get("chembl_id")
            assert chembl_id is not None
            assert chembl_id.startswith("CHEMBL")
    
    def test_threshold_extraction(self, parser):
        """Test threshold extraction variations."""
        queries_and_thresholds = [
            ("similarity 0.8", 0.8),
            ("threshold > 0.7", 0.7),
            ("70% similarity", 0.7),
        ]
        
        for query, expected in queries_and_thresholds:
            result = parser.parse(query)
            threshold = result.entities.get("threshold")
            assert threshold is not None
            assert abs(threshold - expected) < 0.01
    
    def test_limit_extraction(self, parser):
        """Test result limit extraction."""
        queries_and_limits = [
            ("top 10 compounds", 10),
            ("limit 50 results", 50),
            ("first 20 molecules", 20),
        ]
        
        for query, expected_limit in queries_and_limits:
            result = parser.parse(query)
            assert result.entities.get("limit") == expected_limit


# =============================================================================
# Test Constraint Extraction
# =============================================================================

class TestConstraintExtraction:
    """Test constraint extraction from queries."""
    
    def test_mw_constraints(self, parser):
        """Test MW constraint extraction."""
        queries = [
            ("MW < 500", {"mw_max": 500}),
            ("molecular weight greater than 300", {"mw_min": 300}),
            ("mass below 450", {"mw_max": 450}),
        ]
        
        for query, expected in queries:
            result = parser.parse(query)
            for key, value in expected.items():
                assert result.constraints.get(key) == value
    
    def test_logp_constraints(self, parser):
        """Test LogP constraint extraction."""
        queries = [
            ("LogP < 5", {"logp_max": 5.0}),
            ("clogp greater than 2", {"logp_min": 2.0}),
        ]
        
        for query, expected in queries:
            result = parser.parse(query)
            for key, value in expected.items():
                assert result.constraints.get(key) == value
    
    def test_tpsa_constraints(self, parser):
        """Test TPSA constraint extraction."""
        result = parser.parse("TPSA < 140")
        assert result.constraints.get("tpsa_max") == 140


# =============================================================================
# Test Fallback and Edge Cases
# =============================================================================

class TestFallbackParsing:
    """Test fallback parsing for ambiguous queries."""
    
    def test_unknown_query(self, parser):
        """Test completely unknown query."""
        result = parser.parse("random unrelated text")
        assert result.intent_type == IntentType.UNKNOWN
        assert result.confidence == 0.5
    
    def test_partial_match(self, parser):
        """Test partial entity extraction."""
        result = parser.parse("tell me about aspirin")
        # Should still extract compound name
        assert result.entities.get("compound") == "aspirin"
    
    def test_empty_query(self, parser):
        """Test empty query."""
        result = parser.parse("")
        assert result.intent_type == IntentType.UNKNOWN


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegrationScenarios:
    """Test realistic multi-entity scenarios."""
    
    def test_complex_similarity_query(self, parser):
        """Test complex similarity query with multiple entities."""
        query = "Find top 10 compounds similar to aspirin with similarity > 0.8"
        result = parser.parse(query)
        
        assert result.intent_type == IntentType.SIMILARITY_SEARCH
        assert result.entities.get("compound") == "aspirin"
        assert result.entities.get("threshold") == 0.8
        assert result.entities.get("limit") == 10
    
    def test_filtered_search(self, parser):
        """Test search with property filters."""
        query = "Find similar compounds to aspirin with MW < 500"
        result = parser.parse(query)
        
        assert result.intent_type == IntentType.SIMILARITY_SEARCH
        assert result.entities.get("compound") == "aspirin"
        assert result.constraints.get("mw_max") == 500
    
    def test_activity_with_target(self, parser):
        """Test activity query with compound and target."""
        query = "IC50 for aspirin against COX-2"
        result = parser.parse(query)
        
        assert result.intent_type == IntentType.ACTIVITY_LOOKUP
        assert result.entities.get("compound") == "aspirin"
        assert result.entities.get("target") == "COX-2"
        assert result.entities.get("activity_type") == "IC50"


# =============================================================================
# Performance Tests
# =============================================================================

class TestPerformance:
    """Test parser performance."""
    
    def test_batch_parsing(self, parser):
        """Test parsing multiple queries."""
        queries = [
            "Find similar compounds to aspirin",
            "What is CHEMBL25",
            "LogP of caffeine",
            "IC50 for COX-2",
            "Lipinski rule check",
        ] * 10  # 50 queries
        
        results = [parser.parse(q) for q in queries]
        
        # All should parse successfully
        assert len(results) == 50
        assert all(r.intent_type != IntentType.UNKNOWN for r in results)
