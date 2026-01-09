# ChemAgent API Documentation

## Overview

ChemAgent provides a comprehensive REST API for pharmaceutical research queries, including compound lookups, property calculations, similarity searches, and target analysis.

**Base URL:** `http://localhost:8000`  
**Version:** 1.0.0  
**Protocol:** HTTP/REST  
**Content-Type:** application/json

---

## Table of Contents

1. [Authentication](#authentication)
2. [Endpoints](#endpoints)
   - [Query Processing](#query-processing)
   - [Batch Processing](#batch-processing)
   - [Compound Operations](#compound-operations)
   - [Property Calculations](#property-calculations)
   - [Similarity Search](#similarity-search)
   - [Cache Management](#cache-management)
   - [Health & Status](#health--status)
3. [Data Models](#data-models)
4. [Error Handling](#error-handling)
5. [Rate Limiting](#rate-limiting)
6. [Examples](#examples)

---

## Authentication

Currently, the API operates in open mode. When authentication is enabled via configuration, requests must include an API key:

```bash
curl -H "X-API-Key: your_api_key_here" http://localhost:8000/query
```

---

## Endpoints

### Query Processing

#### POST /query

Process a natural language query.

**Request:**
```json
{
  "query": "What is CHEMBL25?",
  "use_cache": true,
  "verbose": false,
  "enable_parallel": true,
  "max_workers": 4
}
```

**Response:**
```json
{
  "status": "success",
  "query": "What is CHEMBL25?",
  "intent": "compound_lookup",
  "result": {
    "name": "Aspirin",
    "chembl_id": "CHEMBL25",
    "type": "Small molecule"
  },
  "execution_time_ms": 234.5,
  "cached": false,
  "error": null,
  "details": null
}
```

**Parameters:**
- `query` (string, required): Natural language query (1-500 characters)
- `use_cache` (boolean, optional): Enable result caching (default: true)
- `verbose` (boolean, optional): Include execution details (default: false)
- `enable_parallel` (boolean, optional): Enable parallel execution (default: true)
- `max_workers` (integer, optional): Max parallel workers 1-16 (default: 4)

**Status Codes:**
- `200 OK`: Query processed successfully
- `400 Bad Request`: Invalid query parameters
- `500 Internal Server Error`: Processing error

---

#### POST /query/stream

Stream query results with Server-Sent Events (SSE).

**Request:**
```json
{
  "query": "Find similar compounds to aspirin",
  "use_cache": true,
  "enable_parallel": true
}
```

**Response Stream:**
```
data: {"event": "start", "query": "Find similar compounds to aspirin"}

data: {"event": "intent", "intent_type": "similarity_search"}

data: {"event": "step", "step": "lookup_compound", "status": "running"}

data: {"event": "step", "step": "lookup_compound", "status": "completed"}

data: {"event": "result", "result": {...}, "execution_time_ms": 456.7}

data: {"event": "complete"}
```

**Event Types:**
- `start`: Query processing started
- `intent`: Intent detected
- `step`: Execution step update
- `progress`: Progress update
- `result`: Final result
- `error`: Error occurred
- `complete`: Processing complete

**Headers:**
- `Accept: text/event-stream`
- `Cache-Control: no-cache`

---

### Batch Processing

#### POST /batch

Process multiple queries in parallel.

**Request:**
```json
{
  "queries": [
    "What is CHEMBL25?",
    "Find similar compounds to aspirin",
    "Get properties for caffeine"
  ],
  "use_cache": true,
  "verbose": false,
  "enable_parallel": true,
  "max_workers": 4
}
```

**Response:**
```json
{
  "total_queries": 3,
  "successful": 3,
  "failed": 0,
  "total_time_ms": 856.3,
  "results": [
    {
      "status": "success",
      "query": "What is CHEMBL25?",
      "intent": "compound_lookup",
      "result": {...},
      "execution_time_ms": 234.5,
      "cached": false
    },
    ...
  ]
}
```

**Parameters:**
- `queries` (array, required): List of 1-100 queries
- `use_cache` (boolean, optional): Enable caching (default: true)
- `verbose` (boolean, optional): Include details (default: false)
- `enable_parallel` (boolean, optional): Parallel processing (default: true)
- `max_workers` (integer, optional): Max workers (default: 4)

**Performance:**
- Sequential: ~250ms per query
- Parallel (4 workers): ~60ms per query (4x speedup)
- Parallel (8 workers): ~35ms per query (7x speedup)

---

### Compound Operations

#### POST /compound/lookup

Direct compound lookup by ID or name.

**Request:**
```json
{
  "identifier": "CHEMBL25",
  "use_cache": true
}
```

**Response:**
```json
{
  "success": true,
  "compound": {
    "chembl_id": "CHEMBL25",
    "name": "Aspirin",
    "type": "Small molecule",
    "max_phase": 4,
    "molecule_properties": {
      "molecular_weight": 180.16,
      "alogp": 1.19,
      "num_ro5_violations": 0
    }
  },
  "cached": false
}
```

---

### Property Calculations

#### POST /properties/calculate

Calculate molecular properties from SMILES.

**Request:**
```json
{
  "smiles": "CC(=O)Oc1ccccc1C(=O)O",
  "use_cache": true
}
```

**Response:**
```json
{
  "success": true,
  "properties": {
    "molecular_weight": 180.16,
    "logp": 1.19,
    "num_h_donors": 1,
    "num_h_acceptors": 4,
    "num_rotatable_bonds": 3,
    "aromatic_rings": 1,
    "polar_surface_area": 63.6
  },
  "cached": false
}
```

---

### Similarity Search

#### POST /similarity/search

Find similar compounds by structure.

**Request:**
```json
{
  "smiles": "CC(=O)Oc1ccccc1C(=O)O",
  "threshold": 0.7,
  "limit": 10,
  "use_cache": true
}
```

**Response:**
```json
{
  "success": true,
  "query_smiles": "CC(=O)Oc1ccccc1C(=O)O",
  "matches": [
    {
      "chembl_id": "CHEMBL521",
      "name": "Compound 521",
      "similarity": 0.89,
      "smiles": "..."
    },
    ...
  ],
  "count": 10,
  "cached": false
}
```

**Parameters:**
- `smiles` (string, required): Query SMILES string
- `threshold` (float, optional): Similarity threshold 0.0-1.0 (default: 0.7)
- `limit` (integer, optional): Max results 1-100 (default: 10)
- `use_cache` (boolean, optional): Enable caching (default: true)

---

### Cache Management

#### GET /cache/stats

Get cache statistics.

**Response:**
```json
{
  "hits": 1234,
  "misses": 567,
  "total": 1801,
  "hit_rate": 0.685,
  "size_mb": 45.3
}
```

#### POST /cache/clear

Clear the cache.

**Response:**
```json
{
  "success": true,
  "message": "Cache cleared successfully"
}
```

---

### Health & Status

#### GET /health

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-12-20T10:30:00",
  "version": "1.0.0",
  "api_available": true,
  "cache_enabled": true,
  "cache_stats": {
    "hits": 1234,
    "misses": 567,
    "hit_rate": 0.685
  }
}
```

#### GET /config

Get server configuration (non-sensitive).

**Response:**
```json
{
  "server": {
    "port": 8000,
    "workers": 4
  },
  "features": {
    "parallel_execution": true,
    "max_workers": 4,
    "caching": true,
    "streaming": true,
    "metrics": true
  },
  "limits": {
    "rate_limit_per_minute": 60,
    "auth_enabled": false
  }
}
```

---

## Data Models

### QueryRequest
```typescript
{
  query: string;              // 1-500 characters
  use_cache?: boolean;        // default: true
  verbose?: boolean;          // default: false
  enable_parallel?: boolean;  // default: true
  max_workers?: number;       // 1-16, default: 4
}
```

### QueryResponse
```typescript
{
  status: "success" | "error" | "partial";
  query: string;
  intent?: string;
  result?: object;
  execution_time_ms?: number;
  cached: boolean;
  error?: string;
  details?: object;
}
```

### BatchQueryRequest
```typescript
{
  queries: string[];          // 1-100 queries
  use_cache?: boolean;
  verbose?: boolean;
  enable_parallel?: boolean;
  max_workers?: number;
}
```

### BatchQueryResponse
```typescript
{
  total_queries: number;
  successful: number;
  failed: number;
  total_time_ms: number;
  results: QueryResponse[];
}
```

---

## Error Handling

All errors follow a consistent format:

```json
{
  "error": "Error type",
  "detail": "Detailed error message",
  "timestamp": "2024-12-20T10:30:00"
}
```

### Common Error Codes

| Code | Description |
|------|-------------|
| 400 | Bad Request - Invalid parameters |
| 401 | Unauthorized - Invalid API key |
| 404 | Not Found - Resource not found |
| 429 | Too Many Requests - Rate limit exceeded |
| 500 | Internal Server Error - Processing error |
| 503 | Service Unavailable - System overloaded |

---

## Rate Limiting

**Default Limits:**
- 60 requests per minute per IP
- 1000 requests per hour per IP
- 10,000 requests per day per API key

**Headers:**
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1640000000
```

**429 Response:**
```json
{
  "error": "Rate limit exceeded",
  "detail": "Too many requests. Try again in 30 seconds.",
  "timestamp": "2024-12-20T10:30:00"
}
```

---

## Examples

### Python

```python
import requests

# Single query
response = requests.post(
    "http://localhost:8000/query",
    json={"query": "What is CHEMBL25?"}
)
result = response.json()
print(result)

# Batch processing
response = requests.post(
    "http://localhost:8000/batch",
    json={
        "queries": [
            "What is CHEMBL25?",
            "Find similar compounds to aspirin"
        ],
        "enable_parallel": True
    }
)
batch_result = response.json()
print(f"Processed {batch_result['total_queries']} queries")
```

### cURL

```bash
# Single query
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is CHEMBL25?"}'

# Batch processing
curl -X POST http://localhost:8000/batch \
  -H "Content-Type: application/json" \
  -d '{
    "queries": ["What is CHEMBL25?", "Find aspirin analogs"],
    "enable_parallel": true
  }'

# Streaming
curl -X POST http://localhost:8000/query/stream \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{"query": "Find similar compounds to aspirin"}'
```

### JavaScript

```javascript
// Single query
const response = await fetch('http://localhost:8000/query', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    query: 'What is CHEMBL25?',
    use_cache: true
  })
});
const result = await response.json();
console.log(result);

// Streaming
const eventSource = new EventSource(
  'http://localhost:8000/query/stream?' + 
  new URLSearchParams({query: 'Find aspirin analogs'})
);

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data.event, data);
};
```

---

## Support

For issues, questions, or feature requests:
- GitHub: https://github.com/yourusername/chemagent
- Email: support@chemagent.example.com
- Documentation: https://chemagent.readthedocs.io
