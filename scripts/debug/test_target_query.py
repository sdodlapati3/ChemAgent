#!/usr/bin/env python3
"""Test target lookup with fix."""

import sys
sys.path.insert(0, '/home/sdodl001_odu_edu/ChemAgent/src')

from chemagent import ChemAgent

agent = ChemAgent()

print("Testing target lookup query...")

# This should now handle gracefully even if entity extraction fails
result = agent.query("What are the targets?")

print(f"\n✅ Query completed")
print(f"Success: {result.success}")
print(f"Error: {result.error}")
print(f"Answer (first 300 chars): {result.answer[:300]}")
