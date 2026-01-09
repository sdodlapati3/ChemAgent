"""
ChemAgent Example: Basic Usage
===============================

This example demonstrates basic ChemAgent functionality:
- SMILES standardization
- Property calculation  
- Lipinski Rule of 5 evaluation
- Similarity search
"""

from rdkit import Chem
from chemagent.tools.rdkit_tools import RDKitTools


def main():
    """Run basic ChemAgent examples."""
    
    # Initialize tools
    tools = RDKitTools()
    
    print("="*70)
    print("ChemAgent Basic Usage Examples")
    print("="*70)
    
    # Example 1: Standardize SMILES
    print("\n1. SMILES Standardization")
    print("-" * 70)
    
    smiles = "CC(=O)Oc1ccccc1C(=O)O"  # Aspirin
    print(f"Input SMILES: {smiles}")
    
    result = tools.standardize_smiles(smiles)
    print(f"Canonical SMILES: {result.smiles}")
    print(f"InChI Key: {result.inchi_key}")
    print(f"Formula: {result.molecular_formula}")
    
    # Example 2: Calculate molecular properties
    print("\n2. Molecular Properties")
    print("-" * 70)
    
    mol = Chem.MolFromSmiles(smiles)
    props = tools.calc_molecular_properties(mol)
    
    print(f"Molecular Weight: {props.molecular_weight:.2f}")
    print(f"LogP: {props.logp:.2f}")
    print(f"TPSA: {props.tpsa:.2f}")
    print(f"H-bond Donors: {props.num_h_donors}")
    print(f"H-bond Acceptors: {props.num_h_acceptors}")
    print(f"Rotatable Bonds: {props.num_rotatable_bonds}")
    
    # Example 3: Lipinski Rule of 5
    print("\n3. Lipinski Rule of 5")
    print("-" * 70)
    
    lipinski = tools.calc_lipinski(mol)
    print(f"Passes Lipinski: {lipinski.passes}")
    print(f"Violations: {lipinski.violations}")
    
    if lipinski.details:
        print("Violation details:")
        for detail in lipinski.details:
            print(f"  - {detail}")
    else:
        print("No violations (drug-like molecule)")
    
    # Example 4: Similarity search
    print("\n4. Similarity Search")
    print("-" * 70)
    
    # Query molecule (aspirin)
    query_mol = Chem.MolFromSmiles("CC(=O)Oc1ccccc1C(=O)O")
    
    # Database of molecules to search
    molecules = {
        "Salicylic acid": "O=C(O)c1ccccc1O",
        "Benzoic acid": "O=C(O)c1ccccc1",
        "Paracetamol": "CC(=O)Nc1ccc(O)cc1",
        "Ibuprofen": "CC(C)Cc1ccc(cc1)C(C)C(=O)O",
        "Ethanol": "CCO",
    }
    
    mol_list = [Chem.MolFromSmiles(s) for s in molecules.values()]
    
    # Find similar molecules
    results = tools.similarity_search(
        query_mol,
        mol_list,
        threshold=0.3,
        return_top_n=3
    )
    
    print(f"Query: Aspirin")
    print(f"Found {len(results)} similar molecules:")
    
    mol_names = list(molecules.keys())
    for result in results:
        name = mol_names[result.index]
        print(f"  {name}: {result.similarity:.3f}")
    
    # Example 5: Substructure search
    print("\n5. Substructure Search")
    print("-" * 70)
    
    # Search for molecules containing a benzene ring
    benzene_pattern = "c1ccccc1"
    matches = tools.substructure_search(benzene_pattern, mol_list)
    
    print(f"Molecules containing benzene ring:")
    for idx in matches:
        name = mol_names[idx]
        print(f"  - {name}")
    
    # Example 6: Scaffold extraction
    print("\n6. Murcko Scaffold Extraction")
    print("-" * 70)
    
    mol = Chem.MolFromSmiles("c1ccc(cc1)CCN")  # Phenethylamine
    scaffold = tools.extract_murcko_scaffold(mol)
    
    print(f"Original: c1ccc(cc1)CCN (Phenethylamine)")
    print(f"Scaffold: {scaffold}")
    
    print("\n" + "="*70)
    print("Examples complete!")
    print("="*70)


if __name__ == "__main__":
    main()
