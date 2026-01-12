#!/usr/bin/env python3
"""Test UI after fixes."""

from chemagent.ui.app import ChemAgentUI

ui = ChemAgentUI()

print("Testing UI process_query method...")
try:
    status, result, viz, history = ui.process_query(
        'What is CHEMBL25?', 
        use_cache=True, 
        verbose=False
    )
    
    print("\n✅ Query processed successfully!")
    print(f"\nStatus (first 100 chars): {status[:100]}")
    print(f"\nResult (first 300 chars):\n{result[:300]}")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
