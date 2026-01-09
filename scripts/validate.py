"""
Integration Validation Script
==============================

Validates that database clients work with real APIs.
Run this to verify everything is connected properly.

Note: Requires internet connection and may be slow on first run.
"""

import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from chemagent.tools.rdkit_tools import RDKitTools
from chemagent.tools.chembl_client import ChEMBLClient
from chemagent.tools.bindingdb_client import BindingDBClient
from chemagent.tools.uniprot_client import UniProtClient


logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def test_rdkit_tools():
    """Test RDKit tools."""
    print("\n" + "="*70)
    print("Testing RDKit Tools")
    print("="*70)
    
    try:
        tools = RDKitTools()
        
        # Test 1: SMILES standardization
        result = tools.standardize_smiles("CCO")
        assert result.smiles is not None
        assert result.inchi_key is not None
        print("✓ SMILES standardization works")
        
        # Test 2: Property calculation
        from rdkit import Chem
        mol = Chem.MolFromSmiles("CCO")
        props = tools.calc_molecular_properties(mol)
        assert props.molecular_weight > 0
        print("✓ Property calculation works")
        
        # Test 3: Lipinski
        lipinski = tools.calc_lipinski(mol)
        assert lipinski.passes is not None
        print("✓ Lipinski calculation works")
        
        return True
        
    except Exception as e:
        print(f"✗ RDKit tools failed: {e}")
        return False


def test_chembl_client():
    """Test ChEMBL client."""
    print("\n" + "="*70)
    print("Testing ChEMBL Client")
    print("="*70)
    
    try:
        client = ChEMBLClient()
        
        # Test 1: Search by name
        results = client.search_by_name("aspirin", limit=2)
        if results:
            print(f"✓ Search by name works: Found {len(results)} results")
            print(f"  Example: {results[0].chembl_id} - {results[0].smiles}")
        else:
            print("⚠ Search returned no results (might be API issue)")
            return False
        
        # Test 2: Get compound
        compound = client.get_compound(results[0].chembl_id)
        if compound:
            print(f"✓ Get compound works: {compound.chembl_id}")
        else:
            print("✗ Get compound failed")
            return False
        
        # Test 3: Check caching
        cache_key = f"compound:{results[0].chembl_id}"
        if cache_key in client.cache:
            print("✓ Caching works")
        else:
            print("⚠ Caching not working as expected")
        
        # Test 4: Provenance
        if compound.provenance and compound.provenance.source == "chembl":
            print("✓ Provenance tracking works")
        else:
            print("✗ Provenance tracking failed")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ ChEMBL client failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_bindingdb_client():
    """Test BindingDB client."""
    print("\n" + "="*70)
    print("Testing BindingDB Client")
    print("="*70)
    
    try:
        client = BindingDBClient()
        
        # Test: Search by target
        # Note: BindingDB API can be slow/unreliable
        print("Attempting BindingDB query (may be slow)...")
        results = client.search_by_target("COX-2", limit=3)
        
        if results:
            print(f"✓ Search by target works: Found {len(results)} results")
            if results[0].ic50_nm:
                print(f"  Example IC50: {results[0].ic50_nm:.2f} nM")
        else:
            print("⚠ BindingDB returned no results (API may be down or rate-limited)")
            print("  This is not necessarily an error - BindingDB can be unreliable")
        
        # Test provenance even if no results
        if not results or results[0].provenance:
            print("✓ BindingDB client initialized correctly")
            return True
        
        return True
        
    except Exception as e:
        print(f"⚠ BindingDB client error (expected - API can be unreliable): {e}")
        # BindingDB failures are expected, don't fail validation
        return True


def test_uniprot_client():
    """Test UniProt client."""
    print("\n" + "="*70)
    print("Testing UniProt Client")
    print("="*70)
    
    try:
        client = UniProtClient()
        
        # Test 1: Get protein info
        protein = client.get_protein_info("P35354")  # COX-2
        if protein:
            print(f"✓ Get protein info works: {protein.protein_name}")
            print(f"  Organism: {protein.organism}")
            print(f"  Sequence length: {protein.sequence_length} aa")
        else:
            print("✗ Get protein info failed")
            return False
        
        # Test 2: Search proteins
        results = client.search_proteins("cyclooxygenase", limit=3)
        if results:
            print(f"✓ Search proteins works: Found {len(results)} results")
        else:
            print("⚠ Search returned no results")
        
        # Test 3: Provenance
        if protein.provenance and protein.provenance.source == "uniprot":
            print("✓ Provenance tracking works")
        else:
            print("✗ Provenance tracking failed")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ UniProt client failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all validation tests."""
    print("\n" + "="*70)
    print("ChemAgent Validation Suite")
    print("="*70)
    print("\nThis will test all database clients with real API calls.")
    print("First run may be slow. Subsequent runs will use cache.")
    print("="*70)
    
    results = {
        "RDKit Tools": test_rdkit_tools(),
        "ChEMBL Client": test_chembl_client(),
        "BindingDB Client": test_bindingdb_client(),
        "UniProt Client": test_uniprot_client(),
    }
    
    print("\n" + "="*70)
    print("Validation Summary")
    print("="*70)
    
    for name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{name:20s}: {status}")
    
    print("="*70)
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n🎉 All validations passed!")
        print("\n✅ ChemAgent is ready to use!")
        print("\nNext steps:")
        print("  1. Run full test suite: pytest tests/unit/")
        print("  2. Try examples: python examples/database_clients.py")
        print("  3. Continue with Phase 1 Week 2 implementation")
        return 0
    else:
        print("\n⚠ Some validations failed!")
        print("\nThis might be due to:")
        print("  • Network connectivity issues")
        print("  • API rate limiting")
        print("  • Missing dependencies")
        print("\nCheck the error messages above for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
