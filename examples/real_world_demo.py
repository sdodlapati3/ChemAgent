#!/usr/bin/env python
"""
Real-world integration demo with actual API calls.

This demo uses the real ChEMBL, RDKit, and UniProt implementations
to demonstrate the complete ChemAgent pipeline with actual data.

Phase 2 Week 1 - Real Tool Integration
"""

import sys

from chemagent.core import (
    ExecutionStatus,
    IntentParser,
    QueryExecutor,
    QueryPlanner,
)


def print_header(title: str):
    """Print a formatted header."""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print('=' * 70)


def print_result(result):
    """Print execution result."""
    print(f"\n✓ Status: {result.status.value}")
    print(f"  Duration: {result.total_duration_ms}ms")
    print(f"  Steps: {result.steps_completed}/{len(result.step_results)}")
    
    if result.status == ExecutionStatus.FAILED:
        print(f"  ✗ Error: {result.error}")


def demo_aspirin_lookup():
    """Demo: Look up aspirin in ChEMBL."""
    print_header("Demo 1: Aspirin Lookup (Real ChEMBL API)")
    
    query = "What is CHEMBL25?"
    print(f"\nQuery: '{query}'")
    
    # Create pipeline with real tools
    parser = IntentParser()
    planner = QueryPlanner()
    executor = QueryExecutor(use_real_tools=True)
    
    # Parse → Plan → Execute
    print("\n1. Parsing query...")
    intent = parser.parse(query)
    print(f"   Intent: {intent.intent_type.value}")
    print(f"   ChEMBL ID: {intent.entities.get('chembl_id')}")
    
    print("\n2. Planning execution...")
    plan = planner.plan(intent)
    print(f"   Steps: {len(plan.steps)}")
    for step in plan.steps:
        print(f"   - {step.tool_name}({step.args})")
    
    print("\n3. Executing with real API...")
    result = executor.execute(plan)
    print_result(result)
    
    if result.status == ExecutionStatus.COMPLETED:
        output = result.final_output
        print(f"\n📊 Results:")
        print(f"   ChEMBL ID: {output.get('chembl_id')}")
        print(f"   Name: {output.get('name')}")
        print(f"   SMILES: {output.get('smiles')}")
        print(f"   MW: {output.get('molecular_weight')}")
        print(f"   ALogP: {output.get('alogp')}")


def demo_property_calculation():
    """Demo: Calculate properties of a molecule."""
    print_header("Demo 2: Property Calculation (Real RDKit)")
    
    query = "Calculate properties of CC(=O)Oc1ccccc1C(=O)O"  # Aspirin SMILES
    print(f"\nQuery: '{query}'")
    
    parser = IntentParser()
    planner = QueryPlanner()
    executor = QueryExecutor(use_real_tools=True)
    
    intent = parser.parse(query)
    print(f"\n1. Intent: {intent.intent_type.value}")
    print(f"   SMILES: {intent.entities.get('smiles')}")
    
    plan = planner.plan(intent)
    print(f"\n2. Plan: {len(plan.steps)} steps")
    
    print("\n3. Executing...")
    result = executor.execute(plan)
    print_result(result)
    
    if result.status == ExecutionStatus.COMPLETED:
        output = result.final_output
        print(f"\n📊 Molecular Properties:")
        props = output.get('properties', output)
        if isinstance(props, dict):
            for key, value in props.items():
                if key not in ['status', 'smiles']:
                    print(f"   {key}: {value}")


def demo_similarity_search():
    """Demo: Find compounds similar to aspirin."""
    print_header("Demo 3: Similarity Search (ChEMBL + RDKit)")
    
    query = "Find compounds similar to CC(=O)Oc1ccccc1C(=O)O"
    print(f"\nQuery: '{query}'")
    print("Note: This may take a few seconds as it queries ChEMBL API...")
    
    parser = IntentParser()
    planner = QueryPlanner()
    executor = QueryExecutor(use_real_tools=True)
    
    intent = parser.parse(query)
    plan = planner.plan(intent)
    
    print(f"\n1. Plan: {len(plan.steps)} steps")
    for i, step in enumerate(plan.steps):
        print(f"   Step {i+1}: {step.tool_name}")
    
    print("\n2. Executing...")
    result = executor.execute(plan)
    print_result(result)
    
    if result.status == ExecutionStatus.COMPLETED:
        output = result.final_output
        count = output.get('count', 0)
        print(f"\n📊 Found {count} similar compounds")
        
        compounds = output.get('compounds', [])[:3]  # Show first 3
        for i, compound in enumerate(compounds, 1):
            mol_id = compound.get('molecule_chembl_id')
            similarity = compound.get('similarity', 'N/A')
            print(f"   {i}. {mol_id} (similarity: {similarity})")


def demo_lipinski_check():
    """Demo: Check Lipinski Rule of Five."""
    print_header("Demo 4: Lipinski Rule Check (RDKit)")
    
    query = "Check Lipinski for CC(=O)Oc1ccccc1C(=O)O"
    print(f"\nQuery: '{query}'")
    
    parser = IntentParser()
    planner = QueryPlanner()
    executor = QueryExecutor(use_real_tools=True)
    
    intent = parser.parse(query)
    plan = planner.plan(intent)
    
    print(f"\n1. Executing Lipinski check...")
    result = executor.execute(plan)
    print_result(result)
    
    if result.status == ExecutionStatus.COMPLETED:
        output = result.final_output
        print(f"\n📊 Lipinski Rule of Five:")
        print(f"   Passes: {output.get('passes_lipinski', 'N/A')}")
        print(f"   MW: {output.get('molecular_weight')} (≤ 500)")
        print(f"   LogP: {output.get('logp')} (≤ 5)")
        print(f"   H-Donors: {output.get('h_bond_donors')} (≤ 5)")
        print(f"   H-Acceptors: {output.get('h_bond_acceptors')} (≤ 10)")


def demo_error_handling():
    """Demo: Error handling with invalid SMILES."""
    print_header("Demo 5: Error Handling")
    
    query = "Calculate properties of INVALID_SMILES"
    print(f"\nQuery: '{query}'")
    
    parser = IntentParser()
    planner = QueryPlanner()
    executor = QueryExecutor(use_real_tools=True)
    
    intent = parser.parse(query)
    plan = planner.plan(intent)
    
    print(f"\n1. Executing with invalid SMILES...")
    result = executor.execute(plan)
    print_result(result)
    
    if result.status == ExecutionStatus.FAILED:
        print(f"\n✓ Error handled gracefully!")
        print(f"   The system detected the invalid input and reported:")
        print(f"   '{result.error}'")


def demo_multi_step_pipeline():
    """Demo: Multi-step pipeline with variable resolution."""
    print_header("Demo 6: Multi-Step Pipeline (Variable Resolution)")
    
    print("\nThis demo shows how the executor chains steps together:")
    print("  Step 1: Look up CHEMBL25 → get SMILES")
    print("  Step 2: Calculate properties using that SMILES")
    print("  Step 3: Check Lipinski rules on those properties")
    
    from chemagent.core.query_planner import PlanStep, QueryPlan
    from chemagent.core import IntentType
    
    # Create a custom multi-step plan
    plan = QueryPlan(
        steps=[
            PlanStep(
                step_id=0,
                tool_name="chembl_get_compound",
                args={"chembl_id": "CHEMBL25"},
                output_name="compound"
            ),
            PlanStep(
                step_id=1,
                tool_name="rdkit_calc_properties",
                args={"smiles": "$compound.smiles"},
                depends_on=[0],
                output_name="properties"
            ),
            PlanStep(
                step_id=2,
                tool_name="rdkit_calc_lipinski",
                args={"smiles": "$compound.smiles"},
                depends_on=[0],
                output_name="lipinski"
            )
        ],
        intent_type=IntentType.PROPERTY_CALCULATION
    )
    
    executor = QueryExecutor(use_real_tools=True)
    
    print("\n1. Executing 3-step pipeline...")
    result = executor.execute(plan)
    print_result(result)
    
    if result.status == ExecutionStatus.COMPLETED:
        print(f"\n📊 Pipeline Results:")
        context = executor.get_context()
        
        # Show what each step produced
        compound = context.get('compound', {})
        print(f"\n   Step 1 (Compound Lookup):")
        print(f"   - Name: {compound.get('name')}")
        print(f"   - SMILES: {compound.get('smiles')}")
        
        properties = context.get('properties', {})
        print(f"\n   Step 2 (Properties):")
        props = properties.get('properties', properties)
        if isinstance(props, dict):
            for key, value in list(props.items())[:5]:
                if key not in ['status', 'smiles']:
                    print(f"   - {key}: {value}")
        
        lipinski = context.get('lipinski', {})
        print(f"\n   Step 3 (Lipinski):")
        print(f"   - Passes: {lipinski.get('passes_lipinski')}")
        print(f"   - MW: {lipinski.get('molecular_weight')}")


def main():
    """Run all real-world demos."""
    print("\n" + "=" * 70)
    print("  ChemAgent Real-World Integration Demo")
    print("  Phase 2 Week 1: Actual API Calls")
    print("=" * 70)
    
    print("\n⚠️  Note: These demos make real API calls to:")
    print("   - ChEMBL Web Services (public API)")
    print("   - RDKit (local chemistry calculations)")
    print("   - UniProt (public API)")
    print("\n   Some demos may take a few seconds to complete.")
    
    try:
        demo_aspirin_lookup()
        demo_property_calculation()
        demo_similarity_search()
        demo_lipinski_check()
        demo_error_handling()
        demo_multi_step_pipeline()
        
        print("\n" + "=" * 70)
        print("  ✓ All demos completed!")
        print("=" * 70)
        
        print("\n🎉 The complete ChemAgent pipeline is working with real APIs!")
        print("\nWhat we demonstrated:")
        print("  ✓ ChEMBL compound lookup")
        print("  ✓ RDKit property calculations")
        print("  ✓ Similarity searching")
        print("  ✓ Lipinski rule checking")
        print("  ✓ Error handling")
        print("  ✓ Multi-step pipelines with variable resolution")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n✗ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
