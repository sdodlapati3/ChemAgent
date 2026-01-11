#!/usr/bin/env python
"""
Quick test script to verify ChemAgent UI functionality.

Tests that the UI can be created without errors.
"""

import sys


def test_ui_import():
    """Test UI module import."""
    print("=" * 60)
    print("TEST 1: Import UI Module")
    print("=" * 60)
    try:
        from chemagent.ui import launch_app, create_app
        print("✓ Successfully imported launch_app and create_app")
        return True
    except Exception as e:
        print(f"✗ Failed to import: {e}")
        return False


def test_ui_creation():
    """Test that UI app can be created."""
    print("\n" + "=" * 60)
    print("TEST 2: Create Gradio App")
    print("=" * 60)
    try:
        from chemagent.ui import create_app
        
        print("Creating Gradio app...")
        app = create_app()
        print("✓ Successfully created Gradio app")
        
        # Verify app has required attributes
        assert hasattr(app, 'launch'), "App should have launch method"
        assert hasattr(app, 'queue'), "App should have queue method"
        print("✓ App has required methods")
        
        return True
    except Exception as e:
        print(f"✗ Failed to create app: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_chemagent_integration():
    """Test that UI can create ChemAgent instance."""
    print("\n" + "=" * 60)
    print("TEST 3: ChemAgent Integration")
    print("=" * 60)
    try:
        from chemagent.ui.app import ChemAgentUI
        
        print("Creating ChemAgentUI instance...")
        ui = ChemAgentUI()
        print("✓ Successfully created ChemAgentUI")
        
        # Verify components
        assert hasattr(ui, 'agent'), "UI should have agent"
        assert hasattr(ui, 'history_manager'), "UI should have history_manager"
        assert hasattr(ui, 'visualizer'), "UI should have visualizer"
        print("✓ UI has all required components")
        
        return True
    except Exception as e:
        print(f"✗ Failed integration test: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_ui_methods():
    """Test UI processing methods."""
    print("\n" + "=" * 60)
    print("TEST 4: UI Processing Methods")
    print("=" * 60)
    try:
        from chemagent.ui.app import ChemAgentUI
        
        ui = ChemAgentUI()
        
        # Test process_query method
        print("Testing process_query with simple query...")
        result = ui.process_query("Calculate properties of CCO", use_cache=False, verbose=False)
        
        # Should return tuple with 4 elements
        assert isinstance(result, tuple), "process_query should return tuple"
        assert len(result) == 4, "process_query should return 4 elements"
        
        status_html, result_text, viz_html, history = result
        
        print(f"✓ process_query returned tuple with 4 elements")
        print(f"   Status HTML length: {len(status_html)} chars")
        print(f"   Result text length: {len(result_text)} chars")
        print(f"   Visualization length: {len(viz_html)} chars")
        print(f"   History items: {len(history)}")
        
        return True
    except Exception as e:
        print(f"✗ UI methods test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("ChemAgent UI Verification")
    print("=" * 60)
    
    results = []
    
    # Run tests
    results.append(("Import UI Module", test_ui_import()))
    results.append(("Create Gradio App", test_ui_creation()))
    results.append(("ChemAgent Integration", test_chemagent_integration()))
    results.append(("UI Processing Methods", test_ui_methods()))
    
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
    
    if passed == total:
        print("\n🎉 All UI tests passed! The frontend is ready to use.")
        print("\nTo launch the UI, run:")
        print("  python -m chemagent.ui.run")
        print("or:")
        print("  python -m chemagent.ui.run --host 0.0.0.0 --port 7860")
    else:
        print("\n⚠️  Some tests failed. Check the errors above.")
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
