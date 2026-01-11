#!/usr/bin/env python3
"""
Query Generator for Comprehensive Testing

Generates test queries across all intent types with variations,
edge cases, and error scenarios.
"""
import random
from typing import Dict, List


# =============================================================================
# Common Compounds and Targets
# =============================================================================

COMMON_COMPOUNDS = [
    "aspirin", "ibuprofen", "acetaminophen", "paracetamol", "caffeine",
    "morphine", "cocaine", "warfarin", "insulin", "penicillin", "metformin",
    "atorvastatin", "lipitor", "viagra", "sildenafil", "prozac", "fluoxetine",
    "amoxicillin", "codeine", "diazepam", "omeprazole", "simvastatin"
]

CHEMBL_IDS = [
    "CHEMBL25", "CHEMBL521", "CHEMBL112", "CHEMBL1200829", "CHEMBL113",
    "CHEMBL1200845", "CHEMBL370", "CHEMBL308932", "CHEMBL1201585", "CHEMBL1431",
    "CHEMBL1200766", "CHEMBL1487", "CHEMBL1771", "CHEMBL192", "CHEMBL941"
]

SMILES_EXAMPLES = [
    "CC(=O)Oc1ccccc1C(=O)O",  # Aspirin
    "CC(C)Cc1ccc(cc1)C(C)C(=O)O",  # Ibuprofen
    "CN1C=NC2=C1C(=O)N(C(=O)N2C)C",  # Caffeine
    "CCO",  # Ethanol
    "CC(C)NCC(COc1ccccc1)O",  # Propranolol
    "c1ccccc1",  # Benzene
    "CC(=O)OC1=CC=CC=C1",  # Phenyl acetate
]

TARGET_PROTEINS = [
    "cyclooxygenase-2", "COX-2", "kinase", "EGFR", "VEGFR",
    "protease", "integrase", "reverse transcriptase",
    "acetylcholinesterase", "carbonic anhydrase"
]

UNIPROT_IDS = [
    "P35354", "P23219", "P00533", "P15056", "P00918",
    "P22303", "Q16539", "P04035"
]

PROPERTIES = [
    "molecular weight", "mw", "logp", "alogp",
    "h-bond donors", "h-bond acceptors", "polar surface area",
    "rotatable bonds", "aromatic rings", "druglikeness"
]


# =============================================================================
# Query Generators by Intent Type
# =============================================================================

def generate_compound_lookup_queries(n: int) -> List[Dict[str, str]]:
    """Generate compound lookup queries."""
    queries = []
    
    # By name
    for compound in random.sample(COMMON_COMPOUNDS, min(n//3, len(COMMON_COMPOUNDS))):
        queries.extend([
            {
                "query": f"What is {compound}?",
                "expected_intent": "compound_lookup"
            },
            {
                "query": f"Tell me about {compound}",
                "expected_intent": "compound_lookup"
            },
            {
                "query": f"Look up {compound}",
                "expected_intent": "compound_lookup"
            },
        ])
    
    # By ChEMBL ID
    for chembl_id in random.sample(CHEMBL_IDS, min(n//3, len(CHEMBL_IDS))):
        queries.extend([
            {
                "query": f"What is {chembl_id}?",
                "expected_intent": "compound_lookup"
            },
            {
                "query": f"Get compound {chembl_id}",
                "expected_intent": "compound_lookup"
            },
        ])
    
    # By SMILES
    for smiles in random.sample(SMILES_EXAMPLES, min(n//3, len(SMILES_EXAMPLES))):
        queries.append({
            "query": f"Look up {smiles}",
            "expected_intent": "compound_lookup"
        })
    
    # Edge cases
    queries.extend([
        {"query": "What is aspirin?", "expected_intent": "compound_lookup"},
        {"query": "Tell me about compound CHEMBL25", "expected_intent": "compound_lookup"},
        {"query": "What is INVALID_ID?", "expected_intent": "compound_lookup"},
        {"query": "Look up CC(=O)Oc1ccccc1C(=O)O", "expected_intent": "compound_lookup"},
    ])
    
    return queries[:n]


def generate_property_queries(n: int) -> List[Dict[str, str]]:
    """Generate property calculation queries."""
    queries = []
    
    for compound in random.sample(COMMON_COMPOUNDS, min(n//2, len(COMMON_COMPOUNDS))):
        queries.extend([
            {
                "query": f"Calculate properties of {compound}",
                "expected_intent": "property_calculation"
            },
            {
                "query": f"What are the properties of {compound}?",
                "expected_intent": "property_calculation"
            },
            {
                "query": f"Get molecular weight of {compound}",
                "expected_intent": "property_calculation"
            },
        ])
    
    for smiles in SMILES_EXAMPLES:
        queries.append({
            "query": f"Calculate properties of {smiles}",
            "expected_intent": "property_calculation"
        })
    
    # Specific property queries
    for prop in PROPERTIES[:5]:
        queries.append({
            "query": f"What is the {prop} of aspirin?",
            "expected_intent": "property_calculation"
        })
    
    return queries[:n]


def generate_similarity_queries(n: int) -> List[Dict[str, str]]:
    """Generate similarity search queries."""
    queries = []
    
    for compound in random.sample(COMMON_COMPOUNDS, min(n//2, len(COMMON_COMPOUNDS))):
        queries.extend([
            {
                "query": f"Find similar compounds to {compound}",
                "expected_intent": "similarity_search"
            },
            {
                "query": f"Search for analogs of {compound}",
                "expected_intent": "similarity_search"
            },
            {
                "query": f"What compounds are similar to {compound}?",
                "expected_intent": "similarity_search"
            },
        ])
    
    # With thresholds
    thresholds = [0.6, 0.7, 0.8, 0.9]
    for threshold in thresholds:
        queries.append({
            "query": f"Find compounds similar to aspirin with similarity > {threshold}",
            "expected_intent": "similarity_search"
        })
    
    # With limits
    for limit in [5, 10, 20]:
        queries.append({
            "query": f"Find top {limit} compounds similar to ibuprofen",
            "expected_intent": "similarity_search"
        })
    
    return queries[:n]


def generate_target_queries(n: int) -> List[Dict[str, str]]:
    """Generate target lookup queries."""
    queries = []
    
    for compound in random.sample(COMMON_COMPOUNDS, min(n//2, len(COMMON_COMPOUNDS))):
        queries.extend([
            {
                "query": f"What targets does {compound} bind to?",
                "expected_intent": "target_lookup"
            },
            {
                "query": f"Find targets for {compound}",
                "expected_intent": "target_lookup"
            },
        ])
    
    for target in TARGET_PROTEINS[:5]:
        queries.append({
            "query": f"Look up {target}",
            "expected_intent": "target_lookup"
        })
    
    for uniprot_id in UNIPROT_IDS[:5]:
        queries.append({
            "query": f"What is {uniprot_id}?",
            "expected_intent": "target_lookup"
        })
    
    return queries[:n]


def generate_lipinski_queries(n: int) -> List[Dict[str, str]]:
    """Generate Lipinski rule queries."""
    queries = []
    
    for compound in random.sample(COMMON_COMPOUNDS, min(n, len(COMMON_COMPOUNDS))):
        queries.extend([
            {
                "query": f"Check Lipinski rules for {compound}",
                "expected_intent": "lipinski_check"
            },
            {
                "query": f"Is {compound} drug-like?",
                "expected_intent": "lipinski_check"
            },
            {
                "query": f"Does {compound} follow Ro5?",
                "expected_intent": "lipinski_check"
            },
        ])
    
    return queries[:n]


def generate_comparison_queries(n: int) -> List[Dict[str, str]]:
    """Generate comparison queries."""
    queries = []
    
    compound_pairs = [
        ("aspirin", "ibuprofen"),
        ("caffeine", "cocaine"),
        ("metformin", "insulin"),
        ("lipitor", "simvastatin"),
        ("viagra", "cialis"),
    ]
    
    for comp1, comp2 in compound_pairs:
        queries.extend([
            {
                "query": f"Compare {comp1} and {comp2}",
                "expected_intent": "comparison"
            },
            {
                "query": f"Compare molecular weight of {comp1} and {comp2}",
                "expected_intent": "comparison"
            },
            {
                "query": f"{comp1} vs {comp2}",
                "expected_intent": "comparison"
            },
            {
                "query": f"What are the differences between {comp1} and {comp2}?",
                "expected_intent": "comparison"
            },
        ])
    
    return queries[:n]


def generate_substructure_queries(n: int) -> List[Dict[str, str]]:
    """Generate substructure search queries."""
    queries = []
    
    functional_groups = [
        ("carboxyl", "C(=O)O"),
        ("amine", "N"),
        ("benzene", "c1ccccc1"),
        ("hydroxyl", "O"),
    ]
    
    for fg_name, smarts in functional_groups:
        queries.extend([
            {
                "query": f"Find compounds with {fg_name} group",
                "expected_intent": "substructure_search"
            },
            {
                "query": f"Search for compounds containing {smarts}",
                "expected_intent": "substructure_search"
            },
        ])
    
    return queries[:n]


def generate_activity_queries(n: int) -> List[Dict[str, str]]:
    """Generate activity lookup queries."""
    queries = []
    
    for compound in random.sample(COMMON_COMPOUNDS, min(n//2, len(COMMON_COMPOUNDS))):
        queries.extend([
            {
                "query": f"Get activities for {compound}",
                "expected_intent": "activity_lookup"
            },
            {
                "query": f"What is the IC50 of {compound}?",
                "expected_intent": "activity_lookup"
            },
        ])
    
    return queries[:n]


def generate_conversion_queries(n: int) -> List[Dict[str, str]]:
    """Generate structure conversion queries."""
    queries = []
    
    for smiles in SMILES_EXAMPLES:
        queries.extend([
            {
                "query": f"Convert {smiles} to InChI",
                "expected_intent": "structure_conversion"
            },
            {
                "query": f"Convert {smiles} to InChI key",
                "expected_intent": "structure_conversion"
            },
        ])
    
    return queries[:n]


def generate_complex_queries(n: int) -> List[Dict[str, str]]:
    """Generate complex multi-step queries."""
    queries = [
        {
            "query": "Find compounds similar to aspirin and calculate their properties",
            "expected_intent": "similarity_search"
        },
        {
            "query": "Get similar compounds to CHEMBL25 with similarity > 0.8 and check Lipinski rules",
            "expected_intent": "similarity_search"
        },
        {
            "query": "Find targets for ibuprofen and get their activities",
            "expected_intent": "target_lookup"
        },
        {
            "query": "Compare properties of aspirin and ibuprofen and check druglikeness",
            "expected_intent": "comparison"
        },
    ]
    
    return queries[:n]


def generate_edge_cases(n: int) -> List[Dict[str, str]]:
    """Generate edge case and error scenarios."""
    queries = [
        {"query": "", "expected_intent": "unknown"},
        {"query": "   ", "expected_intent": "unknown"},
        {"query": "What is INVALID_CHEMBL_ID?", "expected_intent": "compound_lookup"},
        {"query": "Find similar compounds to NONEXISTENT", "expected_intent": "similarity_search"},
        {"query": "Calculate properties of INVALID_SMILES", "expected_intent": "property_calculation"},
        {"query": "What targets does FAKE_COMPOUND bind to?", "expected_intent": "target_lookup"},
        {"query": "Compare INVALID1 and INVALID2", "expected_intent": "comparison"},
        {"query": "!@#$%^&*()", "expected_intent": "unknown"},
        {"query": "SELECT * FROM compounds", "expected_intent": "unknown"},
        {"query": "a" * 1000, "expected_intent": "unknown"},  # Very long query
    ]
    
    return queries[:n]


# =============================================================================
# Main Query Generation
# =============================================================================

def generate_queries(round_num: int) -> List[Dict[str, str]]:
    """
    Generate queries for the specified test round.
    
    Args:
        round_num: Round number (1=100, 2=500, 3=2000)
        
    Returns:
        List of query dictionaries with 'query' and 'expected_intent'
    """
    if round_num == 1:
        total = 100
        distribution = {
            "compound_lookup": 15,
            "property": 15,
            "similarity": 15,
            "target": 10,
            "lipinski": 10,
            "comparison": 10,
            "substructure": 5,
            "activity": 5,
            "conversion": 5,
            "complex": 5,
            "edge_cases": 5,
        }
    elif round_num == 2:
        total = 500
        distribution = {
            "compound_lookup": 75,
            "property": 75,
            "similarity": 75,
            "target": 50,
            "lipinski": 40,
            "comparison": 40,
            "substructure": 30,
            "activity": 30,
            "conversion": 25,
            "complex": 30,
            "edge_cases": 30,
        }
    elif round_num == 3:
        total = 2000
        distribution = {
            "compound_lookup": 300,
            "property": 300,
            "similarity": 300,
            "target": 200,
            "lipinski": 150,
            "comparison": 150,
            "substructure": 120,
            "activity": 120,
            "conversion": 100,
            "complex": 150,
            "edge_cases": 110,
        }
    else:
        raise ValueError(f"Invalid round number: {round_num}")
    
    # Generate queries by category
    all_queries = []
    
    all_queries.extend(generate_compound_lookup_queries(distribution["compound_lookup"]))
    all_queries.extend(generate_property_queries(distribution["property"]))
    all_queries.extend(generate_similarity_queries(distribution["similarity"]))
    all_queries.extend(generate_target_queries(distribution["target"]))
    all_queries.extend(generate_lipinski_queries(distribution["lipinski"]))
    all_queries.extend(generate_comparison_queries(distribution["comparison"]))
    all_queries.extend(generate_substructure_queries(distribution["substructure"]))
    all_queries.extend(generate_activity_queries(distribution["activity"]))
    all_queries.extend(generate_conversion_queries(distribution["conversion"]))
    all_queries.extend(generate_complex_queries(distribution["complex"]))
    all_queries.extend(generate_edge_cases(distribution["edge_cases"]))
    
    # Shuffle to mix categories
    random.shuffle(all_queries)
    
    return all_queries[:total]


if __name__ == "__main__":
    # Test query generation
    for round_num in [1, 2, 3]:
        queries = generate_queries(round_num)
        print(f"\nRound {round_num}: Generated {len(queries)} queries")
        print(f"Sample queries:")
        for q in queries[:5]:
            print(f"  - {q['query']}")
