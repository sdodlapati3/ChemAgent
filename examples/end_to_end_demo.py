#!/usr/bin/env python
"""
ChemAgent End-to-End Demo

Demonstrates the complete pipeline: query → parse → plan → execute

This example shows how to use ChemAgent to process natural language
queries about pharmaceutical compounds and convert them into executable
analysis plans.

Phase 1 Week 3 (Days 10-12) - Execution Engine Demo
"""

from chemagent.core import (
    ExecutionStatus,
    IntentParser,
    QueryExecutor,
    QueryPlanner,
)


def print_separator(title: str = ""):
    """Print a nice separator."""
    if title:
        print(f"\n{'=' * 60}")
        print(f"  {title}")
        print('=' * 60)
    else:
        print('-' * 60)


def demo_compound_lookup():
    """Demo: Looking up a compound by name."""
    print_separator("DEMO 1: Compound Lookup")
    
    # User query
    query = "What is CHEMBL25?"
    print(f"Query: {query}")
    
    # 1. Parse
    parser = IntentParser()
    intent = parser.parse(query)
    print(f"\n1. Parsed Intent:")
    print(f"   Type: {intent.intent_type.value}")
    print(f"   Entities: {intent.entities}")
    
    # 2. Plan
    planner = QueryPlanner()
    plan = planner.plan(intent)
    print(f"\n2. Generated Plan:")
    print(f"   Steps: {len(plan.steps)}")
    for step in plan.steps:
        print(f"   - Step {step.step_id}: {step.tool_name}")
        print(f"     Args: {step.args}")
        print(f"     Output: ${step.output_name}")
    
    # 3. Execute
    executor = QueryExecutor()
    result = executor.execute(plan)
    print(f"\n3. Execution Result:")
    print(f"   Status: {result.status.value}")
    print(f"   Steps Completed: {result.steps_completed}")
    print(f"   Duration: {result.total_duration_ms}ms")
    
    if result.status == ExecutionStatus.COMPLETED:
        print(f"   Final Output: {result.final_output}")
    else:
        print(f"   Error: {result.error}")


def demo_property_calculation():
    """Demo: Calculating molecular properties."""
    print_separator("DEMO 2: Property Calculation")
    
    query = "Calculate properties of CC(=O)O"
    print(f"Query: {query}")
    
    # Parse → Plan → Execute
    parser = IntentParser()
    planner = QueryPlanner()
    executor = QueryExecutor()
    
    intent = parser.parse(query)
    print(f"\n1. Intent Type: {intent.intent_type.value}")
    print(f"   SMILES: {intent.entities.get('smiles')}")
    
    plan = planner.plan(intent)
    print(f"\n2. Plan: {len(plan.steps)} steps")
    for step in plan.steps:
        print(f"   - {step.tool_name} → ${step.output_name}")
    
    result = executor.execute(plan)
    print(f"\n3. Result: {result.status.value}")
    print(f"   Duration: {result.total_duration_ms}ms")
    
    # Show each step's result
    for step_result in result.step_results:
        print(f"\n   Step {step_result.step_id}:")
        print(f"   - Status: {step_result.status.value}")
        print(f"   - Duration: {step_result.duration_ms}ms")
        if step_result.status == ExecutionStatus.COMPLETED:
            print(f"   - Output: {step_result.output}")


def demo_similarity_search():
    """Demo: Finding similar compounds."""
    print_separator("DEMO 3: Similarity Search")
    
    query = "Find compounds similar to aspirin with threshold 0.8"
    print(f"Query: {query}")
    
    parser = IntentParser()
    planner = QueryPlanner()
    executor = QueryExecutor()
    
    intent = parser.parse(query)
    print(f"\n1. Parsed Intent:")
    print(f"   Type: {intent.intent_type.value}")
    print(f"   Entities: {intent.entities}")
    
    plan = planner.plan(intent)
    print(f"\n2. Query Plan:")
    print(f"   Total steps: {len(plan.steps)}")
    print(f"   Estimated time: {plan.estimated_time_ms}ms")
    
    # Show dependencies
    for step in plan.steps:
        deps = f" (depends on: {step.depends_on})" if step.depends_on else ""
        print(f"   - Step {step.step_id}: {step.tool_name}{deps}")
    
    result = executor.execute(plan)
    print(f"\n3. Execution:")
    print(f"   Status: {result.status.value}")
    print(f"   Steps: {result.steps_completed}/{len(plan.steps)}")
    print(f"   Duration: {result.total_duration_ms}ms")


def demo_target_activity():
    """Demo: Finding compound activity against target."""
    print_separator("DEMO 4: Target Activity Lookup")
    
    query = "What is the activity of aspirin against COX-2?"
    print(f"Query: {query}")
    
    parser = IntentParser()
    planner = QueryPlanner()
    executor = QueryExecutor()
    
    intent = parser.parse(query)
    plan = planner.plan(intent)
    
    print(f"\n1. Intent: {intent.intent_type.value}")
    print(f"   Compound: {intent.entities.get('compound')}")
    print(f"   Target: {intent.entities.get('target')}")
    
    print(f"\n2. Plan: {len(plan.steps)} steps")
    
    result = executor.execute(plan)
    print(f"\n3. Result: {result.status.value}")
    
    # Show the execution context (stored outputs)
    context = executor.get_context()
    print(f"\n   Context Variables:")
    for var_name, value in context.items():
        print(f"   - ${var_name}: {type(value).__name__}")


def demo_error_handling():
    """Demo: Error handling with invalid input."""
    print_separator("DEMO 5: Error Handling")
    
    query = "Find compounds with invalid_smiles_xyz"
    print(f"Query: {query}")
    
    parser = IntentParser()
    planner = QueryPlanner()
    executor = QueryExecutor()
    
    intent = parser.parse(query)
    print(f"\n1. Parsed (best effort): {intent.intent_type.value}")
    
    plan = planner.plan(intent)
    print(f"2. Plan generated: {len(plan.steps)} steps")
    
    result = executor.execute(plan)
    print(f"\n3. Execution:")
    print(f"   Status: {result.status.value}")
    
    if result.status == ExecutionStatus.FAILED:
        print(f"   Error: {result.error}")
        print(f"   Steps completed before failure: {result.steps_completed}")


def demo_variable_resolution():
    """Demo: Variable resolution between steps."""
    print_separator("DEMO 6: Variable Resolution")
    
    print("Demonstrating how steps share data via variables:")
    print("  Step 1: Look up 'aspirin' → $compound")
    print("  Step 2: Use $compound.smiles for properties")
    print("  Step 3: Use properties for analysis")
    
    # Create a simple 2-step plan manually to show variable resolution
    from chemagent.core.query_planner import PlanStep, QueryPlan
    from chemagent.core import IntentType
    
    plan = QueryPlan(
        steps=[
            PlanStep(
                step_id=0,
                tool_name="chembl_search_by_name",
                args={"query": "aspirin"},
                output_name="compound"
            ),
            PlanStep(
                step_id=1,
                tool_name="rdkit_calc_properties",
                args={"smiles": "$compound.smiles"},  # Variable reference!
                depends_on=[0],
                output_name="properties"
            )
        ],
        intent_type=IntentType.PROPERTY_CALCULATION
    )
    
    print(f"\n1. Plan Structure:")
    for step in plan.steps:
        print(f"   Step {step.step_id}: {step.tool_name}")
        print(f"   Args: {step.args}")
        if step.depends_on:
            print(f"   Depends on: {step.depends_on}")
    
    executor = QueryExecutor()
    result = executor.execute(plan)
    
    print(f"\n2. Execution:")
    print(f"   Status: {result.status.value}")
    
    print(f"\n3. Variable Resolution:")
    context = executor.get_context()
    for var_name in context:
        print(f"   - ${var_name} stored successfully")


def demo_statistics():
    """Show statistics about the ChemAgent system."""
    print_separator("SYSTEM STATISTICS")
    
    from chemagent.core import ToolRegistry
    
    # Tool registry
    registry = ToolRegistry()
    tools = registry.list_tools()
    print(f"\nAvailable Tools: {len(tools)}")
    print("\nChEMBL Tools:")
    for tool in [t for t in tools if 'chembl' in t]:
        print(f"  - {tool}")
    print("\nRDKit Tools:")
    for tool in [t for t in tools if 'rdkit' in t]:
        print(f"  - {tool}")
    print("\nOther Tools:")
    for tool in [t for t in tools if 'chembl' not in t and 'rdkit' not in t]:
        print(f"  - {tool}")
    
    # Intent types
    from chemagent.core import IntentType
    intents = [i for i in IntentType]
    print(f"\nSupported Intent Types: {len(intents)}")
    for intent in intents:
        print(f"  - {intent.value}")


def main():
    """Run all demos."""
    print("\n" + "=" * 60)
    print("  ChemAgent End-to-End Demo")
    print("  Phase 1 Week 3: Query Execution Engine")
    print("=" * 60)
    print("\nThis demo shows the complete pipeline:")
    print("  1. Natural Language Query")
    print("  2. Intent Parsing (NLU)")
    print("  3. Query Planning (multi-step plans)")
    print("  4. Execution (step-by-step)")
    print("\nNote: Using placeholder tools for this demo")
    print("      (Real API clients will be integrated later)")
    
    # Run demos
    demo_compound_lookup()
    demo_property_calculation()
    demo_similarity_search()
    demo_target_activity()
    demo_error_handling()
    demo_variable_resolution()
    demo_statistics()
    
    print_separator()
    print("\n✓ All demos completed successfully!")
    print("\nNext Steps:")
    print("  - Integrate real tool implementations")
    print("  - Add caching layer")
    print("  - Implement parallel execution")
    print("  - Add result formatting")
    print("  - Build user interface\n")


if __name__ == "__main__":
    main()
