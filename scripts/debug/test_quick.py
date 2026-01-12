#!/usr/bin/env python3
"""Quick test of UI query processing."""

import sys
sys.path.insert(0, '/home/sdodl001_odu_edu/ChemAgent/src')

from chemagent import ChemAgent

print("Testing ChemAgent.query()...")
agent = ChemAgent()

try:
    result = agent.query('What is CHEMBL25?')
    
    print(f"\n✅ Success: {result.success}")
    print(f"Intent: {result.intent_type}")
    print(f"Time: {result.execution_time_ms:.2f}ms")
    print(f"\nAnswer (first 200 chars):\n{result.answer[:200]}...")
    
    # Test that raw_output is accessible (needed for visualizer)
    print(f"\nRaw output type: {type(result.raw_output)}")
    print(f"Has raw_output: {result.raw_output is not None}")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
