# ChemAgent Examples

Real-world examples demonstrating ChemAgent's capabilities.

---

## Table of Contents

1. [Basic Queries](#basic-queries)
2. [Property Calculations](#property-calculations)
3. [Similarity Search](#similarity-search)
4. [Activity Analysis](#activity-analysis)
5. [Batch Processing](#batch-processing)
6. [Advanced Workflows](#advanced-workflows)
7. [Integration Examples](#integration-examples)

---

## Basic Queries

### Example 1: Compound Lookup by Name

```python
from chemagent import ChemAgent

agent = ChemAgent()

# Query by common name
result = agent.query("What is aspirin?")
print(result.answer)
```

**Output**:
```
Compound: aspirin (CHEMBL25)
SMILES: CC(=O)Oc1ccccc1C(=O)O
Molecular Weight: 180.16 Da
Formula: C9H8O4
...
```

### Example 2: Compound Lookup by ChEMBL ID

```python
# Direct ChEMBL ID lookup
result = agent.query("Tell me about CHEMBL25")
print(result.answer)
```

### Example 3: Compound Lookup by SMILES

```python
# Query by SMILES structure
result = agent.query("What compound has SMILES CC(=O)Oc1ccccc1C(=O)O?")
print(result.answer)
```

---

## Property Calculations

### Example 4: Calculate All Properties

```python
# Get all molecular properties
result = agent.query("Calculate properties of metformin")

# Access specific properties
if result.success:
    print(result.answer)  # Formatted output
```

**Output**:
```
Properties for metformin (CHEMBL1431):
- Molecular Weight: 129.17 Da
- LogP: -1.43
- H-Bond Donors: 4
- H-Bond Acceptors: 2
- TPSA: 88.99 Ų
- Rotatable Bonds: 4
- Lipinski Rule of 5: PASS (all criteria met)
```

### Example 5: Specific Property Query

```python
# Ask about specific property
result = agent.query("What is the molecular weight of sildenafil?")
print(result.answer)  # "Molecular Weight: 474.58 Da"

# LogP calculation
result = agent.query("What is the LogP of lipitor?")
print(result.answer)  # "LogP: 4.23"
```

### Example 6: Drug-Likeness Assessment

```python
# Check Lipinski's Rule of 5
result = agent.query("Is lisinopril drug-like?")
print(result.answer)
```

**Output**:
```
Lipinski Rule of 5 Assessment for lisinopril:
✓ Molecular Weight: 405.49 Da (< 500)
✓ LogP: 2.13 (< 5)
✓ H-Bond Donors: 3 (≤ 5)
✓ H-Bond Acceptors: 6 (≤ 10)

Result: PASS - All Lipinski criteria met
Conclusion: Lisinopril is drug-like
```

---

## Similarity Search

### Example 7: Find Similar Compounds

```python
# Find compounds similar to aspirin
result = agent.query("Find compounds similar to aspirin")
print(result.answer)
```

**Output**:
```
Top 10 compounds similar to aspirin (CHEMBL25):

1. CHEMBL194 (98.5% similar)
   Name: Salicylic acid
   SMILES: O=C(O)c1ccccc1O

2. CHEMBL621 (95.2% similar)
   Name: Methyl salicylate
   SMILES: COC(=O)c1ccccc1O
...
```

### Example 8: Similarity with Threshold

```python
# Only high-similarity matches
result = agent.query("Find compounds similar to sildenafil with >90% similarity")
print(result.answer)
```

### Example 9: Similarity by SMILES

```python
# Direct SMILES input
result = agent.query("Find compounds similar to CC(=O)O with >85% similarity")
print(result.answer)
```

---

## Activity Analysis

### Example 10: IC50 Lookup

```python
# Get IC50 values
result = agent.query("What is the IC50 of lipitor?")
print(result.answer)
```

**Output**:
```
IC50 values for lipitor (CHEMBL1487):

Target: HMG-CoA reductase (CHEMBL402)
- IC50: 5.2 nM (Ki = 3.8 nM)
- Assay: Enzyme inhibition assay

Target: CYP3A4 (CHEMBL340)
- IC50: 15.0 μM
- Assay: Metabolic stability
...
```

### Example 11: Activity by ChEMBL ID

```python
# Direct activity lookup
result = agent.query("Get activities for CHEMBL25")
print(result.answer)
```

### Example 12: Activity Summary

```python
# Summary statistics
result = agent.query("Summarize activity data for sildenafil")
print(result.answer)
```

---

## Batch Processing

### Example 13: Process Multiple Queries

```python
# List of queries
queries = [
    "What is aspirin?",
    "What is ibuprofen?",
    "What is metformin?",
    "What is sildenafil?",
    "What is lipitor?"
]

# Process all queries
results = []
for query in queries:
    result = agent.query(query)
    results.append({
        "query": query,
        "success": result.success,
        "time_ms": result.execution_time_ms,
        "answer": result.answer
    })

# Print summary
for r in results:
    print(f"{r['query']}: {r['time_ms']}ms - {'✓' if r['success'] else '✗'}")
```

### Example 14: Parallel Batch Processing

```python
from concurrent.futures import ThreadPoolExecutor

agent = ChemAgent(enable_parallel=True, max_workers=4)

def process_query(query):
    result = agent.query(query)
    return (query, result)

# Process in parallel
with ThreadPoolExecutor(max_workers=4) as executor:
    results = list(executor.map(process_query, queries))

for query, result in results:
    print(f"{query}: {result.execution_time_ms}ms")
```

### Example 15: Export Results

```python
import json
import pandas as pd

# Collect results
data = []
for query in queries:
    result = agent.query(query)
    data.append({
        "query": query,
        "success": result.success,
        "time_ms": result.execution_time_ms,
        "answer": result.answer
    })

# Save as JSON
with open("results.json", "w") as f:
    json.dump(data, f, indent=2)

# Save as CSV
df = pd.DataFrame(data)
df.to_csv("results.csv", index=False)
```

---

## Advanced Workflows

### Example 16: Compound Comparison

```python
# Compare two compounds
result = agent.query("Compare aspirin and ibuprofen")
print(result.answer)
```

**Output**:
```
Comparison: aspirin vs ibuprofen

Property              Aspirin       Ibuprofen     Difference
------------------------------------------------------------------
Molecular Weight      180.16 Da     206.28 Da     +26.12 Da
LogP                  1.19          3.50          +2.31
H-Bond Donors         1             1             0
H-Bond Acceptors      4             2             -2
TPSA                  63.60 Ų       37.30 Ų       -26.30 Ų
Rotatable Bonds       3             4             +1

Drug-likeness         PASS          PASS          Both drug-like
```

### Example 17: Multi-Step Workflow

```python
# Step 1: Find compound
result1 = agent.query("What is the ChEMBL ID of aspirin?")
chembl_id = "CHEMBL25"  # Extract from result

# Step 2: Find similar compounds
result2 = agent.query(f"Find compounds similar to {chembl_id}")

# Step 3: Get properties of top match
result3 = agent.query(f"Calculate properties of CHEMBL194")

print(f"Step 1: {result1.answer}")
print(f"Step 2: {result2.answer}")
print(f"Step 3: {result3.answer}")
```

### Example 18: Target-Based Search

```python
# Find compounds targeting specific protein
result = agent.query("What compounds target HMG-CoA reductase?")
print(result.answer)
```

---

## Integration Examples

### Example 19: Flask Web App Integration

```python
from flask import Flask, request, jsonify
from chemagent import ChemAgent

app = Flask(__name__)
agent = ChemAgent()

@app.route("/query", methods=["POST"])
def query():
    data = request.get_json()
    query_text = data.get("query", "")
    
    result = agent.query(query_text)
    
    return jsonify({
        "success": result.success,
        "answer": result.answer,
        "time_ms": result.execution_time_ms
    })

if __name__ == "__main__":
    app.run(port=5000)
```

### Example 20: Jupyter Notebook Integration

```python
# In Jupyter notebook
from chemagent import ChemAgent
from IPython.display import Markdown, display

agent = ChemAgent()

def show_result(query):
    """Display formatted query result"""
    result = agent.query(query)
    
    # Display as Markdown
    display(Markdown(f"**Query**: {query}"))
    display(Markdown(f"**Time**: {result.execution_time_ms}ms"))
    display(Markdown(result.answer))
    
    return result

# Use it
show_result("What is aspirin?")
show_result("Find compounds similar to aspirin")
```

### Example 21: Streamlit Dashboard

```python
import streamlit as st
from chemagent import ChemAgent

st.title("ChemAgent Dashboard")

# Initialize agent
agent = ChemAgent()

# Query input
query = st.text_input("Enter your query:")

if st.button("Submit"):
    with st.spinner("Processing..."):
        result = agent.query(query)
    
    # Display results
    st.success(f"Completed in {result.execution_time_ms}ms")
    st.markdown(result.answer)
```

---

## Real-World Use Cases

### Example 22: Drug Discovery Pipeline

```python
def drug_discovery_pipeline(target_name, similarity_threshold=80):
    """Complete drug discovery workflow"""
    
    agent = ChemAgent()
    
    # Step 1: Find compounds targeting protein
    result1 = agent.query(f"What compounds target {target_name}?")
    print("Step 1: Target-based search complete")
    
    # Step 2: Get properties of lead compound
    lead_compound = "CHEMBL1487"  # Extract from result1
    result2 = agent.query(f"Calculate properties of {lead_compound}")
    print("Step 2: Properties calculated")
    
    # Step 3: Find similar compounds
    result3 = agent.query(
        f"Find compounds similar to {lead_compound} with >{similarity_threshold}% similarity"
    )
    print("Step 3: Similarity search complete")
    
    # Step 4: Check drug-likeness
    result4 = agent.query(f"Is {lead_compound} drug-like?")
    print("Step 4: Drug-likeness assessed")
    
    return {
        "target_search": result1,
        "properties": result2,
        "similar_compounds": result3,
        "drug_likeness": result4
    }

# Run pipeline
results = drug_discovery_pipeline("HMG-CoA reductase")
```

### Example 23: Compound Library Analysis

```python
import pandas as pd

def analyze_compound_library(compound_list):
    """Analyze list of compounds for drug-likeness"""
    
    agent = ChemAgent()
    results = []
    
    for compound in compound_list:
        # Get properties
        result = agent.query(f"Calculate properties of {compound}")
        
        # Check drug-likeness
        drug_like = agent.query(f"Is {compound} drug-like?")
        
        results.append({
            "compound": compound,
            "properties": result.answer,
            "drug_like": "PASS" in drug_like.answer,
            "time_ms": result.execution_time_ms
        })
    
    # Create DataFrame
    df = pd.DataFrame(results)
    return df

# Analyze library
compounds = ["CHEMBL25", "CHEMBL1431", "CHEMBL1487", "CHEMBL192"]
df = analyze_compound_library(compounds)
print(df)
```

---

## Performance Benchmarks

### Example 24: Cache Performance

```python
import time

agent = ChemAgent(use_cache=True)
query = "What is aspirin?"

# First query (no cache)
start = time.time()
result1 = agent.query(query)
time1 = (time.time() - start) * 1000

# Second query (cached)
start = time.time()
result2 = agent.query(query)
time2 = (time.time() - start) * 1000

print(f"First query: {time1:.0f}ms")
print(f"Cached query: {time2:.0f}ms")
print(f"Speedup: {time1/time2:.1f}x faster")
```

**Output**:
```
First query: 2847ms
Second query: 12ms
Speedup: 237.3x faster
```

### Example 25: Parallel Execution Benchmark

```python
# Test sequential vs parallel
queries = [f"What is CHEMBL{i}?" for i in range(25, 35)]

# Sequential
agent_seq = ChemAgent(enable_parallel=False)
start = time.time()
for q in queries:
    agent_seq.query(q)
time_seq = time.time() - start

# Parallel
agent_par = ChemAgent(enable_parallel=True, max_workers=4)
start = time.time()
for q in queries:
    agent_par.query(q)
time_par = time.time() - start

print(f"Sequential: {time_seq:.2f}s")
print(f"Parallel: {time_par:.2f}s")
print(f"Speedup: {time_seq/time_par:.1f}x faster")
```

---

## Error Handling

### Example 26: Robust Error Handling

```python
def safe_query(query_text):
    """Query with comprehensive error handling"""
    
    agent = ChemAgent()
    
    try:
        result = agent.query(query_text)
        
        if result.success:
            return {"status": "success", "answer": result.answer}
        else:
            return {"status": "failed", "error": result.error}
            
    except TimeoutError:
        return {"status": "error", "message": "Query timed out"}
    except ConnectionError:
        return {"status": "error", "message": "Network connection failed"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# Use it
result = safe_query("What is INVALID_ID?")
print(result)
```

---

## Next Steps

- **[User Guide](../user-guide/USER_GUIDE.md)** - Complete feature reference
- **[API Documentation](../user-guide/API_DOCUMENTATION.md)** - REST API details
- **[Contributing](../../CONTRIBUTING.md)** - Add your own examples

---

**Have a great example?** Submit a pull request to share it with the community!
