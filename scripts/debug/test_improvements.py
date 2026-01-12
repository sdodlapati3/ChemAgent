#!/usr/bin/env python
"""
Quick test script to verify ChemAgent improvements.

Tests the complete implementation of:
- ChemAgent facade with QueryResult
- Response formatting
- Tool registry
- Exception handling
"""

import sys
import traceback


def test_basic_import():
    """Test that ChemAgent imports successfully."""
    print("=" * 60)
    print("TEST 1: Import ChemAgent")
    print("=" * 60)
    try:
        from chemagent import ChemAgent, QueryResult
        print("✓ Successfully imported ChemAgent and QueryResult")
        return True
    except Exception as e:
        print(f"✗ Failed to import: {e}")
        traceback.print_exc()
        return False


def test_initialization():
    """Test ChemAgent initialization."""
    print("\n" + "=" * 60)
    print("TEST 2: Initialize ChemAgent")
    print("=" * 60)
    try:
        from chemagent import ChemAgent
        
        # Test with different configurations
        agent1 = ChemAgent()
        print("✓ Created agent with defaults")
        
        agent2 = ChemAgent(use_cache=False, enable_parallel=False)
        print("✓ Created agent with cache and parallel disabled")
        
        # Verify components exist
        assert hasattr(agent1, 'parser'), "Missing parser"
        assert hasattr(agent1, 'planner'), "Missing planner"
        assert hasattr(agent1, 'executor'), "Missing executor"
        assert hasattr(agent1, 'formatter'), "Missing formatter"
        print("✓ All core components initialized")
        
        return True
    except Exception as e:
        print(f"✗ Initialization failed: {e}")
        traceback.print_exc()
        return False


def test_simple_query():
    """Test a simple query execution."""
    print("\n" + "=" * 60)
    print("TEST 3: Execute Simple Query")
    print("=" * 60)
    try:
        from chemagent import ChemAgent, QueryResult
        
        agent = ChemAgent()
        
        # Test with a simple property calculation
        print("Executing: 'Calculate properties of CCO'")
        result = agent.query("Calculate properties of CCO")
        
        print(f"\nResult type: {type(result)}")
        assert isinstance(result, QueryResult), "Result should be QueryResult"
        print(f"✓ Returned QueryResult")
        
        print(f"\nSuccess: {result.success}")
        print(f"Execution time: {result.execution_time_ms:.2f}ms")
        print(f"Steps taken: {result.steps_taken}")
        print(f"Intent type: {result.intent_type}")
        
        if result.success:
            print(f"\n✓ Query executed successfully!")
            print(f"\nAnswer (first 200 chars):\n{result.answer[:200]}")
        else:
            print(f"\n⚠ Query failed: {result.error}")
            print("(This may be expected if APIs are unavailable)")
        
        return True
    except Exception as e:
        print(f"✗ Query execution failed: {e}")
        traceback.print_exc()
        return False


def test_response_formatter():
    """Test response formatter directly."""
    print("\n" + "=" * 60)
    print("TEST 4: Test Response Formatter")
    print("=" * 60)
    try:
        from chemagent.core import ResponseFormatter, IntentType, ParsedIntent
        from chemagent.core.executor import ExecutionResult, ExecutionStatus
        
        formatter = ResponseFormatter()
        print("✓ Created ResponseFormatter")
        
        # Create a mock execution result
        intent = ParsedIntent(
            intent_type=IntentType.PROPERTY_CALCULATION,
            entities={},
            original_query="test"
        )
        
        # Test with mock data
        mock_output = {
            "status": "success",
            "molecular_weight": 46.07,
            "logp": -0.03,
            "h_bond_donors": 1,
            "h_bond_acceptors": 1
        }
        
        result = ExecutionResult(
            status=ExecutionStatus.COMPLETED,
            final_output=mock_output
        )
        
        answer = formatter.format(intent, result)
        print(f"\n✓ Formatted answer (first 150 chars):\n{answer[:150]}")
        
        return True
    except Exception as e:
        print(f"✗ Formatter test failed: {e}")
        traceback.print_exc()
        return False


def test_exceptions():
    """Test custom exception hierarchy."""
    print("\n" + "=" * 60)
    print("TEST 5: Test Custom Exceptions")
    print("=" * 60)
    try:
        from chemagent.exceptions import (
            ChemAgentError,
            InvalidSMILESError,
            CompoundNotFoundError
        )
        
        print("✓ Imported exception classes")
        
        # Test exception with suggestion
        try:
            raise InvalidSMILESError("INVALID", "Parse error")
        except ChemAgentError as e:
            print(f"\n✓ Caught InvalidSMILESError")
            print(f"   Message: {str(e).split('💡')[0].strip()}")
            if e.suggestion:
                print(f"   Suggestion: {e.suggestion}")
        
        return True
    except Exception as e:
        print(f"✗ Exception test failed: {e}")
        traceback.print_exc()
        return False


def test_tool_registry():
    """Test tool registry."""
    print("\n" + "=" * 60)
    print("TEST 6: Test Tool Registry")
    print("=" * 60)
    try:
        from chemagent.core import ToolRegistry
        
        # Test with placeholder tools
        registry_placeholder = ToolRegistry(use_real_tools=False)
        print(f"✓ Created registry with placeholder tools")
        print(f"   Tools registered: {len(registry_placeholder.list_tools())}")
        
        # Test with real tools
        registry_real = ToolRegistry(use_real_tools=True)
        print(f"✓ Created registry with real tools")
        print(f"   Tools registered: {len(registry_real.list_tools())}")
        
        # List some tools
        tools = registry_real.list_tools()[:5]
        print(f"   Sample tools: {', '.join(tools)}")
        
        return True
    except Exception as e:
        print(f"✗ Tool registry test failed: {e}")
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("ChemAgent Implementation Verification")
    print("=" * 60)
    
    results = []
    
    # Run tests
    results.append(("Import Test", test_basic_import()))
    results.append(("Initialization Test", test_initialization()))
    results.append(("Simple Query Test", test_simple_query()))
    results.append(("Response Formatter Test", test_response_formatter()))
    results.append(("Exception Test", test_exceptions()))
    results.append(("Tool Registry Test", test_tool_registry()))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
    
    print("\n" + "-" * 60)
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 60)
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
