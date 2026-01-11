# Testing Improvements - Before Round 2

## Current Status
- **Round 1 Progress**: 98 queries, 80.6% success (79/98 passed)
- **Improvements Made**: +12.2% success rate from initial 68.4%
- **Issues Fixed**: Intent parsing (drug names vs SMILES), activity lookup parameters
- **Blocker**: Test hung on comparison query #11 for >7 minutes

## Critical Updates Needed

### 1. Add Timeout Protection (CRITICAL - Must Do)

**Problem**: Tests can hang indefinitely on slow queries
**Impact**: Cannot complete test runs reliably

**Solution**: Add timeout wrapper to test executor

```python
# In test_comprehensive.py, add:
import signal
from contextlib import contextmanager

@contextmanager
def timeout(seconds):
    """Context manager for query timeout"""
    def timeout_handler(signum, frame):
        raise TimeoutError(f"Query exceeded {seconds}s timeout")
    
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)

# In run_single_query method, wrap query execution:
try:
    with timeout(30):  # 30 second timeout
        result: QueryResult = self.agent.query(query)
except TimeoutError as e:
    return TestResult(
        query_id=query_id,
        query=query,
        intent_type=None,
        success=False,
        execution_time_ms=(time.time() - start_time) * 1000,
        error="TIMEOUT: Query exceeded 30s",
        answer=None,
        cached=False,
        expected_intent=expected_intent
    )
```

### 2. Investigate Comparison Query Slowness (HIGH PRIORITY)

**Problem**: Comparison queries taking >5 minutes or hanging
**Example**: "aspirin vs ibuprofen" hung at query #11

**Investigation Steps**:
1. Check if comparison queries make multiple sequential API calls
2. Review query_planner.py `_plan_comparison()` - might not be parallelizing properly
3. Test single comparison query manually with logging:
   ```bash
   python -c "from chemagent import ChemAgent; agent = ChemAgent(); result = agent.query('Compare aspirin and ibuprofen'); print(result)"
   ```

**Potential Fixes**:
- Ensure parallel execution is enabled for compound lookups
- Add caching to avoid repeated lookups
- Reduce number of properties calculated per compound
- Set lower limits on results returned

### 3. Expand Common Drug Names (MEDIUM PRIORITY)

**Current List**: 14 drugs (aspirin, ibuprofen, caffeine, etc.)
**Missing**: Many FDA-approved drugs that users might query

**Recommendation**: Add top 50-100 most common drugs:
```python
common_drugs = [
    # Current drugs
    "aspirin", "ibuprofen", "acetaminophen", "paracetamol",
    "caffeine", "morphine", "cocaine", "warfarin", "insulin",
    "penicillin", "metformin", "lipitor", "viagra", "prozac",
    "diazepam", "amoxicillin", "atorvastatin", "simvastatin",
    
    # Add these common drugs:
    "lisinopril", "levothyroxine", "azithromycin", "metoprolol",
    "amlodipine", "omeprazole", "albuterol", "losartan",
    "gabapentin", "hydrochlorothiazide", "sertraline", "furosemide",
    "prednisone", "tramadol", "montelukast", "escitalopram",
    "rosuvastatin", "clopidogrel", "tamsulosin", "pantoprazole",
    # ... etc
]
```

### 4. Add Better Error Recovery (MEDIUM PRIORITY)

**Problem**: Some queries fail due to transient network issues or API rate limits

**Solution**: Add retry logic with exponential backoff
```python
def run_single_query_with_retry(self, query, expected_intent, query_id, max_retries=3):
    for attempt in range(max_retries):
        try:
            return self.run_single_query(query, expected_intent, query_id)
        except Exception as e:
            if attempt < max_retries - 1 and "timeout" not in str(e).lower():
                logger.info(f"Retry {attempt + 1}/{max_retries} for query {query_id}")
                time.sleep(2 ** attempt)  # 1s, 2s, 4s
            else:
                raise
```

### 5. Improve Test Reporting (LOW PRIORITY)

**Add to Report**:
- Breakdown of failures by error type
- List of slowest queries (top 10)
- Cache hit rate statistics
- Network call count per query
- Memory usage statistics

### 6. Create Focused Regression Tests (MEDIUM PRIORITY)

**Purpose**: Quick validation of specific bug fixes

**Create**: `tests/integration/test_regression.py`
```python
def test_similarity_with_drug_names():
    """Regression test for drug name vs SMILES parsing"""
    agent = ChemAgent()
    
    test_cases = [
        ("Search for analogs of diazepam", True),
        ("Find compounds similar to caffeine", True),
        ("What compounds are similar to morphine?", True),
    ]
    
    for query, should_succeed in test_cases:
        result = agent.query(query)
        assert result.success == should_succeed, f"Failed: {query}"

def test_activity_lookups():
    """Regression test for activity lookup parameters"""
    agent = ChemAgent()
    
    result = agent.query("What is the IC50 of ibuprofen?")
    assert result.success, f"Activity lookup failed: {result.error}"
```

## Recommended Testing Sequence

### Phase 1: Validate Fixes (30 minutes)
1. ✅ Add timeout protection
2. ✅ Add common drug names (top 50)
3. ✅ Create regression test suite
4. Run regression tests (should be <2 minutes)
5. Fix any regression failures

### Phase 2: Round 1 Re-run (15 minutes)
1. Re-run Round 1 with timeouts enabled
2. Target: >85% success rate
3. Analyze any new failure patterns
4. Fix critical issues only

### Phase 3: Round 2 (45 minutes)
1. Run 500 queries with timeouts
2. Target: >90% success rate
3. Collect performance metrics
4. Identify optimization opportunities

### Phase 4: Round 3 (3 hours)
1. Run 2000 queries comprehensive test
2. Target: >95% success rate
3. Generate final report
4. Document all remaining issues

## Priority Ranking

**Must Fix Before Round 2**:
1. ✅ Timeout protection (prevents test hangs)
2. ✅ Comparison query investigation (major slowness)

**Should Fix Before Round 2**:
3. ✅ Add more common drug names (improves coverage)
4. ⚠️ Create regression test suite (faster validation)

**Nice to Have**:
5. Better error recovery with retries
6. Enhanced test reporting
7. Performance profiling per query type

## Estimated Time Investment

- **Timeout protection**: 15 minutes
- **Add 50 common drugs**: 10 minutes
- **Investigate comparison slowness**: 30 minutes (might find quick fix)
- **Create regression tests**: 20 minutes
- **Total**: ~75 minutes before Round 2

## Expected Outcomes After Updates

- Round 2 will complete without hanging
- Success rate should reach 85-90%
- Faster iteration cycle with regression tests
- Better visibility into performance issues
- More robust error handling

## Alternative: Skip to Round 2 Now

If time-constrained, minimum viable approach:
1. Add timeout protection only (15 min)
2. Run Round 2 with 30s timeout per query
3. Accept that some queries will timeout and fail
4. Analyze results to prioritize fixes
5. Fix most critical issues
6. Run Round 3

This gets you data faster but with potentially lower success rates.
