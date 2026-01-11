# Comprehensive Frontend Integration Testing

## Overview

This test suite simulates real frontend user interactions to systematically identify issues in query implementation and execution. It covers all intent types, edge cases, and error scenarios across three rounds of increasing complexity.

## Test Strategy

### Three-Round Approach

**Round 1: Basic Validation (100 queries)**
- Quick smoke test covering all intent types
- Focus on common use cases
- Identifies critical failures early
- **Estimated time:** ~5-10 minutes

**Round 2: Extended Coverage (500 queries)**
- Expanded testing with variations
- Edge cases and error handling
- Parameter boundary testing
- **Estimated time:** ~30-45 minutes

**Round 3: Comprehensive Testing (2000 queries)**
- Systematic parameter variations
- Stress testing with complex workflows
- Full coverage of all scenarios
- **Estimated time:** ~2-3 hours

### Coverage Areas

| Intent Type | Round 1 | Round 2 | Round 3 |
|-------------|---------|---------|---------|
| Compound Lookup | 15 | 75 | 300 |
| Property Calculation | 15 | 75 | 300 |
| Similarity Search | 15 | 75 | 300 |
| Target Lookup | 10 | 50 | 200 |
| Lipinski Check | 10 | 40 | 150 |
| Comparison | 10 | 40 | 150 |
| Substructure Search | 5 | 30 | 120 |
| Activity Lookup | 5 | 30 | 120 |
| Structure Conversion | 5 | 25 | 100 |
| Complex Workflows | 5 | 30 | 150 |
| Edge Cases | 5 | 30 | 110 |
| **Total** | **100** | **500** | **2000** |

## Usage

### Prerequisites

```bash
# Activate environment
module load python3
crun -p ~/envs/chemagent

# Ensure ChemAgent is installed
pip install -e .
```

### Running Tests

```bash
# Round 1: Basic validation (100 queries)
python -m tests.integration.test_comprehensive --round 1

# Round 2: Extended coverage (500 queries)
python -m tests.integration.test_comprehensive --round 2

# Round 3: Comprehensive testing (2000 queries)
python -m tests.integration.test_comprehensive --round 3
```

### Custom Output Directory

```bash
python -m tests.integration.test_comprehensive --round 1 \
    --output-dir /path/to/custom/output
```

## Output Files

Each test run generates:

1. **`roundN_results.json`** - Full test results with:
   - Query text
   - Expected vs actual intent
   - Success/failure status
   - Execution time
   - Error messages
   - Truncated answers

2. **`roundN_report.txt`** - Human-readable summary with:
   - Overall success rate
   - Performance metrics (avg/min/max time)
   - Intent recognition accuracy
   - Error type breakdown
   - Sample failed queries

## Example Output

```
======================================================================
COMPREHENSIVE TEST REPORT - ROUND 1
======================================================================

Overall Results:
  Total Queries:    100
  Successful:       92 (92.0%)
  Failed:           8 (8.0%)

Performance Metrics:
  Average Time:     485.32ms
  Min Time:         12.45ms
  Max Time:         2341.56ms
  
Intent Recognition:
  compound_lookup           18 queries
  similarity_search         16 queries
  property_calculation      15 queries
  comparison                10 queries
  target_lookup             9 queries
  lipinski_check            8 queries
  unknown                   7 queries
  substructure_search       5 queries
  activity_lookup           5 queries
  structure_conversion      4 queries
  
  Intent Accuracy:  94.3% (82/87)

Error Analysis:
  AttributeError                           3 occurrences
  ValueError                               2 occurrences
  KeyError                                 2 occurrences
  IndexError                               1 occurrences

Sample Failed Queries (first 10):
  [23] Find compounds with carboxyl group...
      Error: SMARTS pattern not recognized
  [45] Calculate properties of INVALID_SMILES...
      Error: Invalid SMILES string
  ...
======================================================================
```

## What Gets Tested

### 1. Compound Lookup Queries
- By name: "What is aspirin?", "Tell me about ibuprofen"
- By ChEMBL ID: "What is CHEMBL25?", "Get compound CHEMBL521"
- By SMILES: "Look up CC(=O)Oc1ccccc1C(=O)O"
- Invalid compounds: "What is NONEXISTENT?"

### 2. Property Calculation
- General: "Calculate properties of aspirin"
- Specific: "What is the molecular weight of caffeine?"
- From SMILES: "Get properties for CCO"

### 3. Similarity Search
- Basic: "Find similar compounds to aspirin"
- With threshold: "Find compounds similar to ibuprofen with similarity > 0.8"
- With limit: "Find top 10 compounds similar to caffeine"

### 4. Target Lookup
- By compound: "What targets does aspirin bind to?"
- By protein name: "Look up cyclooxygenase-2"
- By UniProt ID: "What is P35354?"

### 5. Lipinski Rules
- "Check Lipinski rules for aspirin"
- "Is ibuprofen drug-like?"
- "Does caffeine follow Ro5?"

### 6. Comparison Queries
- "Compare aspirin and ibuprofen"
- "Compare molecular weight of aspirin and ibuprofen"
- "aspirin vs ibuprofen"
- "What are the differences between aspirin and ibuprofen?"

### 7. Substructure Search
- "Find compounds with carboxyl group"
- "Search for compounds containing benzene ring"

### 8. Activity Lookup
- "Get activities for aspirin"
- "What is the IC50 of ibuprofen?"

### 9. Structure Conversion
- "Convert CC(=O)Oc1ccccc1C(=O)O to InChI"
- "Convert SMILES to InChI key"

### 10. Complex Workflows
- "Find compounds similar to aspirin and calculate their properties"
- "Get similar compounds to CHEMBL25 with similarity > 0.8 and check Lipinski rules"

### 11. Edge Cases
- Empty queries: "", "   "
- Invalid inputs: "!@#$%^&*()", "SELECT * FROM compounds"
- Very long queries: "a" * 1000
- Non-existent IDs: "CHEMBL999999999"

## Analysis Focus Areas

The test framework automatically tracks and reports:

1. **Success Rate** - Overall and per intent type
2. **Intent Recognition Accuracy** - Correct intent detection
3. **Performance** - Query execution times (avg, min, max)
4. **Error Patterns** - Most common error types
5. **Slow Queries** - Queries taking >10 seconds
6. **Failed Queries** - Detailed error messages

## Interpreting Results

### High Priority Issues
- ❌ **Success rate < 90%** - Critical failures
- ⚠️ **Intent accuracy < 85%** - Intent recognition problems
- ⚠️ **Average time > 2 seconds** - Performance concerns

### Medium Priority Issues
- ⚠️ **Specific error patterns** - Systematic bugs (e.g., all comparison queries fail)
- ⚠️ **Edge case failures** - Need better input validation

### Low Priority Issues
- ℹ️ **Occasional timeouts** - External API issues
- ℹ️ **Unknown intent for gibberish** - Expected behavior

## Next Steps After Testing

1. **Review Reports** - Analyze failure patterns
2. **Fix Critical Issues** - Address high-priority failures
3. **Rerun Tests** - Verify fixes work
4. **Iterate** - Continue until success rate > 95%

## Contributing

To add new test scenarios:

1. Edit `query_generator.py`
2. Add queries to appropriate generator function
3. Update distribution in `generate_queries()`
4. Run tests to verify

## Tips

- **Start with Round 1** to catch obvious issues quickly
- **Run with verbose logging** for debugging: `export LOG_LEVEL=DEBUG`
- **Use test results** to prioritize fixes
- **Rerun specific categories** by modifying query_generator.py
- **Check execution times** to identify performance bottlenecks

## Troubleshooting

**Tests taking too long?**
- Reduce query count in `generate_queries()`
- Focus on specific intent types
- Check for hanging external API calls

**High failure rate?**
- Review `roundN_report.txt` for error patterns
- Check sample failed queries
- Run individual queries manually for debugging

**Memory issues?**
- Process results in batches
- Clear cache between rounds
- Monitor system resources

---

**Last Updated:** January 11, 2026  
**Maintainer:** ChemAgent Development Team
