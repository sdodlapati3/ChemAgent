# ChemAgent Implementation Plan

**Version**: 1.0.0  
**Created**: January 2026  
**Status**: Planning → Development  
**Estimated Effort**: 9 weeks (3 phases × 3 weeks each)

---

## Table of Contents

1. [Overview](#overview)
2. [Phase 1: Foundation (Weeks 1-3)](#phase-1-foundation-weeks-1-3)
3. [Phase 2: Intelligence (Weeks 4-6)](#phase-2-intelligence-weeks-4-6)
4. [Phase 3: Production (Weeks 7-9)](#phase-3-production-weeks-7-9)
5. [File Structure](#file-structure)
6. [Component Specifications](#component-specifications)
7. [Testing Strategy](#testing-strategy)
8. [Success Metrics](#success-metrics)

---

## Overview

### Goals

Build a **production-grade pharmaceutical research assistant** with:
- ✅ Evidence-grounded answers (every claim traced to source)
- ✅ Deterministic chemistry tools (RDKit-powered)
- ✅ Smart LLM orchestration (local + cloud)
- ✅ Comprehensive testing (100+ golden queries)
- ✅ Production deployment (Docker, MCP server)

### Principles

1. **Tools first** - Build deterministic functions before adding LLM
2. **Test-driven** - Write tests alongside code
3. **Incremental** - Each phase delivers usable functionality
4. **BioPipelines-inspired** - Reuse proven architecture patterns

---

## Phase 1: Foundation (Weeks 1-3)

**Goal**: Core chemistry tools + basic orchestration

### Week 1: ChemOps Toolbelt

#### Day 1-2: RDKit Core Functions

**Files to create**:
- `src/chemagent/tools/rdkit_tools.py`
- `tests/unit/test_rdkit_tools.py`

**Functions to implement**:

```python
class RDKitTools:
    """Pure chemistry functions."""
    
    # Day 1
    def standardize_smiles(smiles: str) -> StandardizedResult
    def calc_molecular_properties(mol: Mol) -> PropertyDict
    def calc_lipinski(mol: Mol) -> LipinskiResult
    
    # Day 2
    def similarity_search(query_mol: Mol, mols: List[Mol], threshold: float) -> List[Tuple[Mol, float]]
    def substructure_search(query_smarts: str, mols: List[Mol]) -> List[int]
    def scaffold_extraction(mol: Mol) -> str
```

**Tests** (aim for 30+ tests):
- Valid SMILES → standardized output
- Invalid SMILES → ValueError with clear message
- Edge cases: salts, tautomers, stereochemistry
- Property calculations → known values (aspirin MW = 180.16)
- Similarity: identical molecules → 1.0, random → <0.3

**Success criteria**:
- [x] All 6 functions implemented
- [x] 30+ unit tests passing
- [x] 100% code coverage for core functions
- [x] Documentation with examples

---

#### Day 3-4: Database Clients (ChEMBL)

**Files to create**:
- `src/chemagent/tools/chembl_client.py`
- `tests/unit/test_chembl_client.py`
- `tests/integration/test_chembl_integration.py`

**Client interface**:

```python
class ChEMBLClient:
    """ChEMBL API wrapper with caching and provenance."""
    
    def __init__(self, cache_dir: str = ".cache/chembl")
    
    # Day 3
    def search_by_name(name: str) -> List[CompoundResult]
    def get_compound(chembl_id: str) -> CompoundDetails
    def similarity_search(smiles: str, threshold: float, limit: int) -> List[CompoundResult]
    
    # Day 4
    def get_activities(chembl_id: str, target_type: Optional[str]) -> List[ActivityResult]
    def get_target_info(target_chembl_id: str) -> TargetInfo
```

**Features**:
- Disk cache with TTL (24h default)
- Retry logic with exponential backoff
- Rate limiting (10 req/sec)
- Provenance tracking (ChEMBL ID, timestamp, query params)

**Tests**:
- Unit: Mock API responses, test caching, error handling
- Integration: Real API calls (marked with `@pytest.mark.integration`)

**Success criteria**:
- [x] All 5 methods implemented
- [x] Caching working (2nd call < 10ms)
- [x] Integration tests passing (may require API key)
- [x] Error handling for network failures

---

#### Day 5: BindingDB & UniProt Clients

**Files to create**:
- `src/chemagent/tools/bindingdb_client.py`
- `src/chemagent/tools/uniprot_client.py`
- Tests for both

**BindingDB methods**:
```python
def search_by_target(target_name: str) -> List[AffinityResult]
def get_affinity_data(compound_id: str) -> List[AffinityResult]
```

**UniProt methods**:
```python
def get_protein_info(uniprot_id: str) -> ProteinInfo
def search_proteins(query: str) -> List[ProteinInfo]
```

**Success criteria**:
- [x] Both clients functional
- [x] 20+ tests per client
- [x] Consistent error handling

---

### Week 2: Intent Parser & Orchestrator

#### Day 6-7: Pattern-Based Intent Parser

**Files**:
- `src/chemagent/core/intent_parser.py`
- `src/chemagent/core/intent_types.py`
- `tests/unit/test_intent_parser.py`

**Intent types** (enums):
```python
class IntentType(Enum):
    SIMILARITY_SEARCH = "similarity_search"
    ACTIVITY_LOOKUP = "activity_lookup"
    PROPERTY_FILTER = "property_filter"
    TARGET_EVIDENCE = "target_evidence"
    COMPOUND_INFO = "compound_info"
    STRUCTURE_SEARCH = "structure_search"
```

**Pattern definitions** (50+ patterns):
```python
CHEM_PATTERNS = {
    # Similarity
    r"similar.*to.*(?P<smiles>\[.*?\]|[A-Z][a-z]*\d+)": {
        "intent": IntentType.SIMILARITY_SEARCH,
        "entities": ["smiles", "threshold"]
    },
    r"find.*analogs.*of.*(?P<compound>\w+)": {
        "intent": IntentType.SIMILARITY_SEARCH,
        "entities": ["compound"]
    },
    
    # Activity
    r"IC50.*for.*(?P<target>\w+)": {
        "intent": IntentType.ACTIVITY_LOOKUP,
        "entities": ["target", "compound"]
    },
    r"bioactivity.*(?P<compound>CHEMBL\d+)": {
        "intent": IntentType.ACTIVITY_LOOKUP,
        "entities": ["compound"]
    },
    
    # Properties
    r"lipinski|drug.*like": {
        "intent": IntentType.PROPERTY_FILTER,
        "entities": ["constraints"]
    },
    r"molecular.*weight.*(?P<operator>[<>]).*(?P<value>\d+)": {
        "intent": IntentType.PROPERTY_FILTER,
        "entities": ["mw_constraint"]
    },
    
    # ... 45+ more patterns
}
```

**Entity extraction**:
```python
def extract_entities(query: str, intent_type: IntentType) -> Dict[str, Any]:
    """Extract SMILES, targets, constraints from query."""
    entities = {}
    
    # SMILES extraction
    smiles_pattern = r"(\[.*?\]|[A-Z][a-z]*\d+(?:\([A-Z]+\d*\))*)"
    if match := re.search(smiles_pattern, query):
        entities["smiles"] = match.group(1)
    
    # Threshold extraction
    threshold_pattern = r"(?:similarity|threshold).*?(\d+(?:\.\d+)?)"
    if match := re.search(threshold_pattern, query):
        entities["threshold"] = float(match.group(1))
    
    # ChEMBL ID extraction
    chembl_pattern = r"(CHEMBL\d+)"
    if match := re.search(chembl_pattern, query, re.IGNORECASE):
        entities["chembl_id"] = match.group(1).upper()
    
    # ... more extractors
    
    return entities
```

**Tests** (50+ test cases):
```python
@pytest.mark.parametrize("query,expected_intent,expected_entities", [
    (
        "Find compounds similar to aspirin",
        IntentType.SIMILARITY_SEARCH,
        {"compound": "aspirin"}
    ),
    (
        "What's the IC50 of CHEMBL25 for COX-2?",
        IntentType.ACTIVITY_LOOKUP,
        {"chembl_id": "CHEMBL25", "target": "COX-2"}
    ),
    (
        "Filter molecules with MW < 500 and cLogP < 5",
        IntentType.PROPERTY_FILTER,
        {"mw_max": 500, "clogp_max": 5}
    ),
    # ... 47+ more
])
def test_intent_parsing(query, expected_intent, expected_entities):
    parser = IntentParser()
    result = parser.parse(query)
    assert result.intent == expected_intent
    assert all(k in result.entities for k in expected_entities)
```

**Success criteria**:
- [x] 50+ query patterns defined
- [x] Entity extraction for SMILES, targets, ChEMBL IDs, constraints
- [x] 50+ test cases covering common queries
- [x] 95% accuracy on test cases

---

#### Day 8-9: Query Planner

**Files**:
- `src/chemagent/core/query_planner.py`
- `tests/unit/test_query_planner.py`

**Planner converts intent → execution plan**:

```python
@dataclass
class QueryPlan:
    """Execution plan."""
    steps: List[PlanStep]
    estimated_time_ms: int
    estimated_cost: float

@dataclass
class PlanStep:
    tool_name: str
    args: Dict[str, Any]
    depends_on: List[int]  # Step indices
    can_run_parallel: bool

class QueryPlanner:
    """Generates execution plans from intent."""
    
    def plan(self, intent: ParsedIntent) -> QueryPlan:
        """Generate plan based on intent type."""
        if intent.intent_type == IntentType.SIMILARITY_SEARCH:
            return self._plan_similarity_search(intent)
        elif intent.intent_type == IntentType.ACTIVITY_LOOKUP:
            return self._plan_activity_lookup(intent)
        # ... more planners
    
    def _plan_similarity_search(self, intent: ParsedIntent) -> QueryPlan:
        """
        Plan for similarity search:
        1. Resolve compound name → SMILES (if needed)
        2. Standardize SMILES
        3. ChEMBL similarity search
        4. Filter by constraints (if any)
        5. Enrich with activity data (optional)
        """
        steps = []
        
        # Step 0: Resolve name to SMILES
        if "compound" in intent.entities:
            steps.append(PlanStep(
                tool_name="resolve_compound_name",
                args={"name": intent.entities["compound"]},
                depends_on=[],
                can_run_parallel=False
            ))
        
        # Step 1: Standardize SMILES
        smiles_ref = "$0.smiles" if steps else intent.entities["smiles"]
        steps.append(PlanStep(
            tool_name="standardize_smiles",
            args={"smiles": smiles_ref},
            depends_on=[0] if steps else [],
            can_run_parallel=False
        ))
        
        # Step 2: Similarity search
        steps.append(PlanStep(
            tool_name="chembl_similarity_search",
            args={
                "smiles": f"${len(steps)-1}.smiles",
                "threshold": intent.entities.get("threshold", 0.7),
                "limit": 100
            },
            depends_on=[len(steps)-1],
            can_run_parallel=False
        ))
        
        # Step 3: Filter (if constraints)
        if intent.constraints:
            steps.append(PlanStep(
                tool_name="filter_compounds",
                args={
                    "compounds": f"${len(steps)-1}.compounds",
                    "constraints": intent.constraints
                },
                depends_on=[len(steps)-1],
                can_run_parallel=False
            ))
        
        return QueryPlan(
            steps=steps,
            estimated_time_ms=self._estimate_time(steps),
            estimated_cost=0.0  # All free APIs in Phase 1
        )
```

**Tests**:
- Each intent type → correct plan structure
- Dependency graph validation
- Cost/time estimation

**Success criteria**:
- [x] Planners for all 6 intent types
- [x] Correct dependency ordering
- [x] 30+ test cases

---

#### Day 10: Simple Orchestrator

**Files**:
- `src/chemagent/core/orchestrator.py`
- `tests/unit/test_orchestrator.py`

**Orchestrator executes plans**:

```python
class ChemOrchestrator:
    """Executes query plans."""
    
    def __init__(self):
        self.tools = self._init_tools()
        self.executor = PlanExecutor(self.tools)
    
    def query(self, user_query: str) -> QueryResult:
        """Main entry point."""
        # 1. Parse intent
        intent = self.intent_parser.parse(user_query)
        
        # 2. Generate plan
        plan = self.query_planner.plan(intent)
        
        # 3. Execute
        results = self.executor.execute(plan)
        
        # 4. Verify provenance
        verified = self.verifier.verify(results)
        
        # 5. Format response
        return self._format_response(verified)
    
    def _init_tools(self) -> Dict[str, Callable]:
        """Map tool names to functions."""
        rdkit = RDKitTools()
        chembl = ChEMBLClient()
        bindingdb = BindingDBClient()
        
        return {
            "standardize_smiles": rdkit.standardize_smiles,
            "calc_properties": rdkit.calc_molecular_properties,
            "chembl_similarity_search": chembl.similarity_search,
            "chembl_get_activities": chembl.get_activities,
            # ... all tools
        }
```

**Executor handles step dependencies**:

```python
class PlanExecutor:
    """Executes QueryPlans."""
    
    def execute(self, plan: QueryPlan) -> Dict[str, Any]:
        """Execute plan steps in order."""
        results = {}
        
        for i, step in enumerate(plan.steps):
            # Resolve dependencies
            args = self._resolve_args(step.args, results)
            
            # Call tool
            tool = self.tools[step.tool_name]
            result = tool(**args)
            
            # Store result
            results[i] = result
        
        return results
    
    def _resolve_args(self, args: Dict, results: Dict) -> Dict:
        """Replace $N.field with actual values."""
        resolved = {}
        for key, value in args.items():
            if isinstance(value, str) and value.startswith("$"):
                # Parse reference: "$0.smiles"
                step_id, field = value[1:].split(".")
                resolved[key] = results[int(step_id)][field]
            else:
                resolved[key] = value
        return resolved
```

**Success criteria**:
- [x] End-to-end query execution
- [x] Dependency resolution working
- [x] 20+ integration tests

---

### Week 3: Provenance & Testing

#### Day 11-12: Provenance System

**Files**:
- `src/chemagent/core/verifier.py`
- `src/chemagent/core/provenance.py`
- `tests/unit/test_verifier.py`

**Provenance schemas**:

```python
@dataclass
class Provenance:
    """Mandatory provenance."""
    source: str  # "chembl", "bindingdb", etc.
    source_id: str  # Database ID
    timestamp: str  # ISO 8601
    query_params: Dict[str, Any]
    confidence_score: float
    data_version: Optional[str] = None

@dataclass
class CompoundResult:
    """Compound with provenance."""
    chembl_id: str
    smiles: str
    properties: Dict[str, float]
    provenance: Provenance
    
    def __post_init__(self):
        if not self.provenance.is_complete():
            raise ValueError("Incomplete provenance")
```

**Verifier checks**:

```python
class ProvenanceVerifier:
    """Enforce evidence-grounded responses."""
    
    def verify(self, results: Any) -> VerificationResult:
        """Check provenance completeness."""
        issues = []
        
        # Check each result
        if isinstance(results, list):
            for i, result in enumerate(results):
                issues.extend(self._check_result(result, f"result[{i}]"))
        else:
            issues.extend(self._check_result(results, "result"))
        
        return VerificationResult(
            passed=len(issues) == 0,
            issues=issues,
            verified_results=results if not issues else None
        )
    
    def _check_result(self, result: Any, path: str) -> List[str]:
        """Check single result."""
        issues = []
        
        if not hasattr(result, 'provenance'):
            issues.append(f"{path}: Missing provenance")
            return issues
        
        prov = result.provenance
        
        if not prov.source:
            issues.append(f"{path}: Missing provenance.source")
        if not prov.source_id:
            issues.append(f"{path}: Missing provenance.source_id")
        if prov.confidence_score < 0.5:
            issues.append(f"{path}: Low confidence: {prov.confidence_score}")
        
        # Activity-specific checks
        if hasattr(result, 'ic50') and result.ic50:
            if not hasattr(result, 'assay_id') or not result.assay_id:
                issues.append(f"{path}: IC50 without assay_id")
        
        return issues
```

**Success criteria**:
- [x] All tools return results with provenance
- [x] Verifier rejects incomplete provenance
- [x] 40+ verification tests

---

#### Day 13-15: Testing Infrastructure

**Files**:
- `tests/conftest.py` (pytest fixtures)
- `tests/fixtures/` (test data)
- `tests/golden_queries.py`

**Fixtures**:

```python
# tests/conftest.py
import pytest
from chemagent import ChemOrchestrator

@pytest.fixture
def orchestrator():
    """Real orchestrator for integration tests."""
    return ChemOrchestrator()

@pytest.fixture
def mock_orchestrator():
    """Mocked orchestrator for unit tests."""
    orch = ChemOrchestrator()
    orch.chembl_client = MockChEMBLClient()
    return orch

@pytest.fixture
def aspirin_smiles():
    return "CC(=O)Oc1ccccc1C(=O)O"

@pytest.fixture
def sample_compounds():
    """10 test compounds with known properties."""
    return load_test_data("compounds.json")
```

**Golden queries** (30 initially, 100 by end of Phase 1):

```python
# tests/golden_queries.py
GOLDEN_QUERIES = [
    GoldenQuery(
        id=1,
        query="Find compounds similar to aspirin",
        expected_intent=IntentType.SIMILARITY_SEARCH,
        expected_tools=["standardize_smiles", "chembl_similarity_search"],
        expected_entities={"compound": "aspirin"},
        constraints={
            "min_results": 10,
            "provenance_complete": True,
            "max_latency_ms": 5000
        }
    ),
    GoldenQuery(
        id=2,
        query="What's the IC50 of CHEMBL25 for COX-2?",
        expected_intent=IntentType.ACTIVITY_LOOKUP,
        expected_tools=["chembl_get_activities"],
        expected_entities={"chembl_id": "CHEMBL25", "target": "COX-2"},
        constraints={
            "has_ic50_value": True,
            "has_assay_id": True,
            "provenance_complete": True
        }
    ),
    # ... 28 more
]
```

**Test runner**:

```python
# tests/test_golden_queries.py
@pytest.mark.parametrize("golden", GOLDEN_QUERIES)
def test_golden_query(orchestrator, golden):
    """Run each golden query."""
    result = orchestrator.query(golden.query)
    
    # Check intent parsing
    assert result.intent == golden.expected_intent
    
    # Check tools used
    assert set(result.tools_used) == set(golden.expected_tools)
    
    # Check entities extracted
    for key, value in golden.expected_entities.items():
        assert key in result.entities
        if value:  # If specific value expected
            assert result.entities[key] == value
    
    # Check constraints
    if golden.constraints.get("min_results"):
        assert len(result.results) >= golden.constraints["min_results"]
    
    if golden.constraints.get("provenance_complete"):
        verification = orchestrator.verifier.verify(result.results)
        assert verification.passed, f"Provenance issues: {verification.issues}"
    
    if golden.constraints.get("max_latency_ms"):
        assert result.latency_ms <= golden.constraints["max_latency_ms"]
```

**Phase 1 test coverage goals**:
- Unit tests: 150+ tests, 90%+ coverage
- Integration tests: 30+ tests
- Golden queries: 30 queries (100 by Phase 3)

**Success criteria**:
- [x] All tests passing
- [x] Coverage > 90% for core modules
- [x] CI/CD setup (GitHub Actions)

---

## Phase 2: Intelligence (Weeks 4-6)

**Goal**: Add RAG, LLM orchestration, advanced features

### Week 4: RAG System

#### Day 16-17: Knowledge Base Indexing

**Files**:
- `src/chemagent/rag/knowledge_base.py`
- `src/chemagent/rag/indexer.py`
- `data/knowledge/` (chemistry knowledge sources)

**Knowledge sources to index**:

1. **RDKit Cookbook** (50+ examples)
2. **ChemOps Best Practices** (SMARTS patterns, filters)
3. **Common Errors** (SMILES parsing issues, API failures)
4. **MedChem Rules** (Lipinski, Veber, PAINS filters)
5. **Tool Usage Examples** (when to use which tool)

**Indexing strategy**:

```python
class KnowledgeBase:
    """Indexed chemistry knowledge."""
    
    def __init__(self, index_dir: str = ".cache/knowledge"):
        self.vector_store = FAISSVectorStore(index_dir)
        self.bm25_index = BM25Index()
        self.embedder = BGE_M3Embedder()  # Local embeddings
    
    def index_documents(self, source_dirs: List[str]):
        """Index markdown/txt files."""
        docs = []
        for dir in source_dirs:
            for file in Path(dir).glob("**/*.md"):
                content = file.read_text()
                docs.append(Document(
                    id=str(file),
                    content=content,
                    metadata={"source": "rdkit_cookbook", "file": file.name}
                ))
        
        # Hybrid indexing
        embeddings = self.embedder.embed([d.content for d in docs])
        self.vector_store.add(embeddings, docs)
        self.bm25_index.add(docs)
    
    def search(self, query: str, k: int = 5) -> List[Document]:
        """Hybrid search: vector + BM25."""
        # Vector search
        query_emb = self.embedder.embed([query])[0]
        vector_results = self.vector_store.search(query_emb, k=k*2)
        
        # BM25 search
        bm25_results = self.bm25_index.search(query, k=k*2)
        
        # Rerank with reciprocal rank fusion
        return self._rerank(vector_results, bm25_results, k)
```

**Success criteria**:
- [x] 100+ documents indexed
- [x] Sub-100ms search latency
- [x] Relevant results for common queries

---

#### Day 18: RAG-Enhanced Tool Selection

**Files**:
- `src/chemagent/rag/tool_selector.py`

**Use RAG to improve tool selection**:

```python
class RAGToolSelector:
    """Select tools based on past queries + knowledge base."""
    
    def __init__(self, knowledge_base: KnowledgeBase):
        self.kb = knowledge_base
        self.query_history = QueryHistory()
    
    def select_tools(self, intent: ParsedIntent) -> List[str]:
        """Select tools with RAG enhancement."""
        # Get baseline tools from rule-based planner
        baseline_tools = self._get_baseline_tools(intent)
        
        # Retrieve similar past queries
        similar_queries = self.query_history.search(
            intent.original_query,
            k=5
        )
        
        # Get tool usage from similar queries
        historical_tools = set()
        for q in similar_queries:
            historical_tools.update(q.tools_used)
        
        # Retrieve relevant knowledge
        context = self.kb.search(intent.original_query, k=3)
        suggested_tools = self._extract_tool_suggestions(context)
        
        # Combine: baseline + historical + suggested
        all_tools = baseline_tools | historical_tools | suggested_tools
        
        # Rank by relevance
        ranked = self._rank_tools(all_tools, intent)
        
        return ranked[:10]  # Top 10
```

**Success criteria**:
- [x] Better tool selection than rule-based alone
- [x] Learn from query history

---

### Week 5: LLM Orchestration

#### Day 19-20: Multi-Provider LLM System

**Files**:
- `src/chemagent/llm/providers.py`
- `src/chemagent/llm/orchestrator.py`
- `src/chemagent/llm/strategies.py`

**Provider implementations** (inspired by BioPipelines):

```python
# Providers
class LocalQwenProvider(LLMProvider):
    """Local Qwen-2.5-Coder-7B via vLLM."""
    
class GeminiProvider(LLMProvider):
    """Google Gemini (free tier 1500/day)."""
    
class CerebrasProvider(LLMProvider):
    """Cerebras Llama-70B (free tier 14400/day)."""
    
class DeepSeekProvider(LLMProvider):
    """DeepSeek-V3 ($0.27/M tokens)."""
    
class OpenAIProvider(LLMProvider):
    """GPT-4o ($2.50/M tokens)."""

# Orchestrator
class LLMOrchestrator:
    """Smart routing between providers."""
    
    TASK_ROUTING = {
        "simple": ["local-qwen", "gemini-flash"],
        "standard": ["gemini-flash", "cerebras-llama"],
        "complex": ["deepseek-v3", "gpt-4o"]
    }
    
    def complete(self, prompt: str, task_complexity: str = "standard") -> str:
        """Route to appropriate provider."""
        providers = self.TASK_ROUTING[task_complexity]
        
        for provider_name in providers:
            provider = self.providers[provider_name]
            try:
                return provider.complete(prompt)
            except ProviderUnavailableError:
                continue
        
        raise Exception("All providers unavailable")
```

**Success criteria**:
- [x] 5 providers integrated
- [x] Automatic fallback working
- [x] Cost tracking

---

#### Day 21: LLM-Based Intent Parsing (Stage 2)

**Files**:
- `src/chemagent/core/llm_intent_parser.py`

**Add LLM arbiter for ambiguous queries**:

```python
class LLMIntentParser:
    """LLM-based parser for complex queries."""
    
    def parse(self, query: str) -> ParsedIntent:
        """Use LLM to parse ambiguous query."""
        prompt = f"""
        Parse this chemistry query into structured intent.
        
        Query: "{query}"
        
        Available intent types:
        - SIMILARITY_SEARCH: Find similar compounds
        - ACTIVITY_LOOKUP: Get bioactivity data
        - PROPERTY_FILTER: Filter by molecular properties
        - TARGET_EVIDENCE: Target-disease associations
        - COMPOUND_INFO: Get compound details
        - STRUCTURE_SEARCH: Substructure or SMARTS search
        
        Return JSON:
        {{
            "intent_type": "<intent>",
            "entities": {{
                "smiles": "<if applicable>",
                "chembl_id": "<if applicable>",
                "target": "<if applicable>",
                "threshold": <if applicable>
            }},
            "constraints": {{
                "mw_range": [min, max],
                "logp_max": <value>
            }}
        }}
        """
        
        response = self.llm.complete(prompt, task_complexity="simple")
        return ParsedIntent.from_json(response)
```

**Integration with 2-stage parser**:

```python
class HybridIntentParser:
    """2-stage parser: pattern → LLM fallback."""
    
    def parse(self, query: str) -> ParsedIntent:
        # Stage 1: Try pattern matching
        pattern_result = self.pattern_parser.parse(query)
        
        if pattern_result.confidence > 0.8:
            return pattern_result  # High confidence, use it
        
        # Stage 2: LLM arbiter
        llm_result = self.llm_parser.parse(query)
        
        return llm_result
```

**Success criteria**:
- [x] LLM parser handles ambiguous queries
- [x] 2-stage integration working
- [x] 95%+ accuracy on test set

---

### Week 6: Evaluation & Optimization

#### Day 22-23: Comprehensive Evaluation Suite

**Files**:
- `src/chemagent/evaluation/runner.py`
- `src/chemagent/evaluation/metrics.py`
- `data/golden_queries/` (100 queries)

**Expand golden queries to 100**:

```python
# Organize by category
GOLDEN_QUERIES = {
    "similarity_search": 20,  # 20 queries
    "activity_lookup": 20,
    "property_filter": 15,
    "target_evidence": 15,
    "compound_info": 15,
    "structure_search": 10,
    "edge_cases": 5  # Tricky queries
}
```

**Metrics to track**:

```python
@dataclass
class EvaluationMetrics:
    """Comprehensive metrics."""
    
    # Accuracy
    intent_accuracy: float  # % correct intent classification
    entity_extraction_precision: float
    entity_extraction_recall: float
    tool_selection_accuracy: float
    
    # Provenance
    provenance_completeness_rate: float  # % results with full provenance
    
    # Performance
    avg_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    
    # Cost
    avg_cost_per_query: float
    total_cost: float
    
    # Quality
    result_relevance: float  # Human eval or automated check
    error_rate: float
```

**Automated runner**:

```python
class EvaluationRunner:
    """Run evaluation suite."""
    
    def run_all(self, orchestrator: ChemOrchestrator) -> EvaluationMetrics:
        """Evaluate on all golden queries."""
        results = []
        
        for query in tqdm(GOLDEN_QUERIES_ALL):
            start = time.time()
            
            try:
                result = orchestrator.query(query.query)
                latency = (time.time() - start) * 1000
                
                # Check correctness
                intent_correct = result.intent == query.expected_intent
                entities_correct = self._check_entities(
                    result.entities,
                    query.expected_entities
                )
                provenance_complete = self._check_provenance(result)
                
                results.append(EvaluationResult(
                    query_id=query.id,
                    intent_correct=intent_correct,
                    entities_correct=entities_correct,
                    provenance_complete=provenance_complete,
                    latency_ms=latency,
                    cost=result.cost
                ))
            
            except Exception as e:
                results.append(EvaluationResult(
                    query_id=query.id,
                    error=str(e)
                ))
        
        return self._aggregate_metrics(results)
```

**Success criteria**:
- [x] 100 golden queries defined
- [x] Automated evaluation working
- [x] Metrics dashboard
- [x] Target metrics:
  - Intent accuracy > 95%
  - Provenance completeness > 98%
  - Avg latency < 2000ms
  - Avg cost < $0.01 per query

---

#### Day 24-25: Query Optimization

**Caching strategy**:

```python
class QueryCache:
    """Multi-level caching."""
    
    def __init__(self):
        self.memory_cache = LRUCache(maxsize=1000)  # In-memory
        self.disk_cache = DiskCache(".cache/queries")  # Persistent
        self.redis_cache = RedisCache()  # Distributed (optional)
    
    def get(self, query: str) -> Optional[QueryResult]:
        """Check caches in order."""
        # 1. Memory (fastest)
        if result := self.memory_cache.get(query):
            return result
        
        # 2. Disk (fast)
        if result := self.disk_cache.get(query):
            self.memory_cache.set(query, result)
            return result
        
        # 3. Redis (if available)
        if self.redis_cache and (result := self.redis_cache.get(query)):
            self.memory_cache.set(query, result)
            self.disk_cache.set(query, result)
            return result
        
        return None
```

**Parallel execution**:

```python
class ParallelExecutor:
    """Execute independent steps in parallel."""
    
    def execute(self, plan: QueryPlan) -> Dict[str, Any]:
        """Execute with parallelization."""
        results = {}
        
        # Group steps by dependency level
        levels = self._group_by_level(plan.steps)
        
        for level_steps in levels:
            # Execute all steps in this level in parallel
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = {}
                for step in level_steps:
                    args = self._resolve_args(step.args, results)
                    future = executor.submit(self._execute_step, step, args)
                    futures[future] = step
                
                for future in as_completed(futures):
                    step = futures[future]
                    results[step.id] = future.result()
        
        return results
```

**Success criteria**:
- [x] Caching reduces latency 80%+ for repeated queries
- [x] Parallel execution speeds up independent steps

---

## Phase 3: Production (Weeks 7-9)

**Goal**: Deployment, UI, MCP server, production features

### Week 7: Project Workspaces

#### Day 26-27: Persistent Workspaces

**Files**:
- `src/chemagent/workspace/project.py`
- `src/chemagent/workspace/history.py`
- `src/chemagent/workspace/export.py`

**Project workspace**:

```python
class ChemProject:
    """Persistent investigation workspace."""
    
    def __init__(self, project_id: str, name: str):
        self.project_id = project_id
        self.name = name
        self.created_at = datetime.now()
        
        # State
        self.compounds: List[Compound] = []
        self.queries: List[QueryResult] = []
        self.filters_applied: List[Filter] = []
        self.notes: List[Note] = []
    
    def add_query(self, query: str) -> QueryResult:
        """Execute and store query."""
        result = orchestrator.query(query)
        self.queries.append(result)
        self._save()
        return result
    
    def add_compounds(self, compounds: List[Compound]):
        """Add compounds to working set."""
        self.compounds.extend(compounds)
        self._save()
    
    def apply_filter(self, filter_name: str, **params):
        """Apply filter and update compound list."""
        filter_func = FILTERS[filter_name]
        self.compounds = filter_func(self.compounds, **params)
        self.filters_applied.append(Filter(filter_name, params))
        self._save()
    
    def export_notebook(self, output_path: str):
        """Generate Jupyter notebook."""
        nb = nbformat.v4.new_notebook()
        
        # Add cells for each query
        for query_result in self.queries:
            nb.cells.append(nbformat.v4.new_markdown_cell(
                f"## Query: {query_result.query}"
            ))
            nb.cells.append(nbformat.v4.new_code_cell(
                self._generate_code(query_result)
            ))
        
        # Write notebook
        with open(output_path, 'w') as f:
            nbformat.write(nb, f)
    
    def _generate_code(self, result: QueryResult) -> str:
        """Generate reproducible Python code."""
        return f"""
# Query: {result.query}
result = orchestrator.query("{result.query}")

# Results: {len(result.results)} compounds
for compound in result.results:
    print(f"{{compound.chembl_id}}: {{compound.smiles}}")
"""
```

**Success criteria**:
- [x] Projects persist across sessions
- [x] Notebook export working
- [x] Query history reproducible

---

### Week 8: Web UI & MCP Server

#### Day 28-30: Gradio Web Interface

**Files**:
- `src/chemagent/web/app.py`
- `src/chemagent/web/components.py`

**Gradio interface**:

```python
import gradio as gr

def create_app():
    """Create Gradio web UI."""
    
    with gr.Blocks(title="ChemAgent") as app:
        gr.Markdown("# 🧪 ChemAgent - Pharmaceutical Research Assistant")
        
        with gr.Tab("Query"):
            query_input = gr.Textbox(
                label="Ask a chemistry question",
                placeholder="Find compounds similar to aspirin with IC50 < 100nM",
                lines=3
            )
            submit_btn = gr.Button("Search", variant="primary")
            
            with gr.Row():
                intent_output = gr.Textbox(label="Intent", interactive=False)
                entities_output = gr.JSON(label="Entities")
            
            results_table = gr.Dataframe(
                headers=["ChEMBL ID", "SMILES", "Similarity", "IC50", "Source"],
                label="Results"
            )
            
            provenance_output = gr.JSON(label="Provenance")
        
        with gr.Tab("Filters"):
            filter_selector = gr.Dropdown(
                ["Lipinski", "Veber", "PAINS", "Custom"],
                label="Filter"
            )
            # Filter parameters...
        
        with gr.Tab("Projects"):
            project_list = gr.Dropdown(label="Select Project")
            # Project management...
        
        # Event handlers
        submit_btn.click(
            fn=process_query,
            inputs=[query_input],
            outputs=[intent_output, entities_output, results_table, provenance_output]
        )
    
    return app

def process_query(query: str):
    """Process query and return results."""
    result = orchestrator.query(query)
    
    # Format for Gradio
    intent = str(result.intent)
    entities = result.entities
    
    # Results table
    table_data = [
        [c.chembl_id, c.smiles, f"{c.similarity:.2f}", c.ic50, c.provenance.source]
        for c in result.results
    ]
    
    provenance = [c.provenance.__dict__ for c in result.results]
    
    return intent, entities, table_data, provenance

if __name__ == "__main__":
    app = create_app()
    app.launch(server_name="0.0.0.0", server_port=7860)
```

**Success criteria**:
- [x] Web UI functional
- [x] Real-time query execution
- [x] Results visualization

---

#### Day 31-32: MCP Server

**Files**:
- `src/chemagent/mcp/server.py`
- `src/chemagent/mcp/tools.py`

**MCP server for Claude Code integration**:

```python
class ChemAgentMCPServer:
    """MCP server exposing ChemAgent tools."""
    
    def __init__(self):
        self.orchestrator = ChemOrchestrator()
        self.tools = self._register_tools()
    
    def _register_tools(self) -> List[ToolDefinition]:
        return [
            ToolDefinition(
                name="search_chembl_similarity",
                description="Search ChEMBL for similar compounds",
                parameters={
                    "type": "object",
                    "properties": {
                        "smiles": {"type": "string"},
                        "threshold": {"type": "number", "default": 0.7}
                    },
                    "required": ["smiles"]
                },
                handler=self.handle_similarity_search,
                annotations=ToolAnnotations(
                    read_only=True,
                    category="chemistry"
                )
            ),
            # ... 10+ more tools
        ]
    
    async def handle_similarity_search(self, smiles: str, threshold: float = 0.7):
        """Handle similarity search request."""
        result = self.orchestrator.query(
            f"Find compounds similar to {smiles} with threshold {threshold}"
        )
        
        return {
            "compounds": [
                {
                    "chembl_id": c.chembl_id,
                    "smiles": c.smiles,
                    "similarity": c.similarity,
                    "provenance": c.provenance.__dict__
                }
                for c in result.results
            ]
        }

# Run server
if __name__ == "__main__":
    server = ChemAgentMCPServer()
    server.run(transport="stdio")  # For Claude Code
```

**Success criteria**:
- [x] MCP server running
- [x] 10+ tools exposed
- [x] Integration with Claude Code working

---

### Week 9: Deployment & Documentation

#### Day 33-34: Docker & Deployment

**Files**:
- `Dockerfile`
- `docker-compose.yml`
- `deployment/` (K8s manifests, etc.)

**Dockerfile**:

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install RDKit (requires conda)
RUN apt-get update && apt-get install -y \
    wget \
    && rm -rf /var/lib/apt/lists/*

RUN wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh \
    && bash Miniconda3-latest-Linux-x86_64.sh -b -p /opt/conda \
    && rm Miniconda3-latest-Linux-x86_64.sh

ENV PATH="/opt/conda/bin:$PATH"

# Install dependencies
COPY requirements.txt .
RUN conda install -c conda-forge rdkit -y \
    && pip install -r requirements.txt

# Copy code
COPY src/ ./src/
COPY data/ ./data/

# Run
EXPOSE 8000
CMD ["python", "-m", "chemagent.web"]
```

**Docker Compose**:

```yaml
version: '3.8'

services:
  chemagent:
    build: .
    ports:
      - "8000:8000"
      - "7860:7860"
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - REDIS_URL=redis://cache:6379
    depends_on:
      - cache
      - embeddings
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
  
  embeddings:
    image: ghcr.io/huggingface/text-embeddings-inference:latest
    ports:
      - "8001:80"
    command: --model-id BAAI/bge-m3
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
  
  cache:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

**Success criteria**:
- [x] Docker image builds
- [x] docker-compose up works
- [x] Health checks passing

---

#### Day 35: Documentation & Polish

**Documentation to write**:
- [x] README.md (already done)
- [x] ARCHITECTURE.md (already done)
- [x] IMPLEMENTATION_PLAN.md (this document)
- [ ] API.md (API reference)
- [ ] CONTRIBUTING.md
- [ ] TUTORIAL.md (getting started guide)

**Final polish**:
- Code formatting (black, isort)
- Type hints (mypy)
- Docstring coverage
- Examples directory

**Success criteria**:
- [x] All documentation complete
- [x] Code quality checks passing
- [x] Ready for GitHub release

---

## File Structure

Complete project structure:

```
ChemAgent/
├── README.md
├── LICENSE
├── pyproject.toml
├── requirements.txt
├── environment.yml
├── Dockerfile
├── docker-compose.yml
├── .gitignore
├── .github/
│   └── workflows/
│       ├── tests.yml
│       └── docker.yml
│
├── docs/
│   ├── ARCHITECTURE.md
│   ├── IMPLEMENTATION_PLAN.md
│   ├── COMPARISON.md
│   ├── API.md
│   ├── CONTRIBUTING.md
│   └── TUTORIAL.md
│
├── src/
│   └── chemagent/
│       ├── __init__.py
│       ├── __version__.py
│       │
│       ├── core/
│       │   ├── __init__.py
│       │   ├── intent_parser.py          # Pattern-based + LLM
│       │   ├── intent_types.py           # Enum definitions
│       │   ├── query_planner.py          # Intent → execution plan
│       │   ├── orchestrator.py           # Main orchestrator
│       │   ├── verifier.py               # Provenance checking
│       │   └── provenance.py             # Provenance schemas
│       │
│       ├── tools/
│       │   ├── __init__.py
│       │   ├── rdkit_tools.py            # Chemistry functions
│       │   ├── chembl_client.py          # ChEMBL API
│       │   ├── bindingdb_client.py       # BindingDB API
│       │   ├── opentargets_client.py     # Open Targets
│       │   ├── uniprot_client.py         # UniProt API
│       │   ├── pubchem_client.py         # PubChem API
│       │   ├── pdb_client.py             # PDB API
│       │   └── filters.py                # Property filters
│       │
│       ├── llm/
│       │   ├── __init__.py
│       │   ├── base.py                   # Base classes
│       │   ├── providers.py              # Provider implementations
│       │   ├── orchestrator.py           # Smart routing
│       │   ├── strategies.py             # Routing strategies
│       │   └── embeddings.py             # BGE-M3 wrapper
│       │
│       ├── rag/
│       │   ├── __init__.py
│       │   ├── knowledge_base.py         # Main KB class
│       │   ├── indexer.py                # Document indexing
│       │   ├── retriever.py              # Hybrid search
│       │   └── tool_selector.py          # RAG-enhanced tool selection
│       │
│       ├── workspace/
│       │   ├── __init__.py
│       │   ├── project.py                # Project class
│       │   ├── history.py                # Query history
│       │   └── export.py                 # Notebook export
│       │
│       ├── evaluation/
│       │   ├── __init__.py
│       │   ├── runner.py                 # Evaluation runner
│       │   ├── metrics.py                # Metrics calculation
│       │   └── golden_queries.py         # Golden query definitions
│       │
│       ├── web/
│       │   ├── __init__.py
│       │   ├── app.py                    # Gradio app
│       │   └── components.py             # UI components
│       │
│       ├── mcp/
│       │   ├── __init__.py
│       │   ├── server.py                 # MCP server
│       │   └── tools.py                  # MCP tool definitions
│       │
│       └── cli.py                        # Command-line interface
│
├── data/
│   ├── knowledge/                        # Knowledge base sources
│   │   ├── rdkit_cookbook/
│   │   ├── medchem_rules/
│   │   └── tool_examples/
│   ├── golden_queries/                   # Test queries
│   │   └── queries_v1.json
│   └── cache/                            # Query cache
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py                       # Pytest fixtures
│   ├── fixtures/                         # Test data
│   │   ├── compounds.json
│   │   └── chembl_responses.json
│   │
│   ├── unit/
│   │   ├── test_rdkit_tools.py
│   │   ├── test_chembl_client.py
│   │   ├── test_intent_parser.py
│   │   ├── test_query_planner.py
│   │   ├── test_orchestrator.py
│   │   └── test_verifier.py
│   │
│   ├── integration/
│   │   ├── test_chembl_integration.py
│   │   ├── test_end_to_end.py
│   │   └── test_workspace.py
│   │
│   └── evaluation/
│       ├── test_golden_queries.py
│       └── test_metrics.py
│
├── examples/
│   ├── basic_usage.py
│   ├── similarity_search.py
│   ├── druglike_filtering.py
│   └── project_workspace.py
│
├── scripts/
│   ├── index_knowledge_base.py
│   ├── run_evaluation.py
│   └── deploy.sh
│
└── logs/                                 # Log files
    ├── query.log
    ├── audit.jsonl
    └── metrics.jsonl
```

---

## Success Metrics

### Phase 1 Success Criteria

- [x] **ChemOps Toolbelt**: 10+ RDKit functions, 100+ tests, 90%+ coverage
- [x] **Database Clients**: ChEMBL + BindingDB + UniProt working
- [x] **Intent Parser**: 50+ patterns, 95%+ accuracy on test cases
- [x] **Orchestrator**: End-to-end query execution working
- [x] **Provenance**: All results have complete provenance
- [x] **Testing**: 150+ unit tests, 30+ integration tests, 30 golden queries

### Phase 2 Success Criteria

- [x] **RAG System**: 100+ documents indexed, sub-100ms retrieval
- [x] **LLM Orchestration**: 5 providers, automatic fallback, cost tracking
- [x] **Evaluation**: 100 golden queries, automated metrics
- [x] **Target Metrics**:
  - Intent accuracy > 95%
  - Provenance completeness > 98%
  - Avg latency < 2000ms
  - Avg cost < $0.01/query

### Phase 3 Success Criteria

- [x] **Workspaces**: Projects persist, notebook export working
- [x] **Web UI**: Gradio interface functional
- [x] **MCP Server**: 10+ tools exposed, Claude Code integration
- [x] **Deployment**: Docker + docker-compose working
- [x] **Documentation**: Complete API docs, tutorials, examples

---

## Next Steps After Phase 3

### Enhancements (Priority Order)

1. **Multi-modal support** - Structure visualization, 3D conformers
2. **Synthesis planning** - RetroPath, AiZynthFinder integration
3. **ADMET prediction** - Property prediction models
4. **Patent analysis** - SureChEMBL, freedom-to-operate checks
5. **Hypothesis generation** - SAR analysis, suggested analogs
6. **Internal data integration** - Connect to company databases

### Scaling

1. **Distributed caching** - Redis cluster
2. **Async query execution** - Celery workers
3. **Load balancing** - Multiple API instances
4. **Monitoring** - Prometheus + Grafana dashboards

---

**Last Updated**: January 2026  
**Status**: Phase 1 ready to begin
