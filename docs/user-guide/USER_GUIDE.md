# ChemAgent User Guide

## Welcome to ChemAgent! 🧪

ChemAgent is your AI-powered pharmaceutical research assistant that understands natural language queries about compounds, properties, targets, and more.

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Query Types](#query-types)
3. [Using the Web Interface](#using-the-web-interface)
4. [Using the CLI](#using-the-cli)
5. [Using the API](#using-the-api)
6. [Advanced Features](#advanced-features)
7. [Tips & Best Practices](#tips--best-practices)
8. [Troubleshooting](#troubleshooting)

---

## Getting Started

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/chemagent.git
cd chemagent

# Install dependencies
pip install -r requirements.txt

# Or with conda
conda env create -f environment.yml
conda activate chemagent
```

### Quick Start

**Option 1: Web Interface (Recommended)**
```bash
python -m chemagent.ui.run
# Open http://localhost:7860 in your browser
```

**Option 2: Command Line**
```bash
python -m chemagent.cli "What is CHEMBL25?"
```

**Option 3: API Server**
```bash
uvicorn chemagent.api.server:app --reload
# Access at http://localhost:8000
```

---

## Query Types

### 1. Compound Lookup 🔍

Find information about specific compounds by ID, name, or SMILES.

**Examples:**
```
What is CHEMBL25?
Tell me about aspirin
Look up ibuprofen
Find information on CC(=O)OC1=CC=CC=C1C(=O)O
```

**What you get:**
- Compound name and synonyms
- ChEMBL ID
- Chemical structure
- Basic properties
- Drug development phase

### 2. Property Queries 📊

Calculate or retrieve molecular properties.

**Examples:**
```
What is the molecular weight of aspirin?
Get LogP for CHEMBL25
Calculate properties of caffeine
What are the physicochemical properties of ibuprofen?
```

**Available Properties:**
- Molecular weight
- LogP (lipophilicity)
- Hydrogen bond donors/acceptors
- Rotatable bonds
- Polar surface area
- Aromatic rings
- Lipinski rule violations

### 3. Property Comparisons ⚖️

Compare properties between compounds.

**Examples:**
```
Compare molecular weight of aspirin and ibuprofen
Which has higher LogP: aspirin or ibuprofen?
Compare all properties of aspirin and paracetamol
```

**Features:**
- Side-by-side comparison
- Highlight differences
- Identify better candidates

### 4. Similarity Search 🔬

Find structurally similar compounds.

**Examples:**
```
Find compounds similar to aspirin
Search for analogs of CHEMBL25 with similarity > 0.8
Top 10 most similar compounds to caffeine
Find aspirin-like compounds
```

**Parameters:**
- Similarity threshold (0.0 - 1.0)
- Number of results
- Tanimoto coefficient used

### 5. Target Queries 🎯

Discover protein targets and binding information.

**Examples:**
```
What targets does aspirin bind to?
Find targets for CHEMBL25
Get protein targets of ibuprofen with activity < 100nM
What proteins does metformin target?
```

**Information Provided:**
- Target name and type
- Organism
- Binding affinity
- Activity values (IC50, Ki, etc.)

### 6. Reverse Target Search 🔄

Find compounds that bind to specific targets.

**Examples:**
```
Find compounds that bind to COX-2
List drugs targeting EGFR with IC50 < 50nM
What compounds inhibit kinases?
```

### 7. Complex Workflows 🔗

Multi-step queries combining multiple operations.

**Examples:**
```
Find similar compounds to aspirin and get their targets
Get properties and targets for CHEMBL25
Find compounds similar to ibuprofen, get their properties, and filter by MW < 300
Compare properties of aspirin and ibuprofen, then find compounds similar to the one with higher LogP
```

**Capabilities:**
- Chained operations
- Conditional logic
- Filtering and ranking
- Parallel execution

---

## Using the Web Interface

### Main Query Tab

1. **Enter your query** in the text box
2. **Click "Submit"** or press Ctrl+Enter
3. **View results** in three sections:
   - Status: Query execution status
   - Results: Detailed text results
   - Visualization: Interactive visual display

**Options:**
- ✓ **Use cache**: Speed up repeated queries
- ✓ **Verbose output**: See execution details

**Example Queries:** Click any example to populate the query box

### Batch Processing Tab

Process multiple queries at once:

1. **Enter queries** (one per line)
2. **Configure options:**
   - Use cache
   - Enable parallel processing
3. **Click "Process Batch"**
4. **View summary** and individual results

**Example:**
```
What is CHEMBL25?
Find similar compounds to aspirin
Get properties for caffeine
What targets does ibuprofen bind to?
```

### History Tab

Access and manage your query history:

- **Search**: Find past queries by keyword
- **Favorites**: Mark important queries with ⭐
- **Load**: Reload previous queries and results
- **Clear**: Remove all history

**Tips:**
- History persists across sessions
- Up to 1000 queries stored
- Search supports partial matches

---

## Using the CLI

### Interactive Mode

Start an interactive session:

```bash
python -m chemagent.cli
```

**Commands:**
- Type your query and press Enter
- `exit` or `quit` to close
- `history` to see past queries
- `clear` to clear screen

### Single Query Mode

Run one-off queries:

```bash
python -m chemagent.cli "What is CHEMBL25?"
```

### Batch Processing

Process queries from a file:

```bash
# Create a query file
cat > queries.txt << EOF
What is CHEMBL25?
Find similar compounds to aspirin
Get properties for caffeine
EOF

# Process batch
python -m chemagent.cli --batch queries.txt
```

### Evaluation Mode

Run quality assurance tests:

```bash
# Run all evaluations
python -m chemagent.cli --eval all

# Run specific category
python -m chemagent.cli --eval compound_lookup

# Generate HTML report
python -m chemagent.cli --eval all --report html
```

### CLI Options

```bash
--no-api         # Use mock data (for testing)
--verbose        # Show execution details
--no-cache       # Disable result caching
--cache-ttl N    # Set cache TTL in seconds
--no-parallel    # Disable parallel execution
--max-workers N  # Set max parallel workers (1-16)
```

**Examples:**
```bash
# Verbose output with no caching
python -m chemagent.cli "What is aspirin?" --verbose --no-cache

# Batch with 8 workers
python -m chemagent.cli --batch queries.txt --max-workers 8
```

---

## Using the API

### Starting the Server

```bash
# Development mode with auto-reload
uvicorn chemagent.api.server:app --reload

# Production mode
uvicorn chemagent.api.server:app --host 0.0.0.0 --port 8000 --workers 4
```

### Making Requests

**Python:**
```python
import requests

response = requests.post(
    "http://localhost:8000/query",
    json={"query": "What is CHEMBL25?"}
)
result = response.json()
print(result['result'])
```

**cURL:**
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is CHEMBL25?"}'
```

**JavaScript:**
```javascript
const response = await fetch('http://localhost:8000/query', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({query: 'What is CHEMBL25?'})
});
const result = await response.json();
```

### API Documentation

- **Interactive Docs**: http://localhost:8000/docs
- **OpenAPI Spec**: http://localhost:8000/openapi.json
- **Full Documentation**: See [API_DOCUMENTATION.md](API_DOCUMENTATION.md)

---

## Advanced Features

### Caching

Results are automatically cached for faster repeated queries:

```python
# First query (not cached)
response1 = agent.process_query("What is CHEMBL25?")  # 450ms

# Same query (cached)
response2 = agent.process_query("What is CHEMBL25?")  # 15ms
```

**Cache Management:**
- Default TTL: 1 hour
- Configurable per query
- Manual cache clearing available
- Statistics tracking

### Parallel Execution

Independent steps run in parallel automatically:

```python
# Query with parallel-eligible steps
agent.process_query(
    "Compare properties of aspirin and ibuprofen",
    enable_parallel=True,
    max_workers=4
)
# Property lookups run in parallel (4x faster)
```

### Streaming Results

Get real-time updates as queries process:

```python
import requests

response = requests.post(
    "http://localhost:8000/query/stream",
    json={"query": "Find similar compounds to aspirin"},
    headers={"Accept": "text/event-stream"},
    stream=True
)

for line in response.iter_lines():
    if line:
        data = json.loads(line.decode('utf-8').replace('data: ', ''))
        print(f"{data['event']}: {data}")
```

### Configuration

Customize behavior via environment variables:

```bash
# .env file
CHEMAGENT_PORT=8000
CHEMAGENT_WORKERS=4
CHEMAGENT_CACHE_ENABLED=true
CHEMAGENT_ENABLE_PARALLEL=true
CHEMAGENT_MAX_WORKERS=8
CHEMAGENT_LOG_LEVEL=INFO
```

Or programmatically:

```python
from chemagent.config import get_config

config = get_config()
config.max_workers = 8
config.cache_enabled = True
```

---

## Tips & Best Practices

### Writing Good Queries

**✅ DO:**
- Be specific: "What is the molecular weight of aspirin?"
- Use standard identifiers: "CHEMBL25" rather than "that aspirin drug"
- Break complex queries into steps
- Specify thresholds: "similarity > 0.8" not "very similar"

**❌ DON'T:**
- Be vague: "tell me about drugs"
- Use ambiguous terms: "the compound" without context
- Ask unrelated questions: "what's the weather?"
- Combine too many operations in one query

### Performance Optimization

1. **Enable caching** for repeated queries
2. **Use batch processing** for multiple queries
3. **Enable parallel execution** when possible
4. **Specify limits** to avoid large result sets
5. **Use specific identifiers** (ChEMBL IDs) when known

### Data Quality

- Results come from ChEMBL database
- Property calculations use RDKit
- Similarity uses Tanimoto coefficient
- Target data includes experimental evidence

### Query Limits

- Single query: 500 characters max
- Batch processing: 100 queries max
- Similarity results: 100 max
- Rate limit: 60 requests/minute

---

## Troubleshooting

### Common Issues

**"Module not found" error**
```bash
# Ensure you're in the correct environment
conda activate chemagent
pip install -r requirements.txt
```

**"Port already in use"**
```bash
# Use a different port
python -m chemagent.ui.run --port 7861
```

**"Compound not found"**
- Verify the identifier (ChEMBL ID, name, or SMILES)
- Try alternative names or synonyms
- Check ChEMBL database directly

**Slow performance**
- Enable caching: `use_cache=True`
- Use parallel execution: `enable_parallel=True`
- Increase workers: `max_workers=8`
- Check network connectivity

**Empty results**
- Verify query syntax
- Check threshold values (similarity, activity)
- Try broadening search criteria

### Getting Help

1. **Check logs**: `tail -f logs/chemagent.log`
2. **Enable verbose mode**: `--verbose` flag
3. **Review documentation**: See docs/ folder
4. **Report issues**: GitHub Issues
5. **Contact support**: support@example.com

### Debug Mode

```bash
# Enable debug logging
export CHEMAGENT_LOG_LEVEL=DEBUG
python -m chemagent.cli --verbose "your query"
```

---

## Next Steps

- 📖 Read the [API Documentation](API_DOCUMENTATION.md)
- 🚀 See [Deployment Guide](DEPLOYMENT_GUIDE.md)
- 💻 Check out [Examples](../examples/)
- 🧪 Run evaluations: `python -m chemagent.cli --eval all`

**Happy researching! 🎉**
