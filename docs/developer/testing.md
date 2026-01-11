# Testing Guide

Comprehensive guide for testing ChemAgent.

---

## Table of Contents

1. [Test Structure](#test-structure)
2. [Running Tests](#running-tests)
3. [Writing Tests](#writing-tests)
4. [Test Coverage](#test-coverage)
5. [Integration Testing](#integration-testing)
6. [Performance Testing](#performance-testing)

---

## Test Structure

```
tests/
├── conftest.py                    # Pytest configuration and fixtures
├── test_api.py                    # API endpoint tests
├── test_monitoring.py             # Monitoring and metrics tests
├── test_parallel_execution.py     # Parallel execution tests
├── test_evaluation.py             # Evaluation framework tests
├── unit/                          # Unit tests
│   ├── test_caching.py           # Cache functionality
│   ├── test_cli.py               # CLI interface
│   ├── test_config.py            # Configuration
│   ├── test_executor.py          # Query execution
│   ├── test_intent_parser.py    # Intent parsing
│   ├── test_parallel.py         # Parallel processing
│   ├── test_query_planner.py    # Query planning
│   └── test_database_clients.py # Database client tests
├── integration/                   # Integration tests
│   ├── test_full_pipeline.py    # End-to-end workflows
│   ├── test_chembl_integration.py # ChEMBL API
│   ├── test_uniprot_integration.py # UniProt API
│   └── test_bindingdb_integration.py # BindingDB integration
└── data/                         # Test data
    └── golden_queries.json       # Golden query dataset
```

---

## Running Tests

### Run All Tests

```bash
# Run full test suite
pytest tests/ -v

# With coverage
pytest tests/ --cov=chemagent --cov-report=html
```

### Run Specific Test Categories

```bash
# Unit tests only
pytest tests/unit/ -v

# Integration tests only (requires internet)
pytest tests/integration/ -v

# Specific test file
pytest tests/unit/test_caching.py -v

# Specific test function
pytest tests/unit/test_caching.py::test_cache_hit -v
```

### Run Tests by Marker

```bash
# Fast tests only
pytest -m fast

# Slow tests only
pytest -m slow

# Skip integration tests
pytest -m "not integration"

# Run only database tests
pytest -m database
```

### Parallel Test Execution

```bash
# Install pytest-xdist
pip install pytest-xdist

# Run tests in parallel
pytest tests/ -n auto  # Auto-detect CPU count
pytest tests/ -n 4     # Use 4 workers
```

---

## Writing Tests

### Unit Test Example

```python
# tests/unit/test_my_feature.py
import pytest
from chemagent.core.my_module import MyClass

class TestMyFeature:
    """Test suite for MyClass"""
    
    def test_basic_functionality(self):
        """Test basic feature works"""
        obj = MyClass()
        result = obj.do_something("input")
        
        assert result is not None
        assert result == "expected_output"
    
    def test_error_handling(self):
        """Test error handling"""
        obj = MyClass()
        
        with pytest.raises(ValueError):
            obj.do_something(None)
    
    @pytest.mark.parametrize("input,expected", [
        ("test1", "output1"),
        ("test2", "output2"),
        ("test3", "output3"),
    ])
    def test_multiple_inputs(self, input, expected):
        """Test with multiple inputs"""
        obj = MyClass()
        result = obj.do_something(input)
        assert result == expected
```

### Integration Test Example

```python
# tests/integration/test_my_integration.py
import pytest
from chemagent import ChemAgent

@pytest.mark.integration
class TestChemAgentIntegration:
    """Integration tests requiring external APIs"""
    
    @pytest.fixture
    def agent(self):
        """Create agent for testing"""
        return ChemAgent(use_cache=False)
    
    def test_compound_lookup(self, agent):
        """Test compound lookup workflow"""
        result = agent.query("What is aspirin?")
        
        assert result.success
        assert "CHEMBL25" in result.answer
        assert result.execution_time_ms > 0
    
    @pytest.mark.slow
    def test_similarity_search(self, agent):
        """Test similarity search (slow)"""
        result = agent.query("Find compounds similar to aspirin")
        
        assert result.success
        assert "similar" in result.answer.lower()
```

### Using Fixtures

```python
# tests/conftest.py
import pytest
from chemagent import ChemAgent
from chemagent.clients import ChEMBLClient

@pytest.fixture
def agent():
    """Provide ChemAgent instance"""
    return ChemAgent(use_cache=False)

@pytest.fixture
def chembl_client():
    """Provide ChEMBL client"""
    return ChEMBLClient()

@pytest.fixture
def sample_smiles():
    """Provide sample SMILES strings"""
    return {
        "aspirin": "CC(=O)Oc1ccccc1C(=O)O",
        "ibuprofen": "CC(C)Cc1ccc(C(C)C(=O)O)cc1",
        "metformin": "CN(C)C(=N)NC(=N)N"
    }

# Use fixtures in tests
def test_with_fixtures(agent, sample_smiles):
    """Test using multiple fixtures"""
    result = agent.query(f"What is {sample_smiles['aspirin']}?")
    assert result.success
```

### Mocking External APIs

```python
# tests/unit/test_with_mocking.py
from unittest.mock import patch, MagicMock
import pytest

@patch('chemagent.clients.chembl_client.requests.get')
def test_chembl_lookup_with_mock(mock_get):
    """Test ChEMBL lookup with mocked API"""
    
    # Setup mock response
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "molecule_chembl_id": "CHEMBL25",
        "pref_name": "ASPIRIN"
    }
    mock_response.status_code = 200
    mock_get.return_value = mock_response
    
    # Test
    from chemagent.clients import ChEMBLClient
    client = ChEMBLClient()
    result = client.get_compound_by_id("CHEMBL25")
    
    assert result["molecule_chembl_id"] == "CHEMBL25"
    mock_get.assert_called_once()
```

---

## Test Coverage

### Generate Coverage Report

```bash
# Run tests with coverage
pytest tests/ --cov=chemagent --cov-report=html --cov-report=term

# View HTML report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### Coverage Requirements

- **Minimum Coverage**: 85% overall
- **Core Modules**: 90%+ coverage required
- **Utility Modules**: 80%+ coverage acceptable

### Check Coverage Locally

```bash
# Quick coverage check
pytest tests/ --cov=chemagent --cov-report=term-missing

# Shows which lines are not covered
```

---

## Integration Testing

### Setup for Integration Tests

```python
# tests/integration/conftest.py
import pytest

@pytest.fixture(scope="session")
def check_internet_connection():
    """Verify internet connectivity"""
    import requests
    try:
        requests.get("https://www.google.com", timeout=5)
        return True
    except:
        pytest.skip("No internet connection")

@pytest.fixture(scope="session")
def check_chembl_api():
    """Verify ChEMBL API is accessible"""
    import requests
    try:
        r = requests.get(
            "https://www.ebi.ac.uk/chembl/api/data/status",
            timeout=10
        )
        if r.status_code != 200:
            pytest.skip("ChEMBL API not accessible")
    except:
        pytest.skip("ChEMBL API not accessible")
```

### Integration Test Best Practices

1. **Use Markers**: Mark integration tests appropriately
2. **Check Connectivity**: Verify API availability before testing
3. **Use Timeouts**: Set reasonable timeouts for API calls
4. **Cache Responses**: Use VCR.py to record API responses
5. **Test Error Handling**: Test API failures and timeouts

### Using VCR.py for API Testing

```bash
# Install VCR.py
pip install vcrpy
```

```python
# tests/integration/test_with_vcr.py
import pytest
import vcr

@pytest.fixture
def vcr_config():
    return {
        "cassette_library_dir": "tests/cassettes",
        "record_mode": "once"  # Record once, then replay
    }

@vcr.use_cassette("tests/cassettes/chembl_lookup.yaml")
def test_chembl_lookup():
    """Test ChEMBL lookup (cached)"""
    from chemagent.clients import ChEMBLClient
    
    client = ChEMBLClient()
    result = client.get_compound_by_id("CHEMBL25")
    
    assert result["molecule_chembl_id"] == "CHEMBL25"
```

---

## Performance Testing

### Benchmark Tests

```python
# tests/performance/test_benchmarks.py
import pytest
import time

@pytest.mark.benchmark
class TestPerformance:
    """Performance benchmarks"""
    
    def test_query_performance(self, benchmark):
        """Benchmark query execution"""
        from chemagent import ChemAgent
        agent = ChemAgent()
        
        result = benchmark(agent.query, "What is aspirin?")
        
        assert result.success
        assert result.execution_time_ms < 5000  # Should be under 5s
    
    def test_cache_performance(self):
        """Test cache improves performance"""
        from chemagent import ChemAgent
        
        agent = ChemAgent(use_cache=True)
        query = "What is aspirin?"
        
        # First query (no cache)
        start = time.time()
        result1 = agent.query(query)
        time1 = time.time() - start
        
        # Second query (cached)
        start = time.time()
        result2 = agent.query(query)
        time2 = time.time() - start
        
        assert time2 < time1 * 0.1  # Cached should be 10x+ faster
```

### Load Testing

```python
# tests/performance/test_load.py
import pytest
from concurrent.futures import ThreadPoolExecutor

@pytest.mark.load
def test_concurrent_queries():
    """Test handling concurrent queries"""
    from chemagent import ChemAgent
    
    agent = ChemAgent()
    queries = [f"What is CHEMBL{i}?" for i in range(25, 50)]
    
    def run_query(query):
        return agent.query(query)
    
    # Run 25 queries concurrently
    with ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(run_query, queries))
    
    # Verify all succeeded
    assert all(r.success for r in results)
```

---

## Continuous Integration

### GitHub Actions Workflow

```yaml
# .github/workflows/tests.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'
    
    - name: Install dependencies
      run: |
        pip install -e ".[dev]"
    
    - name: Run unit tests
      run: |
        pytest tests/unit/ -v --cov=chemagent
    
    - name: Run integration tests
      run: |
        pytest tests/integration/ -v
      env:
        RUN_INTEGRATION_TESTS: true
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
```

---

## Test Markers

Define custom markers in `pytest.ini`:

```ini
[pytest]
markers =
    fast: Fast tests (< 1s)
    slow: Slow tests (> 5s)
    integration: Integration tests (require internet)
    unit: Unit tests (no external dependencies)
    database: Database-related tests
    benchmark: Performance benchmarks
    load: Load testing
```

Use markers in tests:

```python
@pytest.mark.fast
def test_quick_operation():
    """Fast test"""
    pass

@pytest.mark.slow
@pytest.mark.integration
def test_complex_workflow():
    """Slow integration test"""
    pass
```

---

## Debugging Tests

### Run with Debugger

```bash
# Drop into debugger on failure
pytest tests/ --pdb

# Drop into debugger on first failure
pytest tests/ -x --pdb
```

### Verbose Output

```bash
# Maximum verbosity
pytest tests/ -vv

# Show print statements
pytest tests/ -s

# Show local variables on failure
pytest tests/ -l
```

### Test Specific Scenarios

```python
# Add debugging to test
def test_with_debug():
    """Test with debugging"""
    result = do_something()
    
    import pdb; pdb.set_trace()  # Breakpoint
    
    assert result == expected
```

---

## Next Steps

- **[Contributing Guide](../../CONTRIBUTING.md)** - Submit your tests
- **[Architecture](ARCHITECTURE.md)** - Understand the codebase
- **[API Documentation](../user-guide/API_DOCUMENTATION.md)** - Test API endpoints

---

**Need help?** Open a GitHub issue or discussion!
