"""
FastAPI server for ChemAgent pharmaceutical research assistant.

Provides REST API endpoints for:
- Natural language query processing
- Compound lookups and searches
- Property calculations
- Similarity searches
- Cache management

Run with: uvicorn chemagent.api.server:app --reload
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
import traceback
import os
import json
import asyncio

from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field, validator

from chemagent.core.intent_parser import IntentParser
from chemagent.core.query_planner import QueryPlanner
from chemagent.core.executor import QueryExecutor, ToolRegistry
from chemagent.caching import ResultCache, add_caching_to_registry
from chemagent.config import get_config, load_dotenv_if_exists


# ============================================================================
# Pydantic Models
# ============================================================================

class QueryRequest(BaseModel):
    """Natural language query request"""
    query: str = Field(..., description="Natural language query", min_length=1, max_length=500)
    use_cache: bool = Field(True, description="Enable result caching")
    verbose: bool = Field(False, description="Include execution details")
    enable_parallel: bool = Field(True, description="Enable parallel execution for independent steps")
    max_workers: int = Field(4, description="Maximum parallel workers", ge=1, le=16)
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "What is CHEMBL25?",
                "use_cache": True,
                "verbose": False,
                "enable_parallel": True,
                "max_workers": 4
            }
        }


class CompoundLookupRequest(BaseModel):
    """Direct compound lookup by ID or name"""
    identifier: str = Field(..., description="ChEMBL ID or compound name")
    use_cache: bool = Field(True, description="Enable result caching")
    
    class Config:
        json_schema_extra = {
            "example": {
                "identifier": "CHEMBL25",
                "use_cache": True
            }
        }


class PropertyCalculationRequest(BaseModel):
    """Calculate molecular properties"""
    smiles: str = Field(..., description="SMILES string")
    use_cache: bool = Field(True, description="Enable result caching")
    
    @validator('smiles')
    def validate_smiles(cls, v):
        if not v or len(v) < 2:
            raise ValueError("Invalid SMILES string")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "smiles": "CC(=O)Oc1ccccc1C(=O)O",
                "use_cache": True
            }
        }


class SimilaritySearchRequest(BaseModel):
    """Find similar compounds"""
    smiles: str = Field(..., description="Query SMILES string")
    threshold: float = Field(0.7, description="Tanimoto similarity threshold", ge=0.0, le=1.0)
    limit: int = Field(10, description="Maximum number of results", ge=1, le=100)
    use_cache: bool = Field(True, description="Enable result caching")
    
    class Config:
        json_schema_extra = {
            "example": {
                "smiles": "CC(=O)Oc1ccccc1C(=O)O",
                "threshold": 0.7,
                "limit": 10,
                "use_cache": True
            }
        }


class QueryResponse(BaseModel):
    """Response from query processing"""
    status: str = Field(..., description="Query status: success, error, partial")
    query: str = Field(..., description="Original query")
    intent: Optional[str] = Field(None, description="Detected intent type")
    result: Optional[Dict[str, Any]] = Field(None, description="Query results")
    execution_time_ms: Optional[float] = Field(None, description="Execution time in milliseconds")
    cached: bool = Field(False, description="Whether result was cached")
    error: Optional[str] = Field(None, description="Error message if failed")
    details: Optional[Dict[str, Any]] = Field(None, description="Verbose execution details")


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    timestamp: str
    version: str
    api_available: bool
    cache_enabled: bool
    cache_stats: Optional[Dict[str, Any]] = None


class CacheStatsResponse(BaseModel):
    """Cache statistics response"""
    hits: int
    misses: int
    total: int
    hit_rate: float
    size_mb: Optional[float] = None


class ErrorResponse(BaseModel):
    """Error response"""
    error: str
    detail: Optional[str] = None
    timestamp: str


class BatchQueryRequest(BaseModel):
    """Batch query request"""
    queries: List[str] = Field(..., description="List of queries to process", min_items=1, max_items=100)
    use_cache: bool = Field(True, description="Enable result caching")
    verbose: bool = Field(False, description="Include execution details")
    enable_parallel: bool = Field(True, description="Enable parallel processing")
    max_workers: int = Field(4, description="Maximum parallel workers", ge=1, le=16)
    
    class Config:
        json_schema_extra = {
            "example": {
                "queries": ["What is CHEMBL25?", "Find similar compounds to aspirin"],
                "use_cache": True,
                "verbose": False,
                "enable_parallel": True,
                "max_workers": 4
            }
        }


class BatchQueryResponse(BaseModel):
    """Batch query response"""
    total_queries: int
    successful: int
    failed: int
    total_time_ms: float
    results: List[QueryResponse]


# ============================================================================
# FastAPI Application
# ============================================================================

app = FastAPI(
    title="ChemAgent API",
    description="Pharmaceutical research assistant with natural language interface",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    contact={
        "name": "ChemAgent Team",
        "url": "https://github.com/sdodlapa/ChemAgent",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    }
)

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Application State
# ============================================================================

class ChemAgentState:
    """Global application state"""
    def __init__(self):
        self.parser = None
        self.planner = None
        self.executor = None
        self.cache = None
        self.initialized = False
    
    def initialize(self, use_real_tools: bool = True, enable_cache: bool = True):
        """Initialize ChemAgent components"""
        if self.initialized:
            return
        
        try:
            self.parser = IntentParser()
            self.planner = QueryPlanner()
            
            registry = ToolRegistry(use_real_tools=use_real_tools)
            
            if enable_cache:
                cache_dir = os.getenv("CHEMAGENT_CACHE_DIR", ".cache/chemagent")
                cache_ttl = int(os.getenv("CHEMAGENT_CACHE_TTL", "3600"))
                self.cache = ResultCache(cache_dir=cache_dir, ttl=cache_ttl)
                add_caching_to_registry(registry, self.cache)
            
            self.executor = QueryExecutor(
                registry, 
                enable_parallel=True,
                max_workers=4
            )
            self.initialized = True
            
        except Exception as e:
            raise RuntimeError(f"Failed to initialize ChemAgent: {e}")


state = ChemAgentState()


@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    use_real_tools = os.getenv("CHEMAGENT_USE_REAL_TOOLS", "true").lower() == "true"
    enable_cache = os.getenv("CHEMAGENT_ENABLE_CACHE", "true").lower() == "true"
    state.initialize(use_real_tools=use_real_tools, enable_cache=enable_cache)


def get_chemagent():
    """Get ChemAgent state (for testing)"""
    return state


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/", response_model=Dict[str, str])
async def root():
    """Root endpoint with API information"""
    return {
        "name": "ChemAgent API",
        "version": "1.0.0",
        "description": "Pharmaceutical research assistant",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    cache_stats = None
    if state.cache:
        stats = state.cache.get_statistics()
        cache_stats = {
            "hits": stats["hits"],
            "misses": stats["misses"],
            "hit_rate": stats["hit_rate"]
        }
    
    return HealthResponse(
        status="healthy" if state.initialized else "initializing",
        timestamp=datetime.utcnow().isoformat(),
        version="1.0.0",
        api_available=state.initialized,
        cache_enabled=state.cache is not None,
        cache_stats=cache_stats
    )


@app.post("/query", response_model=QueryResponse, status_code=status.HTTP_200_OK)
async def process_query(request: QueryRequest):
    """
    Process a natural language query.
    
    Supports queries like:
    - "What is CHEMBL25?"
    - "Calculate properties of aspirin"
    - "Find compounds similar to CC(=O)O"
    - "Check Lipinski for CHEMBL25"
    """
    if not state.initialized:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service is initializing"
        )
    
    try:
        import time
        start_time = time.time()
        
        # Parse query
        parsed = state.parser.parse(request.query)
        
        # Plan execution
        plan = state.planner.plan(parsed)
        
        # Create executor with request settings
        executor = QueryExecutor(
            state.executor.tool_registry,
            enable_parallel=request.enable_parallel,
            max_workers=request.max_workers
        )
        
        # Execute
        result = executor.execute(plan)
        
        execution_time = (time.time() - start_time) * 1000
        
        # Build response
        response_data = {
            "status": result.status,
            "query": request.query,
            "intent": parsed.intent_type.value,
            "result": result.result,
            "execution_time_ms": execution_time,
            "cached": False,  # TODO: Track cache hits in execution
            "error": result.error
        }
        
        if request.verbose:
            response_data["details"] = {
                "parsed_intent": {
                    "type": parsed.intent_type.value,
                    "entities": parsed.entities,
                    "constraints": parsed.constraints
                },
                "plan": {
                    "num_steps": len(plan.steps),
                    "steps": [
                        {
                            "tool": step.tool_name,
                            "dependencies": step.dependencies
                        }
                        for step in plan.steps
                    ]
                },
                "parallel_metrics": result.parallel_metrics,
                "cache_stats": state.cache.get_statistics() if state.cache else None
            }
        
        return QueryResponse(**response_data)
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query processing failed: {str(e)}"
        )


@app.post("/compound/lookup", response_model=QueryResponse)
async def lookup_compound(request: CompoundLookupRequest):
    """
    Look up a compound by ChEMBL ID or name.
    
    Examples:
    - CHEMBL25
    - aspirin
    - ibuprofen
    """
    query = f"What is {request.identifier}?"
    return await process_query(QueryRequest(
        query=query,
        use_cache=request.use_cache,
        verbose=False
    ))


@app.post("/compound/properties", response_model=QueryResponse)
async def calculate_properties(request: PropertyCalculationRequest):
    """
    Calculate molecular properties for a SMILES string.
    
    Returns: MW, LogP, H-donors, H-acceptors, PSA, rotatable bonds, etc.
    """
    query = f"Calculate properties of {request.smiles}"
    return await process_query(QueryRequest(
        query=query,
        use_cache=request.use_cache,
        verbose=False
    ))


@app.post("/compound/similar", response_model=QueryResponse)
async def find_similar(request: SimilaritySearchRequest):
    """
    Find compounds similar to the query SMILES.
    
    Uses Tanimoto similarity with configurable threshold.
    """
    query = f"Find compounds similar to {request.smiles} with threshold {request.threshold}"
    return await process_query(QueryRequest(
        query=query,
        use_cache=request.use_cache,
        verbose=False
    ))


@app.get("/compound/{chembl_id}", response_model=QueryResponse)
async def get_compound(
    chembl_id: str,
    use_cache: bool = Query(True, description="Enable caching")
):
    """
    Get compound information by ChEMBL ID.
    
    Example: /compound/CHEMBL25
    """
    query = f"What is {chembl_id}?"
    return await process_query(QueryRequest(
        query=query,
        use_cache=use_cache,
        verbose=False
    ))


@app.get("/cache/stats", response_model=CacheStatsResponse)
async def get_cache_stats():
    """Get cache statistics"""
    if not state.cache:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Caching is not enabled"
        )
    
    stats = state.cache.get_statistics()
    return CacheStatsResponse(
        hits=stats["hits"],
        misses=stats["misses"],
        total=stats["total"],
        hit_rate=stats["hit_rate"]
    )


@app.delete("/cache", status_code=status.HTTP_204_NO_CONTENT)
async def clear_cache():
    """Clear all cached results"""
    if not state.cache:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Caching is not enabled"
        )
    
    state.cache.clear()
    return None


@app.get("/tools", response_model=Dict[str, List[str]])
async def list_tools():
    """List available tools"""
    if not state.initialized:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service is initializing"
        )
    
    tools = list(state.executor.registry.tools.keys())
    
    # Group tools by category
    chembl_tools = [t for t in tools if t.startswith("chembl_")]
    rdkit_tools = [t for t in tools if t.startswith("rdkit_")]
    uniprot_tools = [t for t in tools if t.startswith("uniprot_")]
    other_tools = [t for t in tools if not any(t.startswith(p) for p in ["chembl_", "rdkit_", "uniprot_"])]
    
    return {
        "chembl": chembl_tools,
        "rdkit": rdkit_tools,
        "uniprot": uniprot_tools,
        "other": other_tools,
        "total": len(tools)
    }


# ============================================================================
# Error Handlers
# ============================================================================

@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    """Handle validation errors"""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(
            error="Validation error",
            detail=str(exc),
            timestamp=datetime.utcnow().isoformat()
        ).dict()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle unexpected errors"""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="Internal server error",
            detail=str(exc),
            timestamp=datetime.utcnow().isoformat()
        ).dict()
    )


# ============================================================================
# Main Entry Point (for development)
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("CHEMAGENT_PORT", "8000"))
    host = os.getenv("CHEMAGENT_HOST", "0.0.0.0")
    
    print(f"Starting ChemAgent API server on {host}:{port}")
    print(f"API docs: http://{host}:{port}/docs")
    
    uvicorn.run(
        "chemagent.api.server:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )


# ============================================================================
# Streaming API
# ============================================================================

@app.post("/query/stream")
async def query_stream(request: QueryRequest):
    """
    Stream query execution with real-time progress updates.
    
    Returns Server-Sent Events (SSE) with execution progress.
    """
    if not state.initialized:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service is initializing"
        )
    
    async def event_generator():
        """Generate SSE events for query execution"""
        try:
            # Parse intent
            yield f"data: {json.dumps({'status': 'parsing', 'message': 'Parsing query...'})}\n\n"
            await asyncio.sleep(0.1)  # Allow client to receive
            
            parsed = state.intent_parser.parse(request.query)
            yield f"data: {json.dumps({'status': 'parsed', 'intent': parsed.intent_type, 'entities': len(parsed.entities)})}\n\n"
            
            # Plan query
            yield f"data: {json.dumps({'status': 'planning', 'message': 'Creating execution plan...'})}\n\n"
            await asyncio.sleep(0.1)
            
            plan = state.query_planner.plan(parsed)
            yield f"data: {json.dumps({'status': 'planned', 'steps': len(plan.steps), 'parallel_groups': len(plan.get_parallel_groups())})}\n\n"
            
            # Execute steps
            result = state.executor.execute_plan(
                plan,
                enable_parallel=request.enable_parallel,
                max_workers=request.max_workers
            )
            
            # Send progress updates (simulated - in real impl, executor would yield progress)
            for i, step in enumerate(plan.steps):
                yield f"data: {json.dumps({'status': 'executing', 'step': i + 1, 'total': len(plan.steps), 'tool': step.tool})}\n\n"
                await asyncio.sleep(0.1)
            
            # Send final result
            response_data = {
                "status": "complete",
                "result": result["result"],
                "success": result.get("success", True)
            }
            
            if request.verbose:
                response_data["metadata"] = {
                    "intent": parsed.intent_type,
                    "steps": len(plan.steps),
                    "execution_time_ms": result.get("execution_time_ms", 0)
                }
            
            yield f"data: {json.dumps(response_data)}\n\n"
            
        except Exception as e:
            error_data = {
                "status": "error",
                "error": str(e),
                "traceback": traceback.format_exc() if request.verbose else None
            }
            yield f"data: {json.dumps(error_data)}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )


# ============================================================================
# Batch Processing Endpoint
# ============================================================================

@app.post("/batch", response_model=BatchQueryResponse, status_code=status.HTTP_200_OK)
async def process_batch_queries(request: BatchQueryRequest) -> BatchQueryResponse:
    """Process multiple queries in batch with optional parallelization.
    
    This endpoint allows processing multiple queries efficiently,
    with support for parallel execution and result caching.
    
    Args:
        request: Batch query request with list of queries
        
    Returns:
        BatchQueryResponse with all results
        
    Example:
        ```json
        {
            "queries": [
                "What is CHEMBL25?",
                "Find similar compounds to aspirin",
                "Get properties for caffeine"
            ],
            "enable_parallel": true,
            "max_workers": 4
        }
        ```
    """
    start_time = datetime.now()
    results = []
    successful = 0
    failed = 0
    
    async def process_single_query(query: str) -> QueryResponse:
        """Process a single query"""
        try:
            # Parse intent
            intent_result = intent_parser.parse(query)
            
            # Plan execution
            plan = planner.plan(intent_result)
            
            # Execute plan
            execution_start = datetime.now()
            result = await asyncio.to_thread(
                executor.execute,
                plan,
                use_cache=request.use_cache
            )
            execution_time = (datetime.now() - execution_start).total_seconds() * 1000
            
            response = QueryResponse(
                status="success" if result.get("success") else "error",
                query=query,
                intent=intent_result.intent_type,
                result=result,
                execution_time_ms=execution_time,
                cached=result.get("cached", False),
                error=result.get("error"),
                details={"steps": result.get("steps", [])} if request.verbose else None
            )
            
            return response
            
        except Exception as e:
            return QueryResponse(
                status="error",
                query=query,
                error=str(e),
                execution_time_ms=0
            )
    
    # Process queries
    if request.enable_parallel and len(request.queries) > 1:
        # Parallel processing
        tasks = [process_single_query(q) for q in request.queries]
        results = await asyncio.gather(*tasks)
    else:
        # Sequential processing
        for query in request.queries:
            result = await process_single_query(query)
            results.append(result)
    
    # Count successes and failures
    for result in results:
        if result.status == "success":
            successful += 1
        else:
            failed += 1
    
    total_time = (datetime.now() - start_time).total_seconds() * 1000
    
    return BatchQueryResponse(
        total_queries=len(request.queries),
        successful=successful,
        failed=failed,
        total_time_ms=total_time,
        results=results
    )


# ============================================================================
# Configuration Endpoint
# ============================================================================

@app.get("/config")
async def get_server_config():
    """Get server configuration (non-sensitive fields only)"""
    config = get_config()
    
    return {
        "server": {
            "port": config.port,
            "workers": config.workers
        },
        "features": {
            "parallel_execution": config.enable_parallel,
            "max_workers": config.max_workers,
            "caching": config.cache_enabled,
            "streaming": config.enable_streaming,
            "metrics": config.enable_metrics
        },
        "limits": {
            "rate_limit_per_minute": config.rate_limit_per_minute,
            "auth_enabled": config.enable_auth
        }
    }


# ============================================================================
# Startup: Load Configuration
# ============================================================================

@app.on_event("startup")
async def load_configuration():
    """Load configuration on startup"""
    # Try to load .env file
    load_dotenv_if_exists()
    
    # Validate configuration
    config = get_config()
    print(f"✓ Configuration loaded successfully")
    print(f"  - Server: {config.host}:{config.port}")
    print(f"  - Workers: {config.workers}")
    print(f"  - Parallel execution: {config.enable_parallel} (max workers: {config.max_workers})")
    print(f"  - Caching: {config.cache_enabled}")
    print(f"  - Streaming: {config.enable_streaming}")
    print(f"  - Metrics: {config.enable_metrics}")
    print(f"  - Auth: {config.enable_auth}")

