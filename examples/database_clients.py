"""
Database Clients Example
========================

Demonstrates ChEMBL, BindingDB, and UniProt client usage.
"""

from chemagent.tools.chembl_client import ChEMBLClient
from chemagent.tools.bindingdb_client import BindingDBClient
from chemagent.tools.uniprot_client import UniProtClient


def main():
    """Run database client examples."""
    
    print("="*70)
    print("ChemAgent Database Clients Demo")
    print("="*70)
    
    # =========================================================================
    # ChEMBL Examples
    # =========================================================================
    print("\n" + "="*70)
    print("1. ChEMBL Client")
    print("="*70)
    
    chembl = ChEMBLClient()
    
    # Example 1.1: Search by name
    print("\n1.1 Search by compound name")
    print("-" * 70)
    results = chembl.search_by_name("aspirin", limit=3)
    for r in results:
        print(f"  {r.chembl_id}: {r.smiles}")
        print(f"    MW: {r.molecular_weight:.2f}, LogP: {r.alogp:.2f}")
    
    # Example 1.2: Get compound details
    if results:
        print("\n1.2 Get compound details")
        print("-" * 70)
        chembl_id = results[0].chembl_id
        compound = chembl.get_compound(chembl_id)
        print(f"  ChEMBL ID: {compound.chembl_id}")
        print(f"  Formula: {compound.molecular_formula}")
        print(f"  InChI Key: {compound.inchi_key}")
        print(f"  Synonyms: {', '.join(compound.synonyms[:3])}")
    
    # Example 1.3: Similarity search
    print("\n1.3 Similarity search")
    print("-" * 70)
    similar = chembl.similarity_search("CCO", threshold=0.7, limit=5)
    print(f"  Found {len(similar)} compounds similar to ethanol")
    for s in similar[:3]:
        print(f"    {s.chembl_id}: {s.smiles}")
    
    # Example 1.4: Get bioactivities
    print("\n1.4 Get bioactivities")
    print("-" * 70)
    activities = chembl.get_activities("CHEMBL25", limit=5)
    print(f"  Found {len(activities)} bioactivity records for CHEMBL25")
    for a in activities[:3]:
        value_str = f"{a.standard_value} {a.standard_units}" if a.standard_value else "N/A"
        print(f"    {a.target_name}: {a.standard_type} = {value_str}")
    
    # Example 1.5: Get target info
    if activities:
        print("\n1.5 Get target information")
        print("-" * 70)
        target_id = activities[0].target_chembl_id
        if target_id:
            target = chembl.get_target_info(target_id)
            if target:
                print(f"  Target: {target.pref_name}")
                print(f"  Type: {target.target_type}")
                print(f"  Organism: {target.organism}")
    
    # =========================================================================
    # BindingDB Examples
    # =========================================================================
    print("\n" + "="*70)
    print("2. BindingDB Client")
    print("="*70)
    
    bindingdb = BindingDBClient()
    
    # Example 2.1: Search by target
    print("\n2.1 Search binding data by target")
    print("-" * 70)
    try:
        affinities = bindingdb.search_by_target("COX-2", limit=5)
        print(f"  Found {len(affinities)} binding records for COX-2")
        for a in affinities[:3]:
            if a.ic50_nm:
                print(f"    IC50: {a.ic50_nm:.2f} nM")
                if a.ligand_smiles:
                    print(f"    SMILES: {a.ligand_smiles[:50]}...")
    except Exception as e:
        print(f"  Note: BindingDB query may require network access: {e}")
    
    # Example 2.2: Get affinity data for compound
    print("\n2.2 Get affinity data for compound")
    print("-" * 70)
    try:
        compound_affinities = bindingdb.get_affinity_data("imatinib", limit=5)
        print(f"  Found {len(compound_affinities)} target affinities for imatinib")
        for a in compound_affinities[:3]:
            print(f"    Target: {a.target_name} ({a.target_source_organism})")
            if a.ki_nm:
                print(f"    Ki: {a.ki_nm:.2f} nM")
    except Exception as e:
        print(f"  Note: BindingDB query may require network access: {e}")
    
    # =========================================================================
    # UniProt Examples
    # =========================================================================
    print("\n" + "="*70)
    print("3. UniProt Client")
    print("="*70)
    
    uniprot = UniProtClient()
    
    # Example 3.1: Get protein info
    print("\n3.1 Get protein information")
    print("-" * 70)
    try:
        protein = uniprot.get_protein_info("P35354")  # COX-2
        if protein:
            print(f"  UniProt ID: {protein.uniprot_id}")
            print(f"  Protein: {protein.protein_name}")
            print(f"  Genes: {', '.join(protein.gene_names)}")
            print(f"  Organism: {protein.organism}")
            print(f"  Sequence length: {protein.sequence_length} aa")
            print(f"  PDB structures: {len(protein.pdb_ids)}")
            if protein.function_description:
                desc = protein.function_description[:150]
                print(f"  Function: {desc}...")
    except Exception as e:
        print(f"  Note: UniProt query may require network access: {e}")
    
    # Example 3.2: Search proteins
    print("\n3.2 Search proteins")
    print("-" * 70)
    try:
        proteins = uniprot.search_proteins("cyclooxygenase", limit=5)
        print(f"  Found {len(proteins)} proteins")
        for p in proteins[:3]:
            print(f"    {p.uniprot_id}: {p.protein_name}")
            print(f"      Organism: {p.organism}")
    except Exception as e:
        print(f"  Note: UniProt search may require network access: {e}")
    
    # =========================================================================
    # Integrated Example
    # =========================================================================
    print("\n" + "="*70)
    print("4. Integrated Multi-Database Query")
    print("="*70)
    print("\nScenario: Research aspirin's target (COX-2)")
    print("-" * 70)
    
    # Step 1: Get aspirin from ChEMBL
    print("\nStep 1: Get aspirin compound data from ChEMBL")
    aspirin_results = chembl.search_by_name("aspirin", limit=1)
    if aspirin_results:
        aspirin = aspirin_results[0]
        print(f"  ✓ Found: {aspirin.chembl_id}")
        print(f"  SMILES: {aspirin.smiles}")
        print(f"  MW: {aspirin.molecular_weight:.2f}")
        
        # Step 2: Get bioactivities from ChEMBL
        print("\nStep 2: Get bioactivity data from ChEMBL")
        activities = chembl.get_activities(aspirin.chembl_id, limit=5)
        print(f"  ✓ Found {len(activities)} bioactivity records")
        
        # Find COX-2 target
        cox2_target = None
        for act in activities:
            if "COX-2" in act.target_name or "PTGS2" in act.target_name:
                cox2_target = act
                break
        
        if cox2_target:
            print(f"  ✓ Found COX-2 activity:")
            print(f"    Target: {cox2_target.target_name}")
            print(f"    {cox2_target.standard_type}: {cox2_target.standard_value} {cox2_target.standard_units}")
            
            # Step 3: Get target details from ChEMBL
            print("\nStep 3: Get target details from ChEMBL")
            target = chembl.get_target_info(cox2_target.target_chembl_id)
            if target:
                print(f"  ✓ Target: {target.pref_name}")
                print(f"  Type: {target.target_type}")
                
                # Step 4: Get protein info from UniProt
                print("\nStep 4: Get protein sequence from UniProt")
                try:
                    protein = uniprot.get_protein_info("P35354")  # COX-2 UniProt ID
                    if protein:
                        print(f"  ✓ Protein: {protein.protein_name}")
                        print(f"  Sequence: {protein.sequence_length} amino acids")
                        print(f"  PDB structures available: {len(protein.pdb_ids)}")
                except Exception as e:
                    print(f"  Note: UniProt query requires network: {e}")
    
    print("\n" + "="*70)
    print("Demo complete!")
    print("="*70)
    print("\n💡 Tips:")
    print("  • All queries are cached (24h TTL)")
    print("  • Second run will be much faster")
    print("  • Rate limiting prevents API overload")
    print("  • All results include provenance metadata")
    print("="*70)


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    main()
