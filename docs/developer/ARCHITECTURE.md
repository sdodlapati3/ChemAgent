# ChemAgent Architecture

**Version**: 1.0.0  
**Date**: January 2026  
**Status**: Planning/Development

---

## Table of Contents

1. [Overview](#overview)
2. [Design Philosophy](#design-philosophy)
3. [System Architecture](#system-architecture)
4. [Core Components](#core-components)
5. [Data Flow](#data-flow)
6. [LLM Orchestration](#llm-orchestration)
7. [Provenance System](#provenance-system)
8. [Security & Governance](#security--governance)
9. [Deployment Architecture](#deployment-architecture)

---

## Overview

ChemAgent is an **evidence-grounded pharmaceutical research assistant** that combines:
- Deterministic chemistry tools (RDKit)
- Public pharmaceutical databases (ChEMBL, BindingDB, Open Targets, etc.)
- Smart LLM orchestration (local + cloud)
- Provenance-first design (every claim traceable to source)

### Design Goals

| Goal | Implementation |
|------|----------------|
| **Deployability** | Production-ready from day 1, not a research demo |
| **Evidence-grounded** | Every claim must have source (ChEMBL ID, paper, etc.) |
| **Cost-efficient** | Smart routing: local models for simple tasks, cloud for complex |
| **Reproducible** | Query history + data versioning = reproducible runs |
| **Secure** | Audit logs, role-based permissions, sandboxed execution |

---

## Design Philosophy

### 1. Tools First, Agents Second

**Principle**: Build deterministic chemistry functions before adding LLM reasoning.

```python
# ✅ GOOD: Deterministic tool with clear interface
def calc_lipinski_violations(smiles: str) -> LipinskiResult:
    """
    Calculate Lipinski Rule of 5 violations.
    
    Returns:
        LipinskiResult with violations count and details
    
    Raises:
        ValueError: If SMILES is invalid
    """
    mol = standardize_smiles(smiles)  # Deterministic
    mw = Descriptors.MolWt(mol)
    logp = Descriptors.MolLogP(mol)
    # ... pure calculation, no LLM
    
    return LipinskiResult(
        violations=count,
        mw=mw,
        logp=logp,
        source="rdkit",
        version="2023.09.1"
    )

# ❌ BAD: LLM for deterministic task
def calc_lipinski_violations_llm(smiles: str):
    prompt = f"Calculate Lipinski violations for {smiles}"
    return llm.complete(prompt)  # Non-deterministic, expensive, slow
```

### 2. Provenance First

**Principle**: Never return a claim without source evidence.

```python
@dataclass
class CompoundResult:
    """Result with mandatory provenance."""
    
    chembl_id: str
    smiles: str
    ic50: float
    units: str
    target: str
    
    # MANDATORY provenance fields
    source: str  # "chembl", "bindingdb", etc.
    source_id: str  # "CHEMBL123456"
    assay_id: Optional[str]
    reference_doi: Optional[str]
    confidence_score: float
    
    def __post_init__(self):
        """Enforce provenance requirement."""
        if not self.source or not self.source_id:
            raise ValueError("Provenance required: source + source_id")
```

### 3. Single Orchestrator Default

**Principle**: Multi-agent is a feature flag, not the foundation.

**Why**: BioPipelines learned this the hard way:
- Multi-agent adds coordination overhead
- Harder to debug (which agent failed?)
- More latency (inter-agent communication)
- Diminishing returns for most queries

**When to use multi-agent**:
- Truly independent subtasks (parallel execution)
- Different expertise domains (chem tools vs literature search)
- Long-running workflows (can checkpoint)

```python
# Default: Single orchestrator
class ChemOrchestrator:
    """Single agent that plans and executes."""
    
    def query(self, user_query: str) -> Result:
        # 1. Parse intent
        intent = self.intent_parser.parse(user_query)
        
        # 2. Plan tool calls
        plan = self.query_planner.plan(intent)
        
        # 3. Execute tools
        results = self.executor.execute(plan)
        
        # 4. Verify provenance
        verified = self.verifier.check(results)
        
        # 5. Format response
        return self.formatter.format(verified)

# Feature flag: Multi-agent mode
if config.use_multi_agent:
    orchestrator = MultiAgentOrchestrator()  # Optional
```

### 4. Evaluation Driven

**Principle**: 100+ golden queries with automated testing.

Inspired by BioPipelines' [evaluation infrastructure](https://github.com/sdodlapa/BioPipelines/blob/main/scripts/advanced_evaluation_runner.py):

```python
GOLDEN_QUERIES = [
    GoldenQuery(
        query="Find ChEMBL compounds similar to aspirin",
        expected_tool="chembl_similarity_search",
        expected_entities={"smiles": "CC(=O)Oc1ccccc1C(=O)O"},
        constraints={
            "min_results": 10,
            "tanimoto_threshold": 0.7,
            "has_provenance": True,
            "max_latency_ms": 2000,
        }
    ),
    # 100+ more...
]
```

### 5. Production Ready

**Principle**: Audit logs, security boundaries, reproducible runs.

- Every tool call logged with user, query, result, timestamp
- Role-based permissions (read-only vs write/export)
- Sandboxed code execution (if enabled)
- Query history versioning

---

## System Architecture

### High-Level Diagram

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         ChemAgent System                                  │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                    Interface Layer                               │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │    │
│  │  │   Web UI     │  │  MCP Server  │  │    Python API        │  │    │
│  │  │  (Gradio)    │  │ (Claude Code)│  │  (import chemagent)  │  │    │
│  │  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘  │    │
│  └─────────┼──────────────────┼─────────────────────┼──────────────┘    │
│            └──────────────────┼─────────────────────┘                    │
│                               ▼                                          │
│  ╔══════════════════════════════════════════════════════════════════╗   │
│  ║               ChemAgent Facade (single entry point)              ║   │
│  ║                                                                   ║   │
│  ║  .query(str) → Result                                            ║   │
│  ║  .search_compounds(smiles, threshold) → List[Compound]           ║   │
│  ║  .filter_druglike(compounds, constraints) → List[Compound]       ║   │
│  ║  .get_target_evidence(target, disease) → EvidenceReport          ║   │
│  ║  .create_project(name) → Project                                 ║   │
│  ╚══════════════════════════════════════════════════════════════════╝   │
│                               │                                          │
│  ┌────────────────────────────────────────────────────────────────┐     │
│  │              Intent Understanding Layer                         │     │
│  │                                                                 │     │
│  │  ┌──────────────────────────────────────────────────────────┐ │     │
│  │  │         Stage 1: Fast Path (80% of queries)              │ │     │
│  │  │                                                           │ │     │
│  │  │  ┌─────────────────┐  ┌──────────────────────────────┐  │ │     │
│  │  │  │ Pattern Matching│  │   Entity Extraction          │  │ │     │
│  │  │  │  (regex + dict) │  │  (SMILES, targets, units)    │  │ │     │
│  │  │  └─────────────────┘  └──────────────────────────────┘  │ │     │
│  │  │                                                           │ │     │
│  │  │  Examples:                                                │ │     │
│  │  │  "similarity to [SMILES]" → SIMILARITY_SEARCH            │ │     │
│  │  │  "IC50 for target X" → ACTIVITY_LOOKUP                   │ │     │
│  │  │  "Lipinski filter" → PROPERTY_FILTER                     │ │     │
│  │  └──────────────────────────────────────────────────────────┘ │     │
│  │                            │                                   │     │
│  │              Agreement check (confidence > 0.8)?              │     │
│  │                            │                                   │     │
│  │                      NO (ambiguous)                            │     │
│  │                            ▼                                   │     │
│  │  ┌──────────────────────────────────────────────────────────┐ │     │
│  │  │   Stage 2: LLM Arbiter (20% - complex/ambiguous)        │ │     │
│  │  │                                                           │ │     │
│  │  │  Uses: Local model (Qwen-2.5-7B) or Gemini              │ │     │
│  │  │  Prompt: "Parse chemistry query with entity extraction"  │ │     │
│  │  │  Output: Structured ParsedIntent with entities           │ │     │
│  │  └──────────────────────────────────────────────────────────┘ │     │
│  └─────────────────────────────────────────────────────────────────┘   │
│                               │                                          │
│  ┌────────────────────────────────────────────────────────────────┐     │
│  │              Query Planning & Tool Selection                   │     │
│  │                                                                 │     │
│  │  ┌──────────────────┐  ┌──────────────────────────────────┐   │     │
│  │  │  Query Planner   │  │      RAG-Enhanced Selector       │   │     │
│  │  │                  │  │                                   │   │     │
│  │  │  Intent → Steps  │  │  Retrieves relevant context:     │   │     │
│  │  │                  │  │  - Similar past queries          │   │     │
│  │  │  Example:        │  │  - Tool usage patterns           │   │     │
│  │  │  1. Validate     │  │  - ChemOps cookbook              │   │     │
│  │  │  2. Search DB    │  │  - Error recovery solutions      │   │     │
│  │  │  3. Filter       │  │                                   │   │     │
│  │  │  4. Aggregate    │  │                                   │   │     │
│  │  └──────────────────┘  └──────────────────────────────────┘   │     │
│  └─────────────────────────────────────────────────────────────────┘   │
│                               │                                          │
│  ┌────────────────────────────────────────────────────────────────┐     │
│  │                   Tool Execution Layer                          │     │
│  │                                                                 │     │
│  │  ┌───────────────────────────────────────────────────────────┐ │     │
│  │  │              ChemOps Toolbelt (Deterministic)             │ │     │
│  │  │                                                            │ │     │
│  │  │  RDKit Tools:                 Database Clients:           │ │     │
│  │  │  ┌──────────────────┐         ┌──────────────────────┐   │ │     │
│  │  │  │ standardize()    │         │ ChEMBLClient         │   │ │     │
│  │  │  │ calc_props()     │         │ BindingDBClient      │   │ │     │
│  │  │  │ similarity()     │         │ OpenTargetsClient    │   │ │     │
│  │  │  │ substructure()   │         │ UniProtClient        │   │ │     │
│  │  │  │ scaffold()       │         │ PubChemClient        │   │ │     │
│  │  │  │ filter_druglike()│         │ PDBClient            │   │ │     │
│  │  │  └──────────────────┘         └──────────────────────┘   │ │     │
│  │  │                                                            │ │     │
│  │  │  All tools return:                                        │ │     │
│  │  │  {                                                         │ │     │
│  │  │    "result": <data>,                                      │ │     │
│  │  │    "provenance": {"source": "chembl", "id": "..."},      │ │     │
│  │  │    "metadata": {"timestamp": "...", "version": "..."}    │ │     │
│  │  │  }                                                         │ │     │
│  │  └───────────────────────────────────────────────────────────┘ │     │
│  └─────────────────────────────────────────────────────────────────┘   │
│                               │                                          │
│  ┌────────────────────────────────────────────────────────────────┐     │
│  │                 Verification & Validation Layer                 │     │
│  │                                                                 │     │
│  │  ┌──────────────────────────────────────────────────────────┐  │     │
│  │  │              Provenance Verifier                          │  │     │
│  │  │                                                            │  │     │
│  │  │  Checks:                                                  │  │     │
│  │  │  ✓ Every compound has ChEMBL/BindingDB ID               │  │     │
│  │  │  ✓ Every IC50 value has assay_id + paper reference      │  │     │
│  │  │  ✓ Target-disease claims have Open Targets evidence     │  │     │
│  │  │  ✓ Numeric values within reasonable ranges              │  │     │
│  │  │  ✗ REJECT if provenance missing                          │  │     │
│  │  └──────────────────────────────────────────────────────────┘  │     │
│  │                                                                 │     │
│  │  ┌──────────────────────────────────────────────────────────┐  │     │
│  │  │              Quality Checker                              │  │     │
│  │  │                                                            │  │     │
│  │  │  • SMILES validation (RDKit parse check)                 │  │     │
│  │  │  • Unit consistency (nM vs μM vs Ki vs IC50)            │  │     │
│  │  │  • Confidence scoring (how reliable is this claim?)      │  │     │
│  │  └──────────────────────────────────────────────────────────┘  │     │
│  └─────────────────────────────────────────────────────────────────┘   │
│                               │                                          │
│  ┌────────────────────────────────────────────────────────────────┐     │
│  │                    LLM Provider Cascade                         │     │
│  │                                                                 │     │
│  │  Task-aware routing:                                           │     │
│  │                                                                 │     │
│  │  Simple tasks (SMILES validation, pattern matching):           │     │
│  │  └─► Local: Qwen-2.5-Coder-7B (< 50ms, $0)                    │     │
│  │                                                                 │     │
│  │  Standard queries (entity extraction, tool selection):          │     │
│  │  └─► Gemini-1.5-Flash (200ms, FREE 1500/day)                  │     │
│  │      └─► Cerebras-Llama-3.3-70B (150ms, FREE 14400/day)       │     │
│  │                                                                 │     │
│  │  Complex reasoning (synthesis planning, hypothesis gen):        │     │
│  │  └─► DeepSeek-V3 (800ms, $0.27/M tokens)                      │     │
│  │      └─► GPT-4o (1000ms, $2.50/M tokens)                       │     │
│  │                                                                 │     │
│  │  Embedding tasks (similarity, clustering):                     │     │
│  │  └─► Local: BGE-M3 (embeddings server, $0)                    │     │
│  └─────────────────────────────────────────────────────────────────┘   │
│                               │                                          │
│  ┌────────────────────────────────────────────────────────────────┐     │
│  │                   Observability & Audit Layer                   │     │
│  │                                                                 │     │
│  │  ┌────────────────┐  ┌────────────────┐  ┌─────────────────┐  │     │
│  │  │  Audit Logger  │  │    Metrics     │  │  Health Monitor │  │     │
│  │  │                │  │                │  │                  │  │     │
│  │  │  Logs:         │  │  Tracks:       │  │  Monitors:       │  │     │
│  │  │  • User        │  │  • Accuracy    │  │  • DB uptime     │  │     │
│  │  │  • Query       │  │  • Latency     │  │  • LLM latency   │  │     │
│  │  │  • Tools used  │  │  • Cost        │  │  • Error rates   │  │     │
│  │  │  • Result      │  │  • Provenance  │  │                  │  │     │
│  │  │  • Timestamp   │  │    rate        │  │                  │  │     │
│  │  └────────────────┘  └────────────────┘  └─────────────────┘  │     │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                           │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. Intent Parser

**File**: `chemagent/core/intent_parser.py`

Converts natural language to structured `ParsedIntent`:

```python
@dataclass
class ParsedIntent:
    """Structured representation of user intent."""
    
    intent_type: IntentType  # SIMILARITY_SEARCH, ACTIVITY_LOOKUP, etc.
    entities: Dict[str, Any]  # {smiles, target, threshold, etc.}
    constraints: Dict[str, Any]  # {mw_range, logp_max, etc.}
    confidence: float  # 0.0 to 1.0
    parsing_method: str  # "pattern" or "llm"
```

**Two-stage design**:

Stage 1 (fast, <15ms): Pattern matching
```python
CHEM_PATTERNS = {
    r"similar.*to.*(?P<smiles>\[.*?\]|CC\(.*?\))": {
        "intent": IntentType.SIMILARITY_SEARCH,
        "entities": ["smiles"]
    },
    r"IC50.*for.*(?P<target>\w+)": {
        "intent": IntentType.ACTIVITY_LOOKUP,
        "entities": ["target", "assay_type"]
    },
}
```

Stage 2 (complex): LLM arbiter
```python
def parse_with_llm(query: str) -> ParsedIntent:
    """Use LLM for ambiguous queries."""
    prompt = f"""
    Parse this chemistry query into structured intent:
    Query: "{query}"
    
    Return JSON:
    {{
        "intent_type": "SIMILARITY_SEARCH" | "ACTIVITY_LOOKUP" | ...,
        "entities": {{"smiles": "...", "target": "..."}},
        "constraints": {{"threshold": 0.7, ...}}
    }}
    """
    response = llm.complete(prompt)
    return ParsedIntent.from_json(response)
```

### 2. Query Planner

**File**: `chemagent/core/query_planner.py`

Converts `ParsedIntent` → execution plan:

```python
@dataclass
class QueryPlan:
    """Execution plan for a query."""
    
    steps: List[PlanStep]
    estimated_time_ms: int
    estimated_cost: float
    
@dataclass
class PlanStep:
    """Single step in execution plan."""
    
    tool_name: str
    args: Dict[str, Any]
    depends_on: List[int]  # Step indices this depends on
    can_run_parallel: bool

# Example plan for "Find similar compounds to aspirin with IC50 < 100nM"
plan = QueryPlan(
    steps=[
        PlanStep(
            tool_name="standardize_smiles",
            args={"smiles": "CC(=O)Oc1ccccc1C(=O)O"},
            depends_on=[],
            can_run_parallel=False
        ),
        PlanStep(
            tool_name="chembl_similarity_search",
            args={"smiles": "$0.result", "threshold": 0.7},
            depends_on=[0],
            can_run_parallel=False
        ),
        PlanStep(
            tool_name="filter_by_activity",
            args={"compounds": "$1.result", "ic50_max": 100, "units": "nM"},
            depends_on=[1],
            can_run_parallel=False
        ),
    ]
)
```

### 3. ChemOps Toolbelt

**File**: `chemagent/tools/rdkit_tools.py`

Pure functions, heavily tested:

```python
class RDKitTools:
    """Chemistry operations using RDKit."""
    
    @staticmethod
    def standardize_smiles(smiles: str) -> StandardizedResult:
        """
        Standardize SMILES (salt stripping, tautomer handling).
        
        Args:
            smiles: Input SMILES string
            
        Returns:
            StandardizedResult with canonical SMILES + provenance
            
        Raises:
            ValueError: If SMILES is invalid
        """
        try:
            mol = Chem.MolFromSmiles(smiles)
            if mol is None:
                raise ValueError(f"Invalid SMILES: {smiles}")
            
            # Salt stripping
            remover = SaltRemover()
            mol = remover.StripMol(mol)
            
            # Canonicalization
            canonical_smiles = Chem.MolToSmiles(mol)
            
            return StandardizedResult(
                smiles=canonical_smiles,
                inchi=Chem.MolToInchi(mol),
                inchi_key=Chem.MolToInchiKey(mol),
                provenance={
                    "source": "rdkit",
                    "version": rdkit.__version__,
                    "method": "standardize_smiles"
                }
            )
        except Exception as e:
            raise ValueError(f"Failed to standardize SMILES: {e}")
    
    @staticmethod
    def calc_lipinski(mol: Mol) -> LipinskiResult:
        """Calculate Lipinski Rule of 5 properties."""
        mw = Descriptors.MolWt(mol)
        logp = Descriptors.MolLogP(mol)
        hbd = Descriptors.NumHDonors(mol)
        hba = Descriptors.NumHAcceptors(mol)
        
        violations = sum([
            mw > 500,
            logp > 5,
            hbd > 5,
            hba > 10
        ])
        
        return LipinskiResult(
            mw=mw, logp=logp, hbd=hbd, hba=hba,
            violations=violations,
            passes=violations == 0
        )
```

### 4. Database Clients

**File**: `chemagent/tools/chembl_client.py`

Wrapper around ChEMBL API with caching and error handling:

```python
class ChEMBLClient:
    """ChEMBL database client."""
    
    def __init__(self, cache_dir: str = ".cache/chembl"):
        self.client = new_client.new_client
        self.cache = DiskCache(cache_dir)
    
    def similarity_search(
        self,
        smiles: str,
        threshold: float = 0.7,
        limit: int = 100
    ) -> List[CompoundResult]:
        """
        Search ChEMBL for similar compounds.
        
        Args:
            smiles: Query SMILES
            threshold: Tanimoto similarity threshold (0.0 to 1.0)
            limit: Maximum results
            
        Returns:
            List of compounds with similarity scores + provenance
        """
        cache_key = f"similarity_{smiles}_{threshold}_{limit}"
        
        # Check cache first
        if cached := self.cache.get(cache_key):
            return cached
        
        # Query ChEMBL
        results = self.client.similarity.filter(
            smiles=smiles,
            similarity=threshold
        ).only([
            'molecule_chembl_id',
            'molecule_structures',
            'molecule_properties'
        ])[:limit]
        
        # Convert to our format with provenance
        compounds = []
        for r in results:
            compounds.append(CompoundResult(
                chembl_id=r['molecule_chembl_id'],
                smiles=r['molecule_structures']['canonical_smiles'],
                similarity=r['similarity'],
                provenance={
                    "source": "chembl",
                    "source_id": r['molecule_chembl_id'],
                    "query_smiles": smiles,
                    "threshold": threshold,
                    "timestamp": datetime.now().isoformat()
                }
            ))
        
        # Cache results
        self.cache.set(cache_key, compounds, ttl=86400)  # 24h
        
        return compounds
    
    def get_activities(
        self,
        chembl_id: str,
        target_type: Optional[str] = None
    ) -> List[ActivityResult]:
        """Get bioactivity data for a compound."""
        activities = self.client.activity.filter(
            molecule_chembl_id=chembl_id
        )
        
        if target_type:
            activities = activities.filter(target_type=target_type)
        
        results = []
        for act in activities:
            results.append(ActivityResult(
                chembl_id=chembl_id,
                target_chembl_id=act['target_chembl_id'],
                target_name=act['target_pref_name'],
                assay_chembl_id=act['assay_chembl_id'],
                assay_type=act['assay_type'],
                standard_type=act['standard_type'],  # IC50, Ki, etc.
                standard_value=act['standard_value'],
                standard_units=act['standard_units'],
                pchembl_value=act.get('pchembl_value'),
                provenance={
                    "source": "chembl",
                    "assay_id": act['assay_chembl_id'],
                    "document_id": act.get('document_chembl_id'),
                    "confidence_score": act.get('confidence_score', 0)
                }
            ))
        
        return results
```

### 5. Verifier

**File**: `chemagent/core/verifier.py`

Enforces provenance requirements:

```python
class ProvenanceVerifier:
    """Enforces evidence-grounded responses."""
    
    def verify(self, result: Any) -> VerificationResult:
        """
        Verify result has adequate provenance.
        
        Returns:
            VerificationResult with passed/failed + issues
        """
        issues = []
        
        # Check for provenance field
        if not hasattr(result, 'provenance'):
            issues.append("Missing provenance field")
        
        # Check source and source_id
        if not result.provenance.get('source'):
            issues.append("Missing provenance.source")
        if not result.provenance.get('source_id'):
            issues.append("Missing provenance.source_id")
        
        # Check numeric claims have references
        if isinstance(result, ActivityResult):
            if result.ic50 and not result.assay_id:
                issues.append("IC50 claim without assay_id")
            if result.ic50 and not result.reference_doi:
                issues.append("IC50 claim without paper reference")
        
        # Check confidence score
        if hasattr(result, 'confidence_score'):
            if result.confidence_score < 0.5:
                issues.append(f"Low confidence: {result.confidence_score}")
        
        passed = len(issues) == 0
        
        return VerificationResult(
            passed=passed,
            issues=issues,
            result=result if passed else None
        )
```

---

## Data Flow

### Example: "Find similar compounds to aspirin with IC50 < 100nM"

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. User Query                                                    │
│    "Find ChEMBL compounds similar to aspirin with IC50 < 100nM" │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. Intent Parser                                                 │
│                                                                  │
│    Pattern match: "similar.*to.*aspirin" → SIMILARITY_SEARCH    │
│    Entities: {compound: "aspirin", threshold: 0.7}              │
│    Constraints: {ic50_max: 100, units: "nM"}                    │
│                                                                  │
│    → ParsedIntent(SIMILARITY_SEARCH, ...)                       │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. Query Planner                                                 │
│                                                                  │
│    Plan:                                                         │
│    Step 1: resolve_compound_name("aspirin") → SMILES            │
│    Step 2: chembl_similarity_search(SMILES, 0.7)                │
│    Step 3: filter_by_activity(results, ic50_max=100, "nM")      │
│                                                                  │
│    → QueryPlan with 3 steps                                     │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. Tool Execution                                                │
│                                                                  │
│    [Step 1] resolve_compound_name("aspirin")                    │
│             → SMILES: "CC(=O)Oc1ccccc1C(=O)O"                   │
│                                                                  │
│    [Step 2] chembl_similarity_search(...)                       │
│             → 247 compounds (Tanimoto > 0.7)                    │
│                                                                  │
│    [Step 3] filter_by_activity(...)                             │
│             → 23 compounds with IC50 < 100nM                    │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 5. Verification                                                  │
│                                                                  │
│    For each compound:                                            │
│    ✓ Has ChEMBL ID                                              │
│    ✓ Has IC50 value with assay_id                               │
│    ✓ Has paper reference (DOI or ChEMBL doc_id)                │
│    ✓ Units are consistent (all nM)                              │
│                                                                  │
│    → All 23 compounds pass verification                          │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 6. Response Formatting                                           │
│                                                                  │
│    Found 23 compounds similar to aspirin (Tanimoto > 0.7)       │
│    with IC50 < 100 nM:                                          │
│                                                                  │
│    1. CHEMBL25 (Salicylic acid)                                 │
│       Similarity: 0.89                                           │
│       IC50: 45 nM (COX-2, ChEMBL Assay ID: CHEMBL1234)         │
│       Reference: DOI 10.1021/jm...                              │
│                                                                  │
│    2. CHEMBL521 (Indomethacin)                                  │
│       ...                                                        │
│                                                                  │
│    [Show all 23] [Export CSV] [Save to project]                │
└─────────────────────────────────────────────────────────────────┘
```

---

## LLM Orchestration

### Task-Aware Routing

Inspired by BioPipelines' [dynamic strategy selection](https://github.com/sdodlapa/BioPipelines/blob/main/docs/DYNAMIC_STRATEGY_IMPLEMENTATION_PLAN.md):

```python
class LLMOrchestrator:
    """Smart LLM routing based on task complexity."""
    
    TASK_ROUTING = {
        # Fast, deterministic tasks → local models
        "pattern_matching": {
            "preferred": "local-qwen-coder-7b",
            "latency_target_ms": 50,
            "cost": 0.0
        },
        
        # Standard queries → free cloud tiers
        "entity_extraction": {
            "preferred": "gemini-1.5-flash",
            "fallback": ["cerebras-llama-70b", "groq-mixtral"],
            "latency_target_ms": 300,
            "cost": 0.0  # Free tier
        },
        
        # Complex reasoning → paid models
        "synthesis_planning": {
            "preferred": "deepseek-v3",
            "fallback": ["gpt-4o"],
            "latency_target_ms": 2000,
            "cost": 0.27  # Per 1M tokens
        },
        
        # Embeddings → local server
        "embeddings": {
            "preferred": "local-bge-m3",
            "latency_target_ms": 100,
            "cost": 0.0
        }
    }
    
    def complete(
        self,
        prompt: str,
        task_type: str = "general"
    ) -> str:
        """Route to appropriate LLM based on task."""
        routing = self.TASK_ROUTING.get(task_type, {})
        
        # Try preferred model
        preferred = routing.get("preferred")
        try:
            return self._call_model(preferred, prompt)
        except ProviderUnavailableError:
            pass
        
        # Fallback chain
        for fallback in routing.get("fallback", []):
            try:
                return self._call_model(fallback, prompt)
            except ProviderUnavailableError:
                continue
        
        raise Exception("All LLM providers unavailable")
```

### Cost Optimization

```python
# Example cost breakdown for 1000 queries
COST_ANALYSIS = {
    "naive_gpt4": {
        "queries": 1000,
        "model": "gpt-4o",
        "avg_tokens": 500,
        "cost_per_1m": 2.50,
        "total_cost": 1.25  # $1.25
    },
    
    "smart_routing": {
        "queries": 1000,
        "breakdown": {
            "local_qwen": 800,  # 80% simple queries
            "gemini_free": 150,  # 15% standard
            "gpt4": 50  # 5% complex
        },
        "total_cost": 0.06  # $0.06 (20x cheaper!)
    }
}
```

---

## Provenance System

### Provenance Schema

Every result must include:

```python
@dataclass
class Provenance:
    """Mandatory provenance metadata."""
    
    # REQUIRED
    source: str  # "chembl", "bindingdb", "pubchem", etc.
    source_id: str  # Database-specific ID
    timestamp: str  # ISO 8601
    
    # OPTIONAL but encouraged
    query_params: Dict[str, Any]  # What parameters were used?
    confidence_score: float  # 0.0 to 1.0
    assay_id: Optional[str]  # For bioactivity data
    reference_doi: Optional[str]  # Paper reference
    data_version: Optional[str]  # ChEMBL release 33, etc.
    
    def is_complete(self) -> bool:
        """Check if provenance is adequate."""
        return bool(self.source and self.source_id and self.timestamp)
```

### Provenance Chain

For multi-step operations, maintain chain:

```python
result = {
    "compound": "CHEMBL25",
    "ic50": 45.0,
    "units": "nM",
    
    "provenance_chain": [
        {
            "step": 1,
            "operation": "chembl_similarity_search",
            "source": "chembl",
            "source_id": "CHEMBL25",
            "timestamp": "2026-01-09T10:30:00Z"
        },
        {
            "step": 2,
            "operation": "get_bioactivity",
            "source": "chembl",
            "assay_id": "CHEMBL1234",
            "source_id": "ACT_123456",
            "reference_doi": "10.1021/jm...",
            "timestamp": "2026-01-09T10:30:05Z"
        },
        {
            "step": 3,
            "operation": "standardize_units",
            "source": "local",
            "method": "convert_to_nm",
            "original_value": 0.045,
            "original_units": "μM",
            "timestamp": "2026-01-09T10:30:06Z"
        }
    ]
}
```

---

## Security & Governance

### Role-Based Access Control

```python
class PermissionLevel(Enum):
    """User permission levels."""
    
    READONLY = 1  # Can query, cannot export
    STANDARD = 2  # Can query and export
    ADVANCED = 3  # Can run custom filters
    ADMIN = 4  # Full access

class SecurityManager:
    """Enforce access controls."""
    
    PERMISSIONS = {
        PermissionLevel.READONLY: [
            "query", "search", "view_results"
        ],
        PermissionLevel.STANDARD: [
            "query", "search", "view_results",
            "export_csv", "save_project"
        ],
        PermissionLevel.ADVANCED: [
            "query", "search", "view_results",
            "export_csv", "save_project",
            "custom_smarts", "batch_processing"
        ],
        PermissionLevel.ADMIN: ["*"]
    }
```

### Audit Logging

```python
@dataclass
class AuditEntry:
    """Audit log entry."""
    
    timestamp: str
    user_id: str
    action: str  # "query", "export", "delete", etc.
    resource: str  # What was accessed?
    status: str  # "success", "failed", "denied"
    details: Dict[str, Any]
    ip_address: Optional[str]

class AuditLogger:
    """Thread-safe audit logging."""
    
    def log(self, entry: AuditEntry):
        """Write to audit log."""
        with open("logs/audit.jsonl", "a") as f:
            f.write(json.dumps(asdict(entry)) + "\n")
```

---

## Deployment Architecture

### Docker Compose Setup

```yaml
# docker-compose.yml
version: '3.8'

services:
  # Main ChemAgent API
  chemagent-api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - REDIS_URL=redis://cache:6379
    depends_on:
      - cache
      - embeddings
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
  
  # Local embeddings server (BGE-M3)
  embeddings:
    image: ghcr.io/huggingface/text-embeddings-inference:latest
    ports:
      - "8001:80"
    command: --model-id BAAI/bge-m3 --port 80
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
  
  # Redis for caching
  cache:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
  
  # Web UI (Gradio)
  web-ui:
    build:
      context: .
      dockerfile: Dockerfile.web
    ports:
      - "7860:7860"
    depends_on:
      - chemagent-api

volumes:
  redis-data:
```

### Kubernetes (Production)

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: chemagent
spec:
  replicas: 3
  selector:
    matchLabels:
      app: chemagent
  template:
    metadata:
      labels:
        app: chemagent
    spec:
      containers:
      - name: chemagent
        image: chemagent:1.0.0
        ports:
        - containerPort: 8000
        env:
        - name: GEMINI_API_KEY
          valueFrom:
            secretKeyRef:
              name: llm-secrets
              key: gemini-key
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
```

---

## Next Steps

See [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) for detailed development roadmap.

**Phase 1 Priorities**:
1. ChemOps toolbelt (RDKit wrappers)
2. Database clients (ChEMBL, BindingDB)
3. Intent parser (pattern-based)
4. Simple orchestrator
5. Provenance tracking
6. 100+ unit tests

**Key Metrics to Track**:
- Tool selection accuracy
- Provenance completeness rate
- Query latency (p50, p95, p99)
- Cost per query
- User satisfaction (if applicable)
