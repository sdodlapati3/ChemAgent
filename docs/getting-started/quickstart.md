# Quick Start Tutorial

Get started with ChemAgent in 5 minutes!

---

## Your First Query

### 1. Start ChemAgent

```bash
# Activate your environment
conda activate chemagent

# Run in interactive mode
python -m chemagent
```

### 2. Try a Simple Query

```
ChemAgent> What is aspirin?
```

**Expected Output**:
```
## Compound Information

**ChEMBL ID**: CHEMBL25
**Name**: aspirin
**SMILES**: CC(=O)Oc1ccccc1C(=O)O
**Molecular Weight**: 180.16 Da
...
```

---

## Common Query Patterns

### Compound Information

```python
from chemagent import ChemAgent

agent = ChemAgent()

# By name
result = agent.query("What is aspirin?")

# By ChEMBL ID
result = agent.query("What is CHEMBL25?")

# By SMILES
result = agent.query("What is CC(=O)Oc1ccccc1C(=O)O?")
```

### Property Calculations

```python
# Molecular properties
result = agent.query("Calculate properties of aspirin")

# Specific property
result = agent.query("What is the molecular weight of metformin?")

# Lipinski rules
result = agent.query("Is lisinopril drug-like?")
```

### Similarity Search

```python
# By name
result = agent.query("Find compounds similar to aspirin")

# By SMILES
result = agent.query("Find compounds similar to CC(=O)O")

# With threshold
result = agent.query("Find compounds similar to sildenafil with >80% similarity")
```

### Activity Data

```python
# IC50 values
result = agent.query("What is the IC50 of lipitor?")

# Activity lookup
result = agent.query("Get activities for CHEMBL25")
```

### Compound Comparison

```python
# Compare two compounds
result = agent.query("Compare aspirin and ibuprofen")

# Multiple properties
result = agent.query("What are the differences between lipitor and simvastatin?")
```

---

## Using the Python API

### Basic Usage

```python
from chemagent import ChemAgent

# Create agent
agent = ChemAgent()

# Run query
result = agent.query("What is aspirin?")

# Access results
print(f"Answer: {result.answer}")
print(f"Success: {result.success}")
print(f"Time: {result.execution_time_ms}ms")
```

### Configuration Options

```python
agent = ChemAgent(
    use_cache=True,          # Enable caching (default: True)
    cache_ttl=3600,          # Cache TTL in seconds
    enable_parallel=True,     # Enable parallel execution
    max_workers=4,           # Number of parallel workers
    query_timeout=30         # Query timeout in seconds
)
```

### Error Handling

```python
try:
    result = agent.query("What is INVALID_COMPOUND?")
    if result.success:
        print(result.answer)
    else:
        print(f"Error: {result.error}")
except Exception as e:
    print(f"Query failed: {e}")
```

---

## Using the REST API

### Start the Server

```bash
# Start FastAPI server
python -m chemagent.api.server

# Server runs on http://localhost:8000
# API docs at http://localhost:8000/docs
```

### Query Endpoint

```bash
# POST request
curl -X POST "http://localhost:8000/api/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is aspirin?"}'
```

```python
import requests

response = requests.post(
    "http://localhost:8000/api/query",
    json={"query": "What is aspirin?"}
)

data = response.json()
print(data["answer"])
```

---

## Using the Web UI

### Start Gradio Interface

```bash
# Start UI
python -m chemagent.ui.app

# Opens browser automatically to http://localhost:7860
```

### Features

- **Chat Interface**: Natural conversation flow
- **Example Queries**: Pre-loaded common queries
- **Result History**: Track previous queries
- **Settings Panel**: Configure caching and parallel execution

---

## Performance Tips

### 1. Enable Caching

```python
# First query: ~3000ms
result1 = agent.query("What is aspirin?")

# Cached query: ~10ms (18x faster!)
result2 = agent.query("What is aspirin?")
```

### 2. Use Parallel Execution

```python
# Sequential: ~5000ms
agent = ChemAgent(enable_parallel=False)
result = agent.query("Compare aspirin and ibuprofen")

# Parallel: ~2000ms (2.5x faster!)
agent = ChemAgent(enable_parallel=True, max_workers=4)
result = agent.query("Compare aspirin and ibuprofen")
```

### 3. Batch Processing

```python
queries = [
    "What is aspirin?",
    "What is ibuprofen?",
    "What is metformin?"
]

for query in queries:
    result = agent.query(query)
    print(f"{query}: {result.execution_time_ms}ms")
```

---

## Next Steps

### Learn More

- **[Examples](examples.md)** - More complex use cases
- **[User Guide](../user-guide/USER_GUIDE.md)** - Complete feature reference
- **[API Documentation](../user-guide/API_DOCUMENTATION.md)** - REST API details

### Try Advanced Features

- **Parallel Execution** - Speed up multi-step queries
- **Batch Processing** - Process multiple queries efficiently
- **Custom Configuration** - Tune performance settings
- **Web UI** - Interactive exploration

---

## Common Questions

**Q: How do I clear the cache?**
```bash
rm -rf ~/.cache/chemagent/*
```

**Q: Can I use ChemAgent without internet?**
No, ChemAgent requires internet access for ChEMBL, UniProt, and other APIs.

**Q: How do I increase query timeout?**
```python
agent = ChemAgent(query_timeout=60)  # 60 seconds
```

**Q: Can I save query results?**
```python
import json

result = agent.query("What is aspirin?")
with open("result.json", "w") as f:
    json.dump({
        "answer": result.answer,
        "success": result.success,
        "time_ms": result.execution_time_ms
    }, f, indent=2)
```

---

**Ready to explore?** Check out [Examples](examples.md) for more patterns!
