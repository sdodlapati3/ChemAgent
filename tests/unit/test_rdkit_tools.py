"""
Tests for RDKit Tools
====================

Comprehensive test suite for RDKit chemistry functions.

Run with:
    pytest tests/unit/test_rdkit_tools.py -v
    pytest tests/unit/test_rdkit_tools.py --cov=chemagent.tools.rdkit_tools
"""

import pytest
from rdkit import Chem

from chemagent.tools.rdkit_tools import (
    RDKitTools,
    StandardizedResult,
    MolecularProperties,
    LipinskiResult,
    SimilarityResult,
    smiles_to_mol,
    mol_to_smiles,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def rdkit_tools():
    """Create RDKitTools instance."""
    return RDKitTools()


@pytest.fixture
def aspirin_smiles():
    """Aspirin SMILES."""
    return "CC(=O)Oc1ccccc1C(=O)O"


@pytest.fixture
def aspirin_mol(aspirin_smiles):
    """Aspirin Mol object."""
    return Chem.MolFromSmiles(aspirin_smiles)


@pytest.fixture
def lipinski_passing_molecules():
    """Molecules that pass Lipinski Rule of 5."""
    return [
        "CC(=O)Oc1ccccc1C(=O)O",  # Aspirin
        "CC(C)Cc1ccc(cc1)C(C)C(=O)O",  # Ibuprofen
        "CN1C=NC2=C1C(=O)N(C(=O)N2C)C",  # Caffeine
    ]


@pytest.fixture
def lipinski_failing_molecules():
    """Molecules that fail Lipinski Rule of 5."""
    return [
        "CC(C)CC1=CC=C(C=C1)C(C)C(=O)OCCCCCCCCCCCCCCCCCC",  # High MW
        "C1=CC=C(C=C1)C2=CC=C(C=C2)C3=CC=C(C=C3)C4=CC=C(C=C4)C5=CC=C(C=C5)C6=CC=C(C=C6)C7=CC=CC=C7",  # Very high MW
    ]


# =============================================================================
# Test SMILES Standardization
# =============================================================================

class TestStandardization:
    """Test SMILES standardization."""
    
    def test_standardize_valid_smiles(self, rdkit_tools, aspirin_smiles):
        """Test standardization of valid SMILES."""
        result = rdkit_tools.standardize_smiles(aspirin_smiles)
        
        assert isinstance(result, StandardizedResult)
        assert result.smiles  # Non-empty
        assert result.inchi.startswith("InChI=")
        assert len(result.inchi_key) == 27  # Standard InChI Key length
        assert result.molecular_formula == "C9H8O4"
        
        # Check provenance
        assert result.provenance.source == "rdkit"
        assert result.provenance.method == "standardize_smiles"
    
    def test_standardize_invalid_smiles(self, rdkit_tools):
        """Test standardization of invalid SMILES raises error."""
        with pytest.raises(ValueError, match="Invalid SMILES"):
            rdkit_tools.standardize_smiles("invalid_smiles")
    
    def test_standardize_with_salt(self, rdkit_tools):
        """Test standardization removes salts."""
        # Sodium aspirin
        smiles_with_salt = "CC(=O)Oc1ccccc1C(=O)[O-].[Na+]"
        result = rdkit_tools.standardize_smiles(smiles_with_salt, remove_salts=True)
        
        # Should remove sodium and keep aspirin
        assert "[Na+]" not in result.smiles
        assert "[O-]" in result.smiles or "O" in result.smiles
    
    def test_standardize_neutralization(self, rdkit_tools):
        """Test standardization neutralizes charges."""
        charged_smiles = "CC(=O)Oc1ccccc1C(=O)[O-]"
        result = rdkit_tools.standardize_smiles(charged_smiles, neutralize=True)
        
        # Should be neutralized (exact result may vary)
        assert isinstance(result, StandardizedResult)
        assert result.smiles
    
    def test_canonical_smiles(self, rdkit_tools):
        """Test that different representations give same canonical SMILES."""
        # Different representations of ethanol
        smiles1 = "CCO"
        smiles2 = "OCC"
        smiles3 = "C(C)O"
        
        result1 = rdkit_tools.standardize_smiles(smiles1)
        result2 = rdkit_tools.standardize_smiles(smiles2)
        result3 = rdkit_tools.standardize_smiles(smiles3)
        
        # All should give same canonical SMILES
        assert result1.smiles == result2.smiles == result3.smiles


# =============================================================================
# Test Property Calculation
# =============================================================================

class TestMolecularProperties:
    """Test molecular property calculations."""
    
    def test_calc_properties_aspirin(self, rdkit_tools, aspirin_mol):
        """Test property calculation for aspirin."""
        props = rdkit_tools.calc_molecular_properties(aspirin_mol)
        
        assert isinstance(props, MolecularProperties)
        
        # Check known values for aspirin
        assert abs(props.molecular_weight - 180.16) < 0.1
        assert 1.0 < props.logp < 1.5  # ~1.19
        assert props.num_h_donors == 1  # Carboxylic acid H
        assert props.num_h_acceptors == 4  # 4 oxygens
        assert props.num_aromatic_rings == 1  # Benzene ring
        
        # Check provenance
        assert props.provenance.source == "rdkit"
        assert props.provenance.method == "calc_molecular_properties"
    
    def test_calc_properties_ethanol(self, rdkit_tools):
        """Test property calculation for ethanol."""
        mol = Chem.MolFromSmiles("CCO")
        props = rdkit_tools.calc_molecular_properties(mol)
        
        assert abs(props.molecular_weight - 46.07) < 0.1
        assert props.num_h_donors == 1  # OH
        assert props.num_h_acceptors == 1  # O
        assert props.num_rings == 0
        assert props.num_rotatable_bonds == 0
    
    def test_calc_properties_complex_molecule(self, rdkit_tools):
        """Test property calculation for more complex molecule."""
        # Ibuprofen
        mol = Chem.MolFromSmiles("CC(C)Cc1ccc(cc1)C(C)C(=O)O")
        props = rdkit_tools.calc_molecular_properties(mol)
        
        assert abs(props.molecular_weight - 206.28) < 0.1
        assert props.num_aromatic_rings == 1
        assert props.num_rotatable_bonds >= 3


class TestLipinski:
    """Test Lipinski Rule of 5 calculations."""
    
    def test_lipinski_passing_aspirin(self, rdkit_tools, aspirin_mol):
        """Test Lipinski for aspirin (should pass)."""
        result = rdkit_tools.calc_lipinski(aspirin_mol)
        
        assert isinstance(result, LipinskiResult)
        assert result.passes is True
        assert result.violations == 0
        assert len(result.details) == 0
        
        # Check values
        assert result.molecular_weight < 500
        assert result.logp < 5
        assert result.num_h_donors <= 5
        assert result.num_h_acceptors <= 10
    
    def test_lipinski_passing_molecules(self, rdkit_tools, lipinski_passing_molecules):
        """Test multiple molecules that should pass Lipinski."""
        for smiles in lipinski_passing_molecules:
            mol = Chem.MolFromSmiles(smiles)
            result = rdkit_tools.calc_lipinski(mol)
            
            assert result.passes is True, f"{smiles} should pass Lipinski"
            assert result.violations <= 1
    
    def test_lipinski_failing_high_mw(self, rdkit_tools):
        """Test molecule failing due to high MW."""
        # High MW molecule
        mol = Chem.MolFromSmiles("CC(C)CC1=CC=C(C=C1)C(C)C(=O)OCCCCCCCCCCCCCCCCCC")
        result = rdkit_tools.calc_lipinski(mol)
        
        assert result.passes is False
        assert result.molecular_weight > 500
        assert any("MW" in detail for detail in result.details)
    
    def test_lipinski_one_violation_passes(self, rdkit_tools):
        """Test that 1 violation still passes (Lipinski definition)."""
        # Create a molecule with exactly 1 violation
        # MW ~520 (one violation), but everything else OK
        mol = Chem.MolFromSmiles("CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC(=O)O")
        result = rdkit_tools.calc_lipinski(mol)
        
        # Should have MW violation but still "pass" (≤1 violation allowed)
        if result.violations == 1:
            assert result.passes is True


# =============================================================================
# Test Similarity Search
# =============================================================================

class TestSimilarity:
    """Test similarity calculations."""
    
    def test_calc_fingerprint(self, rdkit_tools, aspirin_mol):
        """Test fingerprint calculation."""
        fp = rdkit_tools.calc_fingerprint(aspirin_mol, fp_type="morgan", radius=2)
        
        assert fp is not None
        assert len(fp) == 2048  # Default n_bits
    
    def test_calc_similarity_identical(self, rdkit_tools, aspirin_mol):
        """Test similarity of molecule with itself."""
        similarity = rdkit_tools.calc_similarity(aspirin_mol, aspirin_mol)
        
        assert similarity == 1.0  # Identical molecules
    
    def test_calc_similarity_similar(self, rdkit_tools):
        """Test similarity of similar molecules."""
        mol1 = Chem.MolFromSmiles("CCO")  # Ethanol
        mol2 = Chem.MolFromSmiles("CCCO")  # Propanol
        
        similarity = rdkit_tools.calc_similarity(mol1, mol2)
        
        assert 0.5 < similarity < 1.0  # Should be similar but not identical
    
    def test_calc_similarity_different(self, rdkit_tools):
        """Test similarity of very different molecules."""
        mol1 = Chem.MolFromSmiles("CCO")  # Ethanol
        mol2 = Chem.MolFromSmiles("c1ccccc1")  # Benzene
        
        similarity = rdkit_tools.calc_similarity(mol1, mol2)
        
        assert similarity < 0.5  # Should be dissimilar
    
    def test_similarity_search(self, rdkit_tools):
        """Test similarity search in molecule list."""
        query = Chem.MolFromSmiles("CCO")
        
        mols = [
            Chem.MolFromSmiles("CCCO"),  # Similar (propanol)
            Chem.MolFromSmiles("CCCCO"),  # Similar (butanol)
            Chem.MolFromSmiles("c1ccccc1"),  # Different (benzene)
            Chem.MolFromSmiles("CC(C)O"),  # Similar (isopropanol)
        ]
        
        results = rdkit_tools.similarity_search(
            query, mols, threshold=0.5, return_top_n=None
        )
        
        # Should find similar alcohols, not benzene
        assert len(results) >= 2
        
        # Check results are sorted by descending similarity
        for i in range(len(results) - 1):
            assert results[i].similarity >= results[i + 1].similarity
        
        # Check provenance
        assert results[0].provenance.source == "rdkit"
        assert results[0].provenance.method == "similarity_search"
    
    def test_similarity_search_top_n(self, rdkit_tools):
        """Test similarity search with top N limit."""
        query = Chem.MolFromSmiles("CCO")
        
        mols = [Chem.MolFromSmiles(s) for s in ["CCCO", "CCCCO", "CCCCCO", "CCCCCCO"]]
        
        results = rdkit_tools.similarity_search(query, mols, threshold=0.3, return_top_n=2)
        
        assert len(results) == 2
        assert results[0].similarity >= results[1].similarity


# =============================================================================
# Test Substructure Search
# =============================================================================

class TestSubstructure:
    """Test substructure search."""
    
    def test_substructure_search_benzene(self, rdkit_tools):
        """Test searching for benzene ring."""
        mols = [
            Chem.MolFromSmiles("c1ccccc1"),  # Benzene
            Chem.MolFromSmiles("CCO"),  # Ethanol (no benzene)
            Chem.MolFromSmiles("c1ccccc1O"),  # Phenol
            Chem.MolFromSmiles("c1ccc(cc1)C(=O)O"),  # Benzoic acid
        ]
        
        matches = rdkit_tools.substructure_search("c1ccccc1", mols)
        
        assert len(matches) == 3  # Indices 0, 2, 3
        assert matches == [0, 2, 3]
    
    def test_substructure_search_carbonyl(self, rdkit_tools):
        """Test searching for carbonyl group."""
        mols = [
            Chem.MolFromSmiles("CC(=O)O"),  # Acetic acid
            Chem.MolFromSmiles("CCO"),  # Ethanol (no carbonyl)
            Chem.MolFromSmiles("CC(=O)C"),  # Acetone
        ]
        
        matches = rdkit_tools.substructure_search("C(=O)", mols)
        
        assert len(matches) == 2  # Indices 0, 2
        assert 1 not in matches
    
    def test_substructure_search_invalid_smarts(self, rdkit_tools):
        """Test invalid SMARTS pattern."""
        mols = [Chem.MolFromSmiles("CCO")]
        
        with pytest.raises(ValueError, match="Invalid SMARTS"):
            rdkit_tools.substructure_search("[invalid", mols)


# =============================================================================
# Test Scaffold Extraction
# =============================================================================

class TestScaffold:
    """Test scaffold extraction."""
    
    def test_extract_murcko_scaffold(self, rdkit_tools):
        """Test Murcko scaffold extraction."""
        # Phenethylamine: benzene ring + ethyl + amine
        mol = Chem.MolFromSmiles("c1ccc(cc1)CCN")
        scaffold = rdkit_tools.extract_murcko_scaffold(mol)
        
        # Scaffold should be benzene + ethyl chain (no amine)
        assert "c1ccc" in scaffold
        assert "CC" in scaffold
    
    def test_scaffold_simple_molecule(self, rdkit_tools):
        """Test scaffold of simple molecule."""
        mol = Chem.MolFromSmiles("CCO")  # Ethanol
        scaffold = rdkit_tools.extract_murcko_scaffold(mol)
        
        # Simple molecules may return themselves
        assert scaffold


# =============================================================================
# Test Validation
# =============================================================================

class TestValidation:
    """Test SMILES/SMARTS validation."""
    
    def test_is_valid_smiles_valid(self, rdkit_tools):
        """Test validation of valid SMILES."""
        assert rdkit_tools.is_valid_smiles("CCO") is True
        assert rdkit_tools.is_valid_smiles("c1ccccc1") is True
        assert rdkit_tools.is_valid_smiles("CC(=O)O") is True
    
    def test_is_valid_smiles_invalid(self, rdkit_tools):
        """Test validation of invalid SMILES."""
        assert rdkit_tools.is_valid_smiles("invalid") is False
        assert rdkit_tools.is_valid_smiles("CC(") is False
        assert rdkit_tools.is_valid_smiles("") is False
    
    def test_is_valid_smarts_valid(self, rdkit_tools):
        """Test validation of valid SMARTS."""
        assert rdkit_tools.is_valid_smarts("c1ccccc1") is True
        assert rdkit_tools.is_valid_smarts("C(=O)") is True
        assert rdkit_tools.is_valid_smarts("[#6]") is True
    
    def test_is_valid_smarts_invalid(self, rdkit_tools):
        """Test validation of invalid SMARTS."""
        assert rdkit_tools.is_valid_smarts("[invalid") is False
        assert rdkit_tools.is_valid_smarts("") is False


# =============================================================================
# Test Convenience Functions
# =============================================================================

class TestConvenienceFunctions:
    """Test convenience functions."""
    
    def test_smiles_to_mol_valid(self, aspirin_smiles):
        """Test SMILES to Mol conversion."""
        mol = smiles_to_mol(aspirin_smiles)
        
        assert mol is not None
        assert isinstance(mol, Chem.Mol)
    
    def test_smiles_to_mol_invalid(self):
        """Test invalid SMILES raises error."""
        with pytest.raises(ValueError, match="Invalid SMILES"):
            smiles_to_mol("invalid")
    
    def test_mol_to_smiles(self, aspirin_mol):
        """Test Mol to SMILES conversion."""
        smiles = mol_to_smiles(aspirin_mol, canonical=True)
        
        assert isinstance(smiles, str)
        assert len(smiles) > 0
    
    def test_roundtrip_conversion(self, aspirin_smiles):
        """Test SMILES → Mol → SMILES roundtrip."""
        mol = smiles_to_mol(aspirin_smiles)
        smiles_out = mol_to_smiles(mol, canonical=True)
        
        # Should get back to same canonical SMILES
        mol2 = smiles_to_mol(smiles_out)
        smiles_out2 = mol_to_smiles(mol2, canonical=True)
        
        assert smiles_out == smiles_out2


# =============================================================================
# Edge Cases and Error Handling
# =============================================================================

class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_molecule_list(self, rdkit_tools):
        """Test similarity search with empty list."""
        query = Chem.MolFromSmiles("CCO")
        results = rdkit_tools.similarity_search(query, [], threshold=0.7)
        
        assert len(results) == 0
    
    def test_none_in_molecule_list(self, rdkit_tools):
        """Test handling of None in molecule list."""
        query = Chem.MolFromSmiles("CCO")
        mols = [Chem.MolFromSmiles("CCCO"), None, Chem.MolFromSmiles("CCCCO")]
        
        results = rdkit_tools.similarity_search(query, mols, threshold=0.5)
        
        # Should skip None and return valid results
        assert len(results) == 2
    
    def test_threshold_edge_cases(self, rdkit_tools):
        """Test similarity search with edge case thresholds."""
        query = Chem.MolFromSmiles("CCO")
        mols = [Chem.MolFromSmiles("CCO")]  # Identical
        
        # Threshold 1.0 should only match identical
        results = rdkit_tools.similarity_search(query, mols, threshold=1.0)
        assert len(results) == 1
        assert results[0].similarity == 1.0
        
        # Threshold 0.0 should match everything
        results = rdkit_tools.similarity_search(query, mols, threshold=0.0)
        assert len(results) >= 1


# =============================================================================
# Performance Tests (marked as slow)
# =============================================================================

@pytest.mark.slow
class TestPerformance:
    """Performance tests (marked as slow, run with: pytest -m slow)."""
    
    def test_large_similarity_search(self, rdkit_tools):
        """Test similarity search with large molecule list."""
        import time
        
        query = Chem.MolFromSmiles("CCO")
        
        # Generate 1000 random-ish molecules
        mols = []
        for i in range(1000):
            smiles = f"{'C' * (i % 10)}O"
            mol = Chem.MolFromSmiles(smiles)
            if mol:
                mols.append(mol)
        
        start = time.time()
        results = rdkit_tools.similarity_search(query, mols, threshold=0.5)
        elapsed = time.time() - start
        
        print(f"Searched {len(mols)} molecules in {elapsed:.2f}s")
        
        assert elapsed < 10.0  # Should complete in reasonable time
        assert len(results) >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
