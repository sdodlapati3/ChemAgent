# Comprehensive Frontend Integration Testing Plan

**Date:** January 11, 2026  
**Status:** Round 1 In Progress  
**Objective:** Systematically identify all issues in query implementation/execution

---

## 🎯 Testing Strategy

### Three-Round Progressive Testing

| Round | Queries | Focus | Time | Status |
|-------|---------|-------|------|--------|
| **1** | 100 | Smoke test, critical path validation | ~10 min | 🔄 Running |
| **2** | 500 | Extended coverage, edge cases | ~45 min | ⏳ Pending |
| **3** | 2000 | Comprehensive, stress testing | ~3 hrs | ⏳ Pending |

---

## 📊 Test Coverage

### Query Distribution by Intent Type

```
Round 1 (100 queries):
├── Compound Lookup       15 queries  ██████████
├── Property Calculation  15 queries  ██████████
├── Similarity Search     15 queries  ██████████
├── Target Lookup         10 queries  ███████
├── Lipinski Check        10 queries  ███████
├── Comparison            10 queries  ███████
├── Substructure Search    5 queries  ███
├── Activity Lookup        5 queries  ███
├── Structure Conversion   5 queries  ███
├── Complex Workflows      5 queries  ███
└── Edge Cases             5 queries  ███

Round 2 (500 queries):
├── Compound Lookup       75 queries  ██████████
├── Property Calculation  75 queries  ██████████
├── Similarity Search     75 queries  ██████████
├── Target Lookup         50 queries  ███████
├── Lipinski Check        40 queries  █████
├── Comparison            40 queries  █████
├── Substructure Search   30 queries  ████
├── Activity Lookup       30 queries  ████
├── Structure Conversion  25 queries  ███
├── Complex Workflows     30 queries  ████
└── Edge Cases            30 queries  ████

Round 3 (2000 queries):
├── Compound Lookup       300 queries  ██████████
├── Property Calculation  300 queries  ██████████
├── Similarity Search     300 queries  ██████████
├── Target Lookup         200 queries  ███████
├── Lipinski Check        150 queries  █████
├── Comparison            150 queries  █████
├── Substructure Search   120 queries  ████
├── Activity Lookup       120 queries  ████
├── Structure Conversion  100 queries  ███
├── Complex Workflows     150 queries  █████
└── Edge Cases            110 queries  ████
```

---

## 🔍 What Gets Tested

### 1. Compound Lookup Queries
- ✓ By name: "What is aspirin?"
- ✓ By ChEMBL ID: "What is CHEMBL25?"
- ✓ By SMILES: "Look up CC(=O)Oc1ccccc1C(=O)O"
- ✓ Variations: "Tell me about...", "Get compound...", "Look up..."
- ⚠️ Invalid: "What is NONEXISTENT?"

### 2. Property Calculation
- ✓ General: "Calculate properties of aspirin"
- ✓ Specific: "What is the molecular weight of caffeine?"
- ✓ From SMILES: "Get properties for CCO"
- ✓ Multiple properties: "Get logP and PSA for aspirin"

### 3. Similarity Search
- ✓ Basic: "Find similar compounds to aspirin"
- ✓ With threshold: "Find compounds similar to ibuprofen with similarity > 0.8"
- ✓ With limit: "Find top 10 compounds similar to caffeine"
- ✓ Variations: "Search for analogs...", "What compounds are similar..."

### 4. Target Lookup
- ✓ By compound: "What targets does aspirin bind to?"
- ✓ By protein name: "Look up cyclooxygenase-2"
- ✓ By UniProt ID: "What is P35354?"

### 5. Lipinski Rules
- ✓ Check rules: "Check Lipinski rules for aspirin"
- ✓ Druglikeness: "Is ibuprofen drug-like?"
- ✓ Ro5: "Does caffeine follow Ro5?"

### 6. Comparison Queries (NEW!)
- ✓ Compare: "Compare aspirin and ibuprofen"
- ✓ Specific property: "Compare molecular weight of aspirin and ibuprofen"
- ✓ Vs format: "aspirin vs ibuprofen"
- ✓ Differences: "What are the differences between aspirin and ibuprofen?"

### 7-11. Other Intent Types
- Substructure search (functional groups)
- Activity lookup (IC50, Ki)
- Structure conversion (InChI, InChI Key)
- Complex workflows (multi-step)
- Edge cases (empty, invalid, malformed)

---

## 📈 Success Metrics

### Target Benchmarks

| Metric | Minimum | Target | Excellent |
|--------|---------|--------|-----------|
| **Success Rate** | 85% | 90% | 95% |
| **Intent Accuracy** | 80% | 85% | 90% |
| **Avg Execution Time** | <3s | <2s | <1s |
| **Slow Queries (<10s)** | <10% | <5% | <2% |

### Early Observations from Round 1

Based on initial output (first 40 queries):

**✅ Working Well:**
- Compound lookup by name (aspirin, ibuprofen, etc.)
- Property calculation for common compounds
- Lipinski rule checking
- Target lookup
- Comparison queries (though slow)

**⚠️ Issues Identified:**

1. **Intent Recognition Failures:**
   - "Tell me about atorvastatin" → `unknown` (expected: `compound_lookup`)
   - "What is amoxicillin?" → `unknown` (expected: `compound_lookup`)
   - Pattern: Some compound names not recognized

2. **Similarity Search Errors:**
   - Trying to use compound NAME directly as SMILES
   - "What compounds are similar to acetaminophen?" → SMILES parse error
   - Root cause: Not looking up compound first before similarity search

3. **Conversion Query Failures:**
   - "Convert CC(=O)Oc1ccccc1C(=O)O to InChI key" → Failed (error: None)
   - Need to investigate structure conversion implementation

4. **Performance Issues:**
   - Comparison queries taking 12-15 seconds
   - Need to optimize multi-compound queries

5. **Empty Query Handling:**
   - Empty string queries properly caught

---

## 🐛 Known Issues to Fix

### Priority 1 (Critical)
- [ ] Intent recognition for certain compound names (atorvastatin, amoxicillin)
- [ ] Similarity search should lookup compound first, not treat name as SMILES
- [ ] Structure conversion queries returning None error

### Priority 2 (Important)
- [ ] Comparison queries taking >10 seconds (should be <5s)
- [ ] Better error messages for failed queries

### Priority 3 (Nice to Have)
- [ ] Cache optimization for repeated compound lookups
- [ ] Parallel execution for independent similarity searches

---

## 📁 Output Files

Test results are saved to: `tests/integration/test_results/`

**Files Generated:**
- `round1_results.json` - Full test results (JSON)
- `round1_report.txt` - Human-readable summary
- `/tmp/test_round1.log` - Complete execution log

---

## 🚀 Running Tests

### Quick Start

```bash
# Activate environment
module load python3
crun -p ~/envs/chemagent

# Round 1: Basic validation (100 queries, ~10 min)
python -m tests.integration.test_comprehensive --round 1

# Round 2: Extended coverage (500 queries, ~45 min)
python -m tests.integration.test_comprehensive --round 2

# Round 3: Comprehensive (2000 queries, ~3 hrs)
python -m tests.integration.test_comprehensive --round 3
```

### Background Execution

```bash
# Run in background and save logs
python -m tests.integration.test_comprehensive --round 1 > /tmp/test_round1.log 2>&1 &

# Check progress
tail -f /tmp/test_round1.log

# Check when complete
ls -lh tests/integration/test_results/
```

---

## 📊 Analysis Workflow

### 1. Review Report
```bash
cat tests/integration/test_results/round1_report.txt
```

### 2. Check Failed Queries
```bash
# Extract failures from JSON
jq '.results[] | select(.success == false)' tests/integration/test_results/round1_results.json
```

### 3. Check Intent Accuracy
```bash
# Count intent mismatches
jq '[.results[] | select(.expected_intent != null and .intent_type != .expected_intent)] | length' \
   tests/integration/test_results/round1_results.json
```

### 4. Performance Analysis
```bash
# Find slowest queries
jq '.results | sort_by(-.execution_time_ms) | .[0:10]' \
   tests/integration/test_results/round1_results.json
```

---

## 🔄 Iteration Plan

### After Round 1:
1. **Review report** - Identify top 3 failure patterns
2. **Fix critical issues** - Address P1 bugs
3. **Verify fixes** - Re-run failed queries manually
4. **Proceed to Round 2** - Once success rate >85%

### After Round 2:
1. **Analyze edge cases** - Focus on unusual failures
2. **Performance optimization** - Target slow queries
3. **Intent tuning** - Improve recognition accuracy
4. **Proceed to Round 3** - Once success rate >90%

### After Round 3:
1. **Final report** - Comprehensive analysis
2. **Documentation** - Update API docs with findings
3. **Benchmarks** - Establish performance baselines
4. **Release decision** - Go/no-go based on metrics

---

## 📝 Next Steps

1. ⏳ **Wait for Round 1 completion** (~10 minutes)
2. 📊 **Review generated report** in `test_results/`
3. 🐛 **Fix identified issues** based on failure patterns
4. ✅ **Re-run Round 1** to verify fixes
5. 🚀 **Proceed to Round 2** once stable

---

## 💡 Tips

- **Start small**: Always run Round 1 first
- **Fix iteratively**: Don't wait for all rounds to fix issues
- **Check logs**: Detailed errors in `/tmp/test_round1.log`
- **Monitor progress**: `tail -f` on log file
- **Save results**: Keep all test outputs for comparison

---

**Test Framework Files:**
- `tests/integration/test_comprehensive.py` - Main test executor
- `tests/integration/query_generator.py` - Query generation
- `tests/integration/README.md` - Detailed documentation

**Current Status:** Round 1 running (PID 543685)  
**Check results:** `cat tests/integration/test_results/round1_report.txt`
