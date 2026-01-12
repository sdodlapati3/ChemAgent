#!/usr/bin/env python3
"""Debug similarity search query planning."""

import json
from chemagent.core.intent_parser import IntentParser
from chemagent.core.query_planner import QueryPlanner
from chemagent.core.executor import ToolRegistry

# Initialize
parser = IntentParser()
planner = QueryPlanner()

# Parse intent
query = "Find similar compounds to aspirin"
print("=" * 60)
print(f"Query: {query}")
print("=" * 60)

intent = parser.parse(query)
print(f"\nIntent Type: {intent.intent_type}")
print(f"Entities: {intent.entities}")
print(f"Confidence: {intent.confidence}")

# Create plan
plan = planner.plan(intent)
print(f"\nPlan Steps: {len(plan.steps)}")
for i, step in enumerate(plan.steps, 1):
    print(f"\n--- Step {i} ---")
    print(f"Tool: {step.tool_name}")
    print(f"Arguments: {json.dumps(step.args, indent=2)}")
    print(f"Output Name: {step.output_name}")
    print(f"Depends On: {step.depends_on}")
