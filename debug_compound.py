#!/usr/bin/env python3
"""Debug compound lookup to see what fields are available."""

from chemagent.tools.chembl_client import ChEMBLClient

client = ChEMBLClient()

# Test lookup by name
print("=" * 60)
print("Testing compound search: aspirin")
print("=" * 60)

results = client.search_by_name("aspirin", limit=1)

print(f"\nResult type: {type(results)}")
print(f"Number of results: {len(results) if isinstance(results, list) else 'N/A'}")

if results:
    result = results[0]
    print(f"\nFirst result type: {type(result)}")
    print(f"Result: {result}")
    
    if hasattr(result, '__dict__'):
        print(f"\nAttributes:")
        for key, value in result.__dict__.items():
            val_str = str(value)[:100] if value else "None"
            print(f"  {key}: {type(value).__name__} = {val_str}")
    elif isinstance(result, dict):
        print(f"\nDict keys: {list(result.keys())}")
        for key, value in result.items():
            val_str = str(value)[:100] if value else "None"
            print(f"  {key}: {type(value).__name__} = {val_str}")
