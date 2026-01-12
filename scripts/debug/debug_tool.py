#!/usr/bin/env python3
"""Debug tool execution to see what's actually returned."""

import json
from chemagent.core.executor import QueryExecutor, ToolRegistry
from chemagent.tools.chembl_client import ChEMBLClient
from chemagent.caching import add_caching_to_registry

# Setup
registry = ToolRegistry()
chembl = ChEMBLClient()
registry.register_tool("chembl_search_by_name", chembl.search_by_name, {
    "description": "Search for compounds by name",
    "parameters": {
        "query": {"type": "string", "description": "Search query (compound name)"}
    }
})

# Execute tool directly
print("=" * 60)
print("Testing chembl_search_by_name tool")
print("=" * 60)

result = registry.call_tool("chembl_search_by_name", {"query": "aspirin"})

print(f"\nResult type: {type(result)}")
print(f"Result: {result}")

if isinstance(result, list):
    print(f"\nList length: {len(result)}")
    if result:
        print(f"First item type: {type(result[0])}")
        print(f"First item: {result[0]}")
elif isinstance(result, dict):
    print(f"\nDict keys: {list(result.keys())}")
    for key, val in result.items():
        print(f"  {key}: {type(val).__name__}")
