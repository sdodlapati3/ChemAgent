"""
Test script for ChemAgent FastAPI server.

Tests all API endpoints with real queries.
"""

import requests
import json
import time
from typing import Dict, Any


BASE_URL = "http://localhost:8000"


def print_response(name: str, response: requests.Response):
    """Pretty print API response"""
    print(f"\n{'='*70}")
    print(f"Test: {name}")
    print(f"{'='*70}")
    print(f"Status: {response.status_code}")
    
    try:
        data = response.json()
        print(json.dumps(data, indent=2))
    except:
        print(response.text)
    
    if response.status_code == 200:
        print("✓ SUCCESS")
    else:
        print("✗ FAILED")


def test_root():
    """Test root endpoint"""
    response = requests.get(f"{BASE_URL}/")
    print_response("Root Endpoint", response)
    return response.status_code == 200


def test_health():
    """Test health check"""
    response = requests.get(f"{BASE_URL}/health")
    print_response("Health Check", response)
    return response.status_code == 200


def test_query_compound_lookup():
    """Test natural language compound lookup"""
    payload = {
        "query": "What is CHEMBL25?",
        "use_cache": True,
        "verbose": False
    }
    response = requests.post(f"{BASE_URL}/query", json=payload)
    print_response("Query: Compound Lookup", response)
    return response.status_code == 200


def test_query_properties():
    """Test property calculation query"""
    payload = {
        "query": "Calculate properties of aspirin",
        "use_cache": True,
        "verbose": True  # Show execution details
    }
    response = requests.post(f"{BASE_URL}/query", json=payload)
    print_response("Query: Property Calculation (Verbose)", response)
    return response.status_code == 200


def test_query_similarity():
    """Test similarity search query"""
    payload = {
        "query": "Find compounds similar to CC(=O)Oc1ccccc1C(=O)O",
        "use_cache": True,
        "verbose": False
    }
    response = requests.post(f"{BASE_URL}/query", json=payload)
    print_response("Query: Similarity Search", response)
    return response.status_code == 200


def test_direct_compound_lookup():
    """Test direct compound lookup endpoint"""
    payload = {
        "identifier": "CHEMBL25",
        "use_cache": True
    }
    response = requests.post(f"{BASE_URL}/compound/lookup", json=payload)
    print_response("Direct Compound Lookup", response)
    return response.status_code == 200


def test_direct_properties():
    """Test direct properties endpoint"""
    payload = {
        "smiles": "CC(=O)Oc1ccccc1C(=O)O",
        "use_cache": True
    }
    response = requests.post(f"{BASE_URL}/compound/properties", json=payload)
    print_response("Direct Property Calculation", response)
    return response.status_code == 200


def test_direct_similarity():
    """Test direct similarity endpoint"""
    payload = {
        "smiles": "CC(=O)Oc1ccccc1C(=O)O",
        "threshold": 0.7,
        "limit": 5,
        "use_cache": True
    }
    response = requests.post(f"{BASE_URL}/compound/similar", json=payload)
    print_response("Direct Similarity Search", response)
    return response.status_code == 200


def test_get_compound():
    """Test GET compound endpoint"""
    response = requests.get(f"{BASE_URL}/compound/CHEMBL25?use_cache=true")
    print_response("GET Compound by ID", response)
    return response.status_code == 200


def test_list_tools():
    """Test tools listing endpoint"""
    response = requests.get(f"{BASE_URL}/tools")
    print_response("List Available Tools", response)
    return response.status_code == 200


def test_cache_stats():
    """Test cache statistics endpoint"""
    response = requests.get(f"{BASE_URL}/cache/stats")
    print_response("Cache Statistics", response)
    return response.status_code == 200


def test_caching_performance():
    """Test caching performance improvement"""
    print(f"\n{'='*70}")
    print("Test: Caching Performance")
    print(f"{'='*70}")
    
    payload = {
        "query": "What is CHEMBL25?",
        "use_cache": True,
        "verbose": False
    }
    
    # First request (cache miss)
    start = time.time()
    response1 = requests.post(f"{BASE_URL}/query", json=payload)
    time1 = (time.time() - start) * 1000
    
    # Second request (cache hit)
    start = time.time()
    response2 = requests.post(f"{BASE_URL}/query", json=payload)
    time2 = (time.time() - start) * 1000
    
    print(f"First request:  {time1:.0f}ms (cache miss)")
    print(f"Second request: {time2:.0f}ms (cache hit)")
    
    if time1 > time2:
        speedup = time1 / time2
        print(f"Speedup: {speedup:.1f}x faster with cache!")
        print("✓ SUCCESS - Caching is working")
        return True
    else:
        print("✗ WARNING - No significant speedup detected")
        return False


def test_error_handling():
    """Test error handling with invalid input"""
    print(f"\n{'='*70}")
    print("Test: Error Handling")
    print(f"{'='*70}")
    
    # Invalid SMILES
    payload = {
        "smiles": "",  # Empty SMILES
        "use_cache": True
    }
    response = requests.post(f"{BASE_URL}/compound/properties", json=payload)
    print(f"Invalid SMILES Status: {response.status_code}")
    
    if response.status_code == 422:  # Validation error
        print("✓ SUCCESS - Properly rejected invalid input")
        return True
    else:
        print("✗ FAILED - Should return 422 validation error")
        return False


def run_all_tests():
    """Run all API tests"""
    print(f"\n{'#'*70}")
    print("ChemAgent API Test Suite")
    print(f"{'#'*70}")
    print(f"Server: {BASE_URL}")
    print(f"Started: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    tests = [
        ("Root Endpoint", test_root),
        ("Health Check", test_health),
        ("Query: Compound Lookup", test_query_compound_lookup),
        ("Query: Property Calculation", test_query_properties),
        ("Query: Similarity Search", test_query_similarity),
        ("Direct Compound Lookup", test_direct_compound_lookup),
        ("Direct Properties", test_direct_properties),
        ("Direct Similarity", test_direct_similarity),
        ("GET Compound by ID", test_get_compound),
        ("List Tools", test_list_tools),
        ("Cache Statistics", test_cache_stats),
        ("Caching Performance", test_caching_performance),
        ("Error Handling", test_error_handling),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except requests.exceptions.ConnectionError:
            print(f"\n✗ FAILED: Cannot connect to server at {BASE_URL}")
            print("Make sure the server is running:")
            print("  crun -p ~/envs/chemagent python -m chemagent.api.server")
            return
        except Exception as e:
            print(f"\n✗ FAILED: {name} - {e}")
            results.append((name, False))
    
    # Summary
    print(f"\n{'='*70}")
    print("Test Summary")
    print(f"{'='*70}")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status}: {name}")
    
    print(f"\n{passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("\n🎉 All tests passed!")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")


if __name__ == "__main__":
    run_all_tests()
