#!/usr/bin/env python
"""
Multi-Agent Orchestration Demo

Demonstrates how the CoordinatorAgent orchestrates specialist agents
to handle complex pharmaceutical research queries.

Architecture:
    Coordinator (Nemotron/large model) - Orchestrates
    ├── CompoundAgent - Search, lookup, similarity
    ├── ActivityAgent - IC50, Ki, targets
    ├── PropertyAgent - Properties, Lipinski
    └── TargetAgent - Proteins, UniProt

Usage:
    python examples/multi_agent_demo.py
"""

import json
import time
from typing import Dict, Any

# Setup path
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from chemagent.core.executor import ToolRegistry
from chemagent.core.multi_agent import (
    CoordinatorAgent,
    CompoundAgent,
    ActivityAgent,
    PropertyAgent,
    TargetAgent,
    create_multi_agent_system,
    ModelConfig,
    AgentRole,
)


def print_header(text: str):
    """Print a formatted header."""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)


def print_result(result: Dict[str, Any]):
    """Print query result."""
    print(f"\n✅ Success: {result.get('success', False)}")
    print(f"🔄 Orchestration: {result.get('orchestration', 'unknown')}")
    print(f"📊 Tasks Executed: {result.get('tasks_executed', 0)}")
    print(f"🤖 Agents Used: {result.get('agents_used', [])}")
    print(f"⏱️  Execution Time: {result.get('execution_time_ms', 0):.0f}ms")
    
    if result.get('answer'):
        print("\n📝 Answer:")
        print("-" * 50)
        print(result['answer'][:1000])  # Truncate long answers
        if len(result.get('answer', '')) > 1000:
            print("... [truncated]")


def demo_individual_agents():
    """Demo each specialist agent individually."""
    print_header("INDIVIDUAL SPECIALIST AGENTS DEMO")
    
    # Create tool registry
    registry = ToolRegistry(use_real_tools=True)
    
    # Demo CompoundAgent
    print("\n🧪 CompoundAgent - Compound search specialist")
    compound_agent = CompoundAgent(tool_registry=registry)
    print(f"  Role: {compound_agent.role.value}")
    print(f"  Tools: {list(compound_agent.tools.keys())}")
    print(f"  Model: {compound_agent.model}")
    
    # Demo ActivityAgent
    print("\n📈 ActivityAgent - Bioactivity specialist")
    activity_agent = ActivityAgent(tool_registry=registry)
    print(f"  Role: {activity_agent.role.value}")
    print(f"  Tools: {list(activity_agent.tools.keys())}")
    
    # Demo PropertyAgent
    print("\n⚗️  PropertyAgent - Property calculation specialist")
    property_agent = PropertyAgent(tool_registry=registry)
    print(f"  Role: {property_agent.role.value}")
    print(f"  Tools: {list(property_agent.tools.keys())}")
    
    # Demo TargetAgent
    print("\n🎯 TargetAgent - Target resolution specialist")
    target_agent = TargetAgent(tool_registry=registry)
    print(f"  Role: {target_agent.role.value}")
    print(f"  Tools: {list(target_agent.tools.keys())}")


def demo_coordinator():
    """Demo the Coordinator agent orchestrating specialists."""
    print_header("COORDINATOR ORCHESTRATION DEMO")
    
    # Show model configuration
    print("\n📋 Model Configuration:")
    print(f"  Coordinator: {ModelConfig.get_coordinator_model()}")
    print(f"  Specialists: {ModelConfig.get_specialist_model()}")
    
    # Create multi-agent system
    registry = ToolRegistry(use_real_tools=True)
    coordinator = create_multi_agent_system(tool_registry=registry)
    
    print(f"\n🤖 Coordinator initialized")
    print(f"  Specialists: {[r.value for r in coordinator.specialists.keys()]}")
    
    # Test queries
    queries = [
        "What is aspirin?",
        "Find compounds similar to ibuprofen",
        "What are the targets of CHEMBL25?",
    ]
    
    for query in queries:
        print_header(f"Query: {query}")
        
        start = time.time()
        result = coordinator.process(query)
        elapsed = (time.time() - start) * 1000
        
        print_result(result)
    
    # Show final stats
    print_header("COORDINATOR STATISTICS")
    stats = coordinator.get_stats()
    print(json.dumps(stats, indent=2))


def demo_complex_query():
    """Demo a complex multi-step query."""
    print_header("COMPLEX MULTI-STEP QUERY DEMO")
    
    registry = ToolRegistry(use_real_tools=True)
    coordinator = create_multi_agent_system(tool_registry=registry)
    
    # Complex query that requires multiple agents
    query = "Find compounds similar to aspirin and compare their IC50 values against COX-2"
    
    print(f"\n🔍 Complex Query: {query}")
    print("\nThis query requires:")
    print("  1. CompoundAgent - Find aspirin and similar compounds")
    print("  2. ActivityAgent - Get IC50 data for COX-2")
    print("  3. Coordinator - Synthesize results")
    
    result = coordinator.process(query)
    print_result(result)


def main():
    """Run all demos."""
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║                   ChemAgent Multi-Agent Demo                         ║
║                                                                       ║
║  Architecture: Coordinator → Specialist Agents → Tools               ║
╚══════════════════════════════════════════════════════════════════════╝
    """)
    
    # Run demos
    demo_individual_agents()
    demo_coordinator()
    # demo_complex_query()  # Uncomment for complex query demo
    
    print_header("DEMO COMPLETE")
    print("\nTo enable multi-agent via API:")
    print("  export CHEMAGENT_USE_MULTI_AGENT=true")
    print("  ./scripts/server.sh restart 8000")
    print("  curl -X POST http://localhost:8000/query/multi-agent \\")
    print('       -H "Content-Type: application/json" \\')
    print('       -d \'{"query": "What is aspirin?", "verbose": true}\'')


if __name__ == "__main__":
    main()
