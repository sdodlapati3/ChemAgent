#!/usr/bin/env python3
"""Test script to simulate frontend query."""

import sys
import traceback
from chemagent import ChemAgent

def test_query(query_text):
    """Test a single query."""
    print(f"\n{'='*60}")
    print(f"Testing Query: {query_text}")
    print('='*60)
    
    try:
        agent = ChemAgent()
        print("✓ ChemAgent initialized")
        
        result = agent.query(query_text)
        print(f"\n✓ Query completed")
        print(f"  Success: {result.success}")
        print(f"  Execution Time: {result.execution_time_ms/1000:.2f}s")
        print(f"  Cached: {result.cached}")
        
        if result.error:
            print(f"\n❌ Error: {result.error}")
        else:
            print(f"\n✓ Result (first 500 chars):")
            print(result.answer[:500] if result.answer else "No result")
        
        return result
        
    except Exception as e:
        print(f"\n❌ Exception occurred:")
        print(f"  Type: {type(e).__name__}")
        print(f"  Message: {str(e)}")
        print(f"\nFull traceback:")
        traceback.print_exc()
        return None

if __name__ == "__main__":
    # Test queries
    queries = [
        "What is CHEMBL25?",
        "Calculate properties of CCO",
        "Find similar compounds to aspirin"
    ]
    
    for query in queries:
        result = test_query(query)
        if not result or result.error:
            print(f"\n⚠️  Query failed, stopping here")
            sys.exit(1)
    
    print(f"\n{'='*60}")
    print("✅ All queries completed successfully!")
    print('='*60)
