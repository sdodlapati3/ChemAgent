#!/usr/bin/env python3
"""Test UniProt query fix."""

import sys
sys.path.insert(0, '/home/sdodl001_odu_edu/ChemAgent/src')

from chemagent.tools.uniprot_client import UniProtClient

print("Testing UniProt client with empty query...")
client = UniProtClient()

# Test 1: Empty query
print("\n1. Testing empty query:")
result = client.search_proteins("")
print(f"   Result: {result}")
print(f"   Type: {type(result)}")
print(f"   Length: {len(result)}")

# Test 2: Whitespace only
print("\n2. Testing whitespace query:")
result = client.search_proteins("   ")
print(f"   Result: {result}")
print(f"   Length: {len(result)}")

# Test 3: Valid query
print("\n3. Testing valid query (cyclooxygenase):")
result = client.search_proteins("cyclooxygenase", limit=2)
print(f"   Found {len(result)} results")
if result:
    print(f"   First result: {result[0].protein_name}")

print("\n✅ All tests completed!")
