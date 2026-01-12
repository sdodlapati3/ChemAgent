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

from dataclasses import asdict, is_dataclass
from datetime import datetime
from typing import Dict, List, Optional, Any
import traceback
import os
import json
import asyncio
import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, validator

# =============================================================================
# Logging Configuration - Write to file and console
# =============================================================================
LOG_DIR = Path(__file__).parent.parent.parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "chemagent.log"

# Configure root logger to capture all module logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler(LOG_FILE, mode='a'),
        logging.StreamHandler()
    ]
)

# Set specific loggers
logging.getLogger("chemagent").setLevel(logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)  # Reduce noise
logging.getLogger("uvicorn").setLevel(logging.INFO)

logger = logging.getLogger(__name__)


def to_serializable(obj: Any) -> Any:
    """Convert dataclasses and other objects to JSON-serializable format."""
    if is_dataclass(obj) and not isinstance(obj, type):
        return {k: to_serializable(v) for k, v in asdict(obj).items()}
    elif isinstance(obj, dict):
        return {k: to_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [to_serializable(item) for item in obj]
    elif isinstance(obj, datetime):
        return obj.isoformat()
    else:
        return obj


from chemagent.core.intent_parser import IntentParser
from chemagent.core.query_planner import QueryPlanner
from chemagent.core.executor import QueryExecutor, ToolRegistry
from chemagent.core.response_formatter import ResponseFormatter
from chemagent.caching import ResultCache, add_caching_to_registry
from chemagent.config import get_config, load_dotenv_if_exists

# Import OptimalAgent (new hybrid architecture)
try:
    from chemagent.core.optimal_agent import OptimalAgent, LITELLM_AVAILABLE as AGENT_AVAILABLE
except ImportError:
    OptimalAgent = None
    AGENT_AVAILABLE = False

# Import Multi-Agent Orchestration System
try:
    from chemagent.core.multi_agent import (
        CoordinatorAgent,
        create_multi_agent_system,
        LITELLM_AVAILABLE as MULTI_AGENT_AVAILABLE
    )
except ImportError:
    CoordinatorAgent = None
    create_multi_agent_system = None
    MULTI_AGENT_AVAILABLE = False

# Static files directory
STATIC_DIR = Path(__file__).parent / "static"


# ============================================================================
# Pydantic Models
# ============================================================================


# ============================================================================
# Pydantic Models
# ============================================================================

class QueryRequest(BaseModel):
    """Natural language query request"""
    query: str = Field(..., description="Natural language query", min_length=1, max_length=500)
    session_id: Optional[str] = Field(None, description="Session ID for conversation memory")
    use_cache: bool = Field(True, description="Enable result caching")
    verbose: bool = Field(False, description="Include execution details")
    enable_parallel: bool = Field(True, description="Enable parallel execution for independent steps")
    max_workers: int = Field(4, description="Maximum parallel workers", ge=1, le=16)
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "What is CHEMBL25?",
                "session_id": "abc123",
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


class MultiAgentQueryRequest(BaseModel):
    """Multi-agent orchestration query request"""
    query: str = Field(..., description="Natural language query", min_length=1, max_length=1000)
    session_id: Optional[str] = Field(None, description="Session ID for conversation memory")
    verbose: bool = Field(False, description="Include detailed agent execution info")
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "Find compounds similar to aspirin with IC50 < 100nM",
                "session_id": "session-123",
                "verbose": True
            }
        }


class MultiAgentQueryResponse(BaseModel):
    """Multi-agent orchestration response"""
    success: bool
    query: str
    answer: str
    orchestration_type: str
    tasks_executed: int
    agents_used: List[str]
    execution_time_ms: float
    error: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


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
        self.formatter = None
        self.cache = None
        self.agent = None  # OptimalAgent (hybrid architecture)
        self.coordinator = None  # Multi-agent coordinator (Nemotron)
        self.initialized = False
        self.llm_enabled = False
        self.agent_mode = False  # Use OptimalAgent instead of pattern parser
        self.multi_agent_mode = False  # Multi-agent orchestration available
    
    def initialize(self, use_real_tools: bool = True, enable_cache: bool = True, enable_llm: bool = True):
        """Initialize ChemAgent components"""
        if self.initialized:
            return
        
        try:
            # Initialize tool registry first (needed by both paths)
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
            
            # Try to use OptimalAgent (hybrid architecture)
            use_agent = os.getenv("CHEMAGENT_USE_AGENT", "true").lower() == "true"
            
            if AGENT_AVAILABLE and OptimalAgent and enable_llm and use_agent:
                try:
                    self.agent = OptimalAgent(tool_registry=registry)
                    self.agent_mode = True
                    self.llm_enabled = True
                    import logging
                    logging.getLogger(__name__).info(
                        "OptimalAgent enabled (hybrid tiered + verification)"
                    )
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).warning(
                        "OptimalAgent initialization failed: %s", e
                    )
                    self.agent_mode = False
            
            # Try to initialize Multi-Agent Coordinator
            use_multi_agent = os.getenv("CHEMAGENT_USE_MULTI_AGENT", "false").lower() == "true"
            
            if MULTI_AGENT_AVAILABLE and create_multi_agent_system and enable_llm and use_multi_agent:
                try:
                    self.coordinator = create_multi_agent_system(tool_registry=registry)
                    self.multi_agent_mode = True
                    import logging
                    logging.getLogger(__name__).info(
                        "Multi-Agent Orchestration enabled (Coordinator + Specialists)"
                    )
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).warning(
                        "Multi-Agent initialization failed: %s", e
                    )
                    self.multi_agent_mode = False
                    logging.getLogger(__name__).info(
                        "OptimalAgent enabled (hybrid tiered + verification)"
                    )
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).warning(
                        "OptimalAgent initialization failed: %s", e
                    )
                    self.agent_mode = False
            
            # Fallback to pattern-based parsing if agent not available
            if not self.agent_mode:
                self.parser = IntentParser()
                self.planner = QueryPlanner()
                import logging
                logging.getLogger(__name__).info(
                    "Fallback mode: Pattern parser + Rule planner"
                )
            
            self.formatter = ResponseFormatter()
            self.initialized = True
            
        except Exception as e:
            raise RuntimeError(f"Failed to initialize ChemAgent: {e}")


state = ChemAgentState()


@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    use_real_tools = os.getenv("CHEMAGENT_USE_REAL_TOOLS", "true").lower() == "true"
    enable_cache = os.getenv("CHEMAGENT_ENABLE_CACHE", "true").lower() == "true"
    enable_llm = os.getenv("CHEMAGENT_ENABLE_LLM", "true").lower() == "true"
    state.initialize(
        use_real_tools=use_real_tools,
        enable_cache=enable_cache,
        enable_llm=enable_llm
    )


def get_chemagent():
    """Get ChemAgent state (for testing)"""
    return state


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main chat UI"""
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        content = index_path.read_text()
        return HTMLResponse(
            content=content, 
            status_code=200,
            headers={"Cache-Control": "no-cache, no-store, must-revalidate"}
        )
    else:
        # Fallback to JSON API info if no static file
        return HTMLResponse(content="""
            <html>
                <head><title>ChemAgent API</title></head>
                <body style="font-family: sans-serif; padding: 2rem;">
                    <h1>🧪 ChemAgent API</h1>
                    <p>Pharmaceutical research assistant API is running.</p>
                    <ul>
                        <li><a href="/docs">API Documentation</a></li>
                        <li><a href="/health">Health Check</a></li>
                    </ul>
                </body>
            </html>
        """, status_code=200)


@app.get("/api/info")
async def api_info():
    """API information endpoint (JSON)"""
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
        stats = state.cache.stats()
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


@app.get("/status")
async def get_status():
    """Get detailed system status including agent mode"""
    agent_stats = None
    if state.agent_mode and state.agent:
        agent_stats = state.agent.get_stats()
    
    coordinator_stats = None
    if state.multi_agent_mode and state.coordinator:
        coordinator_stats = state.coordinator.get_stats()
    
    return {
        "initialized": state.initialized,
        "agent_mode": state.agent_mode,
        "multi_agent_mode": state.multi_agent_mode,
        "llm_enabled": state.llm_enabled,
        "architecture": "multi_agent" if state.multi_agent_mode else ("optimal_agent" if state.agent_mode else "pattern_based"),
        "agent_stats": agent_stats,
        "coordinator_stats": coordinator_stats,
        "cache_enabled": state.cache is not None
    }


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
        
        # Use OptimalAgent if available (hybrid architecture)
        if state.agent_mode and state.agent:
            response = state.agent.process(request.query, session_id=request.session_id)
            
            return QueryResponse(
                status="success" if response.success else "error",
                query=request.query,
                intent=f"optimal_agent/{response.path_used}",
                result={
                    "answer": response.answer,
                    "raw_data": to_serializable(response.tool_results),
                    "session_id": state.agent.session_id  # Return session ID for frontend
                },
                execution_time_ms=response.execution_time_ms,
                cached=False,
                error=response.error,
                details={
                    "tools_used": response.tools_used,
                    "path_used": response.path_used,
                    "confidence": response.confidence,
                    "session_id": state.agent.session_id
                } if request.verbose else None
            )
        
        # Fallback to pattern-based parsing
        # Parse query
        parsed = state.parser.parse(request.query)
        
        # Plan execution
        plan = state.planner.plan(parsed)
        
        # Create executor with request settings
        executor = QueryExecutor(
            tool_registry=state.executor.tool_registry,
            enable_parallel=request.enable_parallel,
            max_workers=request.max_workers
        )
        
        # Execute
        result = executor.execute(plan)
        
        execution_time = (time.time() - start_time) * 1000
        
        # Format the response using ResponseFormatter for human-readable answer
        formatted_answer = state.formatter.format(parsed, result)
        
        # Build response with both raw and formatted data
        response_data = {
            "status": "success" if result.status.value == "completed" else result.status.value,
            "query": request.query,
            "intent": parsed.intent_type.value,
            "result": {
                "answer": formatted_answer,
                "raw_data": result.final_output
            },
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
                            "dependencies": step.depends_on
                        }
                        for step in plan.steps
                    ]
                },
                "parallel_metrics": result.parallel_metrics,
                "cache_stats": state.cache.stats() if state.cache else None
            }
        
        return QueryResponse(**response_data)
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query processing failed: {str(e)}"
        )


@app.post("/query/multi-agent", response_model=MultiAgentQueryResponse)
async def process_multi_agent_query(request: MultiAgentQueryRequest):
    """
    Process a query using multi-agent orchestration.
    
    This endpoint uses a Coordinator agent (powered by Nemotron/larger model) 
    to orchestrate specialist agents:
    - CompoundAgent: Search and lookup compounds
    - ActivityAgent: Bioactivity data (IC50, Ki, targets)
    - PropertyAgent: Calculate molecular properties
    - TargetAgent: Protein/target resolution
    
    Best for complex queries that require multiple data types.
    """
    if not state.initialized:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service is initializing"
        )
    
    # Check if multi-agent is available
    if not state.multi_agent_mode or not state.coordinator:
        # Fall back to regular query processing
        logger.info("Multi-agent not enabled, using OptimalAgent fallback")
        
        # Use OptimalAgent if available
        if state.agent_mode and state.agent:
            response = state.agent.process(request.query, session_id=request.session_id)
            return MultiAgentQueryResponse(
                success=response.success,
                query=request.query,
                answer=response.answer,
                orchestration_type="optimal_agent_fallback",
                tasks_executed=len(response.tools_used),
                agents_used=["optimal_agent"],
                execution_time_ms=response.execution_time_ms,
                error=response.error,
                details={"note": "Multi-agent not enabled, used OptimalAgent"}
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Multi-agent orchestration not available. Set CHEMAGENT_USE_MULTI_AGENT=true"
            )
    
    try:
        import time
        start_time = time.time()
        
        logger.info(f"Multi-Agent Query: {request.query}")
        
        # Process with coordinator
        result = state.coordinator.process(request.query, session_id=request.session_id)
        
        execution_time = (time.time() - start_time) * 1000
        
        return MultiAgentQueryResponse(
            success=result.get("success", False),
            query=request.query,
            answer=result.get("answer", ""),
            orchestration_type=result.get("orchestration", "multi_agent"),
            tasks_executed=result.get("tasks_executed", 0),
            agents_used=result.get("agents_used", []),
            execution_time_ms=result.get("execution_time_ms", execution_time),
            error=result.get("error"),
            details={
                "coordinator_stats": state.coordinator.get_stats()
            } if request.verbose else None
        )
        
    except Exception as e:
        logger.error(f"Multi-agent query failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Multi-agent query processing failed: {str(e)}"
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
    
    stats = state.cache.stats()
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
    
    Progress events include:
    - parsing: Query is being analyzed
    - parsed: Intent and entities extracted
    - planning: Execution plan being created
    - planned: Plan ready with step count
    - executing: Running a specific tool
    - step_complete: A step finished
    - complete: All done with results
    - error: Something went wrong
    
    Example usage with JavaScript:
    ```javascript
    const eventSource = new EventSource('/query/stream', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({query: 'What is aspirin?'})
    });
    eventSource.onmessage = (e) => console.log(JSON.parse(e.data));
    ```
    """
    if not state.initialized:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service is initializing"
        )
    
    # Import here to avoid circular imports
    from chemagent.core.executor import ProgressEvent, get_tool_description
    import queue
    import threading
    
    async def event_generator():
        """Generate SSE events for query execution with real progress"""
        progress_queue = queue.Queue()
        execution_complete = threading.Event()
        execution_result = {"result": None, "error": None}
        
        def progress_callback(event: ProgressEvent):
            """Callback invoked by executor for each progress update"""
            progress_queue.put(event.to_dict())
        
        def run_execution():
            """Run executor in background thread"""
            try:
                # Check if using OptimalAgent
                if state.agent_mode and state.agent:
                    # OptimalAgent mode
                    progress_queue.put({
                        "status": "analyzing",
                        "message": "Analyzing your question..."
                    })
                    
                    # Process with OptimalAgent (include session_id for conversation memory)
                    response = state.agent.process(request.query, session_id=request.session_id)
                    
                    if response.tools_used:
                        progress_queue.put({
                            "status": "executing",
                            "message": f"Executed {len(response.tools_used)} tool(s)",
                            "tools": response.tools_used,
                            "path": response.path_used
                        })
                    
                    # Store result in format compatible with streaming response
                    execution_result["agent_response"] = response
                    
                else:
                    # Pattern-based mode - detailed progress
                    # Parse intent
                    progress_queue.put({
                        "status": "parsing",
                        "message": "Understanding your question..."
                    })
                    
                    parsed = state.parser.parse(request.query)
                    progress_queue.put({
                        "status": "parsed",
                        "intent": parsed.intent_type.value if hasattr(parsed.intent_type, 'value') else str(parsed.intent_type),
                        "entities": len(parsed.entities),
                        "message": f"Identified intent: {parsed.intent_type.value if hasattr(parsed.intent_type, 'value') else parsed.intent_type}"
                    })
                    
                    # Plan query
                    progress_queue.put({
                        "status": "planning",
                        "message": "Creating execution plan..."
                    })
                    
                    plan = state.planner.plan(parsed)
                    step_descriptions = [get_tool_description(s.tool_name) for s in plan.steps]
                    progress_queue.put({
                        "status": "planned",
                        "steps": len(plan.steps),
                        "parallel_groups": len(plan.get_parallel_groups()),
                        "step_descriptions": step_descriptions,
                        "message": f"Plan ready: {len(plan.steps)} steps"
                    })
                    
                    # Execute with progress callback
                    result = state.executor.execute(plan, progress_callback=progress_callback)
                    
                    # Store result
                    execution_result["result"] = result
                
            except Exception as e:
                execution_result["error"] = str(e)
                progress_queue.put({
                    "status": "error",
                    "error": str(e),
                    "traceback": traceback.format_exc() if request.verbose else None
                })
            finally:
                execution_complete.set()
        
        # Start execution in background thread
        exec_thread = threading.Thread(target=run_execution, daemon=True)
        exec_thread.start()
        
        # Yield progress events as they arrive
        while not execution_complete.is_set() or not progress_queue.empty():
            try:
                # Check for new progress events (non-blocking with timeout)
                try:
                    event = progress_queue.get(timeout=0.05)
                    yield f"data: {json.dumps(event, default=str)}\n\n"
                except queue.Empty:
                    pass
                
                # Allow other async tasks to run
                await asyncio.sleep(0.01)
                
            except Exception as e:
                logger.error(f"Error in progress stream: {e}")
                break
        
        # Drain any remaining events
        while not progress_queue.empty():
            try:
                event = progress_queue.get_nowait()
                yield f"data: {json.dumps(event, default=str)}\n\n"
            except queue.Empty:
                break
        
        # Send final result
        result = execution_result.get("result")
        agent_response = execution_result.get("agent_response")
        error = execution_result.get("error")
        
        if error:
            yield f"data: {json.dumps({'status': 'error', 'error': error})}\n\n"
        elif agent_response:
            # LLM Agent response
            response_data = {
                "status": "complete",
                "success": agent_response.success,
                "agent_mode": True,
                "result": {
                    "answer": agent_response.answer,
                    "raw_data": to_serializable(agent_response.tool_results) if agent_response.tool_results else None
                }
            }
            if agent_response.error:
                response_data["error"] = agent_response.error
            
            yield f"data: {json.dumps(response_data)}\n\n"
        elif result:
            # Pattern-based executor result
            from chemagent.core.executor import ExecutionStatus
            response_data = {
                "status": "complete",
                "success": result.status == ExecutionStatus.COMPLETED,
                "execution_time_ms": result.total_duration_ms,
                "steps_completed": result.steps_completed
            }
            
            # Format and include result - include both answer and raw_data
            if result.final_output:
                # Use response formatter if available
                try:
                    formatted = state.formatter.format(
                        result.final_output,
                        state.parser.parse(request.query).intent_type.value
                    )
                    response_data["result"] = {
                        "answer": formatted,
                        "raw_data": to_serializable(result.final_output)
                    }
                except Exception:
                    response_data["result"] = {
                        "answer": None,
                        "raw_data": to_serializable(result.final_output)
                    }
            
            if result.error:
                response_data["error"] = result.error
            
            if request.verbose:
                response_data["metadata"] = {
                    "steps": result.steps_completed,
                    "parallel_metrics": result.parallel_metrics
                }
            
            yield f"data: {json.dumps(response_data)}\n\n"
        
        # Send stream end marker
        yield f"data: {json.dumps({'status': 'stream_end'})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
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

