# ChemAgent REST API Documentation

**Version**: 1.0.0  
**Base URL**: `http://localhost:8000`  
**OpenAPI Docs**: `http://localhost:8000/docs`

---

## Quick Start

### Starting the Server

```bash
# Using the startup script
./start_api.sh

# Or directly with uvicorn
crun -p ~/envs/chemagent python -m uvicorn chemagent.api.server:app --reload

# Custom port
./start_api.sh --port 8080
```

### Making Your First Request

```bash
# Using curl
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is CHEMBL25?"}'

# Using Python requests
import requests
response = requests.post(
    "http://localhost:8000/query",
    json={"query": "What is CHEMBL25?"}
)
print(response.json())
```

---

## Endpoints

### Core Endpoints

#### `GET /` - API Information
Returns basic API information.

**Response:**
```json
{
  "name": "ChemAgent API",
  "version": "1.0.0",
  "description": "Pharmaceutical research assistant",
  "docs": "/docs",
  "health": "/health"
}
```

#### `GET /health` - Health Check
Check API health and status.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-01-09T12:00:00",
  "version": "1.0.0",
  "api_available": true,
  "cache_enabled": true,
  "cache_stats": {
    "hits": 10,
    "misses": 5,
    "hit_rate": 0.667
  }
}
```

---

### Query Endpoints

#### `POST /query` - Process Natural Language Query
Main endpoint for processing natural language queries.

**Request Body:**
```json
{
  "query": "What is CHEMBL25?",
  "use_cache": true,
  "verbose": false
}
```

**Parameters:**
- `query` (string, required): Natural language query (1-500 characters)
- `use_cache` (boolean, optional): Enable result caching (default: true)
- `verbose` (boolean, optional): Include execution details (default: false)

**Example Queries:**
- `"What is CHEMBL25?"`
- `"Calculate properties of aspirin"`
- `"Find compounds similar to CC(=O)Oc1ccccc1C(=O)O"`
- `"Check Lipinski for CHEMBL25"`
- `"What is the activity of aspirin?"`

**Response:**
```json
{
  "status": "completed",
  "query": "What is CHEMBL25?",
  "intent": "compound_lookup",
  "result": {
    "compound": {
      "chembl_id": "CHEMBL25",
      "preferred_name": "8-hour bayer",
      "smiles": "CC(=O)Oc1ccccc1C(=O)O",
      "molecular_formula": "C9H8O4",
      "molecular_weight": 180.16,
      "alogp": 1.31
    }
  },
  "execution_time_ms": 18.5,
  "cached": false,
  "error": null,
  "details": null
}
```

**With Verbose Mode:**
```json
{
  "status": "completed",
  "query": "Calculate properties of aspirin",
  "intent": "property_calculation",
  "result": { ... },
  "execution_time_ms": 25.3,
  "cached": false,
  "error": null,
  "details": {
    "parsed_intent": {
      "type": "property_calculation",
      "entities": {"compound_name": "aspirin"},
      "constraints": {}
    },
    "plan": {
      "num_steps": 3,
      "steps": [
        {"tool": "chembl_search_by_name", "dependencies": []},
        {"tool": "rdkit_standardize_smiles", "dependencies": [0]},
        {"tool": "rdkit_calc_properties", "dependencies": [1]}
      ]
    },
    "cache_stats": {
      "hits": 2,
      "misses": 1,
      "total": 3,
      "hit_rate": 0.667
    }
  }
}
```

---

### Compound Endpoints

#### `POST /compound/lookup` - Lookup Compound
Look up a compound by ChEMBL ID or name.

**Request Body:**
```json
{
  "identifier": "CHEMBL25",
  "use_cache": true
}
```

**Parameters:**
- `identifier` (string, required): ChEMBL ID or compound name
- `use_cache` (boolean, optional): Enable caching (default: true)

**Response:** Same as `/query` endpoint

---

#### `POST /compound/properties` - Calculate Properties
Calculate molecular properties for a SMILES string.

**Request Body:**
```json
{
  "smiles": "CC(=O)Oc1ccccc1C(=O)O",
  "use_cache": true
}
```

**Parameters:**
- `smiles` (string, required): Valid SMILES string
- `use_cache` (boolean, optional): Enable caching (default: true)

**Response:**
```json
{
  "status": "completed",
  "query": "Calculate properties of CC(=O)Oc1ccccc1C(=O)O",
  "intent": "property_calculation",
  "result": {
    "properties": {
      "mw": 180.16,
      "alogp": 1.31,
      "num_h_donors": 1,
      "num_h_acceptors": 3,
      "tpsa": 63.60,
      "rotatable_bonds": 2,
      "num_rings": 1
    }
  },
  "execution_time_ms": 15.2,
  "cached": false,
  "error": null
}
```

---

#### `POST /compound/similar` - Find Similar Compounds
Find compounds similar to the query SMILES.

**Request Body:**
```json
{
  "smiles": "CC(=O)Oc1ccccc1C(=O)O",
  "threshold": 0.7,
  "limit": 10,
  "use_cache": true
}
```

**Parameters:**
- `smiles` (string, required): Query SMILES string
- `threshold` (float, optional): Tanimoto similarity threshold 0.0-1.0 (default: 0.7)
- `limit` (integer, optional): Max results 1-100 (default: 10)
- `use_cache` (boolean, optional): Enable caching (default: true)

**Response:**
```json
{
  "status": "completed",
  "query": "Find compounds similar to CC(=O)Oc1ccccc1C(=O)O with threshold 0.7",
  "intent": "similarity_search",
  "result": {
    "similar_compounds": [
      {
        "chembl_id": "CHEMBL25",
        "smiles": "CC(=O)Oc1ccccc1C(=O)O",
        "similarity": 1.0
      },
      {
        "chembl_id": "CHEMBL521",
        "smiles": "CC(=O)Oc1ccccc1",
        "similarity": 0.85
      }
    ]
  },
  "execution_time_ms": 250.5,
  "cached": false,
  "error": null
}
```

---

#### `GET /compound/{chembl_id}` - Get Compound by ID
Get compound information by ChEMBL ID.

**Path Parameters:**
- `chembl_id` (string, required): ChEMBL ID (e.g., "CHEMBL25")

**Query Parameters:**
- `use_cache` (boolean, optional): Enable caching (default: true)

**Example:**
```bash
curl http://localhost:8000/compound/CHEMBL25?use_cache=true
```

**Response:** Same as compound lookup

---

### Cache Management

#### `GET /cache/stats` - Get Cache Statistics
Get current cache performance statistics.

**Response:**
```json
{
  "hits": 15,
  "misses": 8,
  "total": 23,
  "hit_rate": 0.652,
  "size_mb": null
}
```

---

#### `DELETE /cache` - Clear Cache
Clear all cached results.

**Response:** 204 No Content

---

### Tools

#### `GET /tools` - List Available Tools
List all registered tools grouped by category.

**Response:**
```json
{
  "chembl": [
    "chembl_search_by_name",
    "chembl_get_compound",
    "chembl_similarity_search",
    "chembl_substructure_search",
    "chembl_get_activities"
  ],
  "rdkit": [
    "rdkit_standardize_smiles",
    "rdkit_calc_properties",
    "rdkit_calc_lipinski",
    "rdkit_convert_format",
    "rdkit_extract_scaffold"
  ],
  "uniprot": [
    "uniprot_get_protein",
    "uniprot_search"
  ],
  "other": [
    "filter_by_properties"
  ],
  "total": 13
}
```

---

## Error Handling

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 204 | Success (No Content) |
| 422 | Validation Error |
| 500 | Internal Server Error |
| 503 | Service Unavailable |

### Error Response Format

```json
{
  "error": "Validation error",
  "detail": "Invalid SMILES string",
  "timestamp": "2026-01-09T12:00:00"
}
```

---

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `CHEMAGENT_PORT` | Server port | 8000 |
| `CHEMAGENT_HOST` | Server host | 0.0.0.0 |
| `CHEMAGENT_USE_REAL_TOOLS` | Use real APIs | true |
| `CHEMAGENT_ENABLE_CACHE` | Enable caching | true |
| `CHEMAGENT_CACHE_DIR` | Cache directory | .cache/chemagent |
| `CHEMAGENT_CACHE_TTL` | Cache TTL (seconds) | 3600 |

---

## Usage Examples

### Python Client

```python
import requests

# Initialize base URL
BASE_URL = "http://localhost:8000"

# Example 1: Compound lookup
response = requests.post(
    f"{BASE_URL}/query",
    json={"query": "What is CHEMBL25?"}
)
data = response.json()
print(f"Compound: {data['result']['compound']['preferred_name']}")

# Example 2: Property calculation
response = requests.post(
    f"{BASE_URL}/compound/properties",
    json={"smiles": "CC(=O)Oc1ccccc1C(=O)O"}
)
props = response.json()["result"]["properties"]
print(f"MW: {props['mw']}, LogP: {props['alogp']}")

# Example 3: Similarity search
response = requests.post(
    f"{BASE_URL}/compound/similar",
    json={
        "smiles": "CC(=O)Oc1ccccc1C(=O)O",
        "threshold": 0.8,
        "limit": 5
    }
)
similar = response.json()["result"]["similar_compounds"]
for compound in similar:
    print(f"{compound['chembl_id']}: {compound['similarity']:.2f}")

# Example 4: Verbose mode for debugging
response = requests.post(
    f"{BASE_URL}/query",
    json={
        "query": "Calculate properties of aspirin",
        "verbose": True
    }
)
details = response.json()["details"]
print(f"Plan steps: {details['plan']['num_steps']}")
print(f"Cache hit rate: {details['cache_stats']['hit_rate']:.1%}")
```

### JavaScript/TypeScript Client

```javascript
const BASE_URL = 'http://localhost:8000';

// Example 1: Compound lookup
async function lookupCompound(query) {
  const response = await fetch(`${BASE_URL}/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query })
  });
  const data = await response.json();
  return data;
}

// Example 2: Property calculation
async function calcProperties(smiles) {
  const response = await fetch(`${BASE_URL}/compound/properties`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ smiles, use_cache: true })
  });
  const data = await response.json();
  return data.result.properties;
}

// Usage
const result = await lookupCompound('What is CHEMBL25?');
console.log(result.result.compound.preferred_name);

const props = await calcProperties('CC(=O)Oc1ccccc1C(=O)O');
console.log(`MW: ${props.mw}, LogP: ${props.alogp}`);
```

### cURL Examples

```bash
# Compound lookup
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is CHEMBL25?"}'

# Property calculation
curl -X POST http://localhost:8000/compound/properties \
  -H "Content-Type: application/json" \
  -d '{"smiles": "CC(=O)Oc1ccccc1C(=O)O"}'

# Similarity search
curl -X POST http://localhost:8000/compound/similar \
  -H "Content-Type: application/json" \
  -d '{"smiles": "CC(=O)Oc1ccccc1C(=O)O", "threshold": 0.8}'

# GET compound by ID
curl http://localhost:8000/compound/CHEMBL25

# Cache statistics
curl http://localhost:8000/cache/stats

# Clear cache
curl -X DELETE http://localhost:8000/cache

# List tools
curl http://localhost:8000/tools
```

---

## Testing

### Run API Tests

```bash
# Start the server first
./start_api.sh

# In another terminal, run tests
crun -p ~/envs/chemagent python tests/test_api.py
```

### Expected Output

```
ChemAgent API Test Suite
======================================================================
Server: http://localhost:8000
Started: 2026-01-09 12:00:00

======================================================================
Test: Root Endpoint
======================================================================
Status: 200
{
  "name": "ChemAgent API",
  "version": "1.0.0",
  ...
}
✓ SUCCESS

...

Test Summary
======================================================================
✓ PASS: Root Endpoint
✓ PASS: Health Check
✓ PASS: Query: Compound Lookup
✓ PASS: Query: Property Calculation
...

13/13 tests passed (100.0%)

🎉 All tests passed!
```

---

## OpenAPI Documentation

Interactive API documentation is automatically available at:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

These provide:
- Complete endpoint documentation
- Request/response schemas
- Interactive API testing
- Code generation examples

---

## Performance

### Caching Benefits

| Query Type | Without Cache | With Cache | Speedup |
|------------|---------------|------------|---------|
| Compound lookup | 18ms | 1ms | 18x |
| Property calc | 15ms | 1ms | 15x |
| Similarity search | 250ms | 1ms | 250x |

### Benchmarks

- **Throughput**: ~50 requests/second (single worker)
- **Latency**: <20ms for cached queries, <500ms for complex queries
- **Memory**: ~200MB baseline, +5MB per 1000 cached results

---

## Troubleshooting

### Server won't start

```bash
# Check if port is in use
lsof -i :8000

# Try different port
./start_api.sh --port 8080
```

### Import errors

```bash
# Reinstall dependencies
crun -p ~/envs/chemagent pip install -r requirements.txt
```

### API not responding

```bash
# Check server logs
# Check health endpoint
curl http://localhost:8000/health

# Verify ChemAgent initialization
crun -p ~/envs/chemagent python -c "from chemagent.api.server import state; state.initialize(); print('OK')"
```

---

## Production Deployment

### Gunicorn (Production WSGI Server)

```bash
# Install gunicorn
crun -p ~/envs/chemagent pip install gunicorn

# Run with multiple workers
gunicorn chemagent.api.server:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile - \
  --error-logfile -
```

### Docker Deployment

See `docker/` directory for Dockerfile and docker-compose.yml

---

## License

MIT License - See LICENSE file for details
