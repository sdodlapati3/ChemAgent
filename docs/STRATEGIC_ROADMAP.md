# ChemAgent Strategic Roadmap: Building a Deployable Pharma Agentic System

## Executive Summary

**Current State**: We have a working OptimalAgent with hybrid architecture, now enhanced with Open Targets evidence integration.

**Recent Progress (Phase B Completed)**:
- ✅ Provenance foundation created (`src/chemagent/core/provenance.py`)
- ✅ Open Targets Platform integration (`src/chemagent/clients/opentargets_client.py`)
- ✅ Evidence-based tools with provenance tracking
- ✅ Automatic tool chaining for target→disease associations
- ✅ Entity extraction for targets (EGFR, BRAF, etc.)

**Strategic Insight**: The ChatGPT analysis is correct:
- **"Don't start multi-agent; start agentic"** - Single orchestrator + tools is the right foundation
- **"Provenance-first answers"** - Every claim needs traceable evidence ✅ IMPLEMENTED
- **"Evaluation harness"** - Critical for deployment (NEXT PRIORITY)

**Target Product**: **Evidence-Grounded Target→Compound Copilot**

---

## Analysis: What Existing Systems Get Right & Wrong

### 1. ChemCrow (ur-whitelab) ⭐
**What they got right:**
- LLM + RDKit + chemistry tools pattern
- Clean tool definitions
- Langchain integration

**What's missing:**
- No provenance tracking (claims without sources)
- No evaluation harness
- API restrictions limit reproducibility

### 2. BioChatter (biocypher) ⭐⭐
**What they got right:**
- Knowledge graph native
- Evaluation framework emphasis
- Multiple LLM provider support
- Active benchmark development

**What's missing:**
- Less chemistry-focused (more general biomedical)
- Not pharma workflow-oriented

### 3. AIAgents4Pharma (VirtualPatientEngine) ⭐⭐⭐
**What they got right:**
- Multiple specialized agents (Talk2BioModels, Talk2KnowledgeGraphs, Talk2Scholars)
- Docker deployment
- Streamlit frontends
- LangGraph architecture

**What's missing:**
- Agents are domain-silos (not integrated workflow)
- No provenance/evidence tracking
- Limited evaluation

### 4. Chemprop (MIT)
**What they got right:**
- Message passing neural networks for property prediction
- Strong scientific foundation
- Well-documented

**What's missing:**
- Not an agent system (ML library only)
- Could be a tool in our toolbelt

### 5. NVIDIA BioNeMo
**What they got right:**
- Production-grade NIM microservices
- Structure prediction, docking, molecular generation
- Enterprise scale

**What's missing:**
- Heavy/expensive infrastructure
- Less flexible than agent approach

---

## The Gap We Can Fill

None of the existing systems do **Evidence-Grounded Pharmaceutical Intelligence** well:

```
User: "What's the evidence that EGFR is implicated in lung cancer?"

Current Systems: "EGFR is a target in lung cancer..." (no sources)

What We Should Do:
├── Query Open Targets API for EGFR-lung cancer association
├── Return: Association score: 0.95, Evidence sources:
│   ├── Literature: 847 publications (PubMed IDs)
│   ├── Genetic: GWAS studies (study IDs)
│   ├── Expression: Differential expression data
│   └── Drugs: FDA-approved EGFR inhibitors
└── Every claim traceable to source database + record ID
```

---

## Strategic Plan: Three Concrete Builds

### Plan 1: Target→Compound Copilot (RECOMMENDED) ⭐⭐⭐

**Vision**: A system for R&D scientists doing target triage and compound intelligence.

**Real Workflows It Supports**:
1. Target validation: "What's the evidence for [target] in [disease]?"
2. Compound intelligence: "What known ligands exist for [target], and their potencies?"
3. SAR filtering: "Find compounds matching [scaffold] with [property constraints]"
4. Competitive analysis: "What's the clinical pipeline for [target]?"

**Architecture**:
```
┌────────────────────────────────────────────────────────────────────┐
│                    EVIDENCE-GROUNDED COPILOT                        │
├────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   User Query → Single Orchestrator Agent (Groq-70B)                │
│                        │                                           │
│                        ▼                                           │
│   ┌──────────────────────────────────────────────────────────┐    │
│   │              PROVENANCE-AWARE TOOL LAYER                 │    │
│   ├──────────────────────────────────────────────────────────┤    │
│   │                                                          │    │
│   │  open_targets_get_evidence(target, disease)              │    │
│   │  → Returns: {score, sources: [{type, id, url}...]}       │    │
│   │                                                          │    │
│   │  chembl_get_ligands(target_chembl_id)                    │    │
│   │  → Returns: {compounds: [{id, IC50, Ki, source}...]}     │    │
│   │                                                          │    │
│   │  rdkit_filter_compounds(smiles_list, constraints)        │    │
│   │  → Returns: {passed: [...], failed: [...]}               │    │
│   │                                                          │    │
│   │  uniprot_get_protein(accession)                          │    │
│   │  → Returns: {name, function, GO_terms, source}           │    │
│   │                                                          │    │
│   └──────────────────────────────────────────────────────────┘    │
│                        │                                           │
│                        ▼                                           │
│   ┌──────────────────────────────────────────────────────────┐    │
│   │              EVIDENCE SYNTHESIZER                         │    │
│   │  - Formats answer with inline citations                   │    │
│   │  - Generates "Evidence Table" (source, ID, confidence)    │    │
│   │  - Attaches machine-readable evidence block               │    │
│   └──────────────────────────────────────────────────────────┘    │
│                                                                     │
└────────────────────────────────────────────────────────────────────┘
```

**Data Sources** (all public, high utility):
| Source | What it provides | API |
|--------|------------------|-----|
| Open Targets | Target-disease evidence scores | GraphQL |
| ChEMBL | Bioactivity, ligands, assays | REST |
| BindingDB | Protein-ligand affinities | REST |
| UniProt | Protein sequences, annotations | REST |
| PubChem | Compound structures | REST |
| PDB/AlphaFold | Protein structures (optional) | REST |

**Differentiator**: Every numeric claim (IC50, association score) carries:
```json
{
  "value": 45.2,
  "unit": "nM",
  "source": "ChEMBL",
  "record_id": "CHEMBL12345",
  "assay_id": "CHEMBL789",
  "url": "https://www.ebi.ac.uk/chembl/assay_report_card/CHEMBL789"
}
```

---

### Plan 2: Structure Query Engine with Agentic Query Planning

**Vision**: "Find molecules like this, but within these constraints" - turning natural language into repeatable query plans.

**Real Workflows**:
1. "Find analogs of ibuprofen with better selectivity for COX-2"
2. "Search for compounds with MW < 500, LogP 2-4, and a benzimidazole scaffold"
3. "Compare purchasing options for these 50 hits"

**Architecture**:
```
User: "Find COX-2 selective NSAIDs with LogP < 3"

┌─────────────────────────────────────────────────────────────────┐
│                 QUERY PLANNING AGENT                            │
├─────────────────────────────────────────────────────────────────┤
│ Step 1: Parse constraints                                       │
│   → target: COX-2 (CHEMBL230)                                  │
│   → selectivity: COX-2/COX-1 ratio > 10                        │
│   → property: LogP < 3                                         │
│                                                                 │
│ Step 2: Generate Query Plan (reproducible)                     │
│   {                                                            │
│     "plan_id": "query_20260112_001",                          │
│     "steps": [                                                 │
│       {"tool": "chembl_get_activities",                       │
│        "params": {"target": "CHEMBL230", "type": "IC50"}},    │
│       {"tool": "chembl_get_activities",                       │
│        "params": {"target": "CHEMBL218", "type": "IC50"}},    │
│       {"tool": "rdkit_filter",                                │
│        "params": {"LogP": {"max": 3}}}                        │
│     ]                                                          │
│   }                                                            │
│                                                                 │
│ Step 3: Execute & Return                                       │
│   → 23 compounds match                                         │
│   → Evidence table with selectivity ratios                     │
│   → Query plan saved for reproducibility                       │
└─────────────────────────────────────────────────────────────────┘
```

**Key Innovation**: Query plans are **saved and reproducible**. Users can:
- Re-run the same query later
- Modify parameters and compare
- Share queries with colleagues
- Audit exactly what was searched

---

### Plan 3: Virtual Screening Workflow Agent (Advanced)

**Vision**: Orchestrate computational drug discovery workflows end-to-end.

**Real Workflows**:
1. "Run virtual screening against EGFR kinase domain"
2. "Dock these 100 compounds and rank by predicted binding"
3. "Generate a report comparing screening results"

**Architecture** (requires more compute):
```
User: "Screen compounds against EGFR"

┌─────────────────────────────────────────────────────────────────┐
│              VIRTUAL SCREENING WORKFLOW AGENT                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ Phase 1: Target Structure                                       │
│   └─ Fetch PDB structure (4HJO) OR AlphaFold prediction        │
│   └─ Identify binding pocket                                   │
│                                                                 │
│ Phase 2: Ligand Preparation                                     │
│   └─ Standardize SMILES                                        │
│   └─ Generate 3D conformers                                    │
│   └─ Protonate at physiological pH                             │
│                                                                 │
│ Phase 3: Docking (sandboxed compute)                           │
│   └─ Run AutoDock Vina / DiffDock                              │
│   └─ Score poses                                               │
│                                                                 │
│ Phase 4: Analysis & Report                                      │
│   └─ Rank by binding affinity                                  │
│   └─ ADMET predictions (Chemprop)                              │
│   └─ Generate PDF report with provenance                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Guardrails Required**:
- ❌ NO synthesis route suggestions (safety)
- ✅ Strong provenance for all predictions
- ✅ Sandboxed compute environments
- ✅ Clear "prediction" vs "experimental" labels

---

## Implementation Roadmap

### Phase A: Foundation (Weeks 1-2) ✅ COMPLETE
- [x] Core tool registry with ChEMBL, RDKit
- [x] OptimalAgent with hybrid fast/smart paths
- [x] Conversation memory
- [x] Basic API server

### Phase B: Provenance Layer (Weeks 3-4) ✅ COMPLETE
- [x] Add `ProvenanceRecord` to all tool outputs
- [x] Implement Open Targets integration
- [x] Open Targets client with GraphQL API
- [x] Evidence synthesizer with citations
- [x] Target entity extraction (EGFR, BRAF, etc.)
- [x] Automatic tool chaining for associations

**Files Created:**
- `src/chemagent/core/provenance.py` - Provenance tracking foundation
- `src/chemagent/clients/opentargets_client.py` - Open Targets GraphQL client
- `src/chemagent/tools/opentargets.py` - Open Targets tools with provenance

**Example Query Now Working:**
```
User: "What evidence links EGFR to lung cancer?"

Agent Response (with provenance):
├── Target found: ENSG00000146648 (EGFR)
├── Disease associations:
│   ├── Non-small cell lung carcinoma: 0.85 (literature: 0.999, drug: 0.991)
│   ├── Lung adenocarcinoma: 0.77
│   └── Cancer: 0.74
├── Known drugs: Erlotinib, Gefitinib, Afatinib
└── Source: Open Targets Platform (platform.opentargets.org)
```

### Phase C: Evaluation Harness (Weeks 5-6) ✅ COMPLETE
- [x] Create assertion-based evaluation framework
- [x] Implement constraint checking (not exact answer matching)
- [x] Build task suite with 20 evaluation tasks across 8 categories
- [x] Provenance assertions (HasProvenance, SourceIs)
- [x] Entity assertions (ContainsEntity, ContainsAnyEntity)
- [x] Numeric assertions (HasNumericValue, HasAssociationScore)
- [x] Quality assertions (ResponseLength, HasStructuredData)
- [x] Hallucination detection (NoHallucination)
- [x] Rate-limited LLM calls with exponential backoff

**Files Created:**
- `src/chemagent/evaluation/assertions.py` - Constraint-based assertions
- `src/chemagent/evaluation/task_suite.py` - 20 evaluation tasks across 8 categories
- `src/chemagent/evaluation/assertion_evaluator.py` - Evaluation runner with reporting

**Example Evaluation:**
```python
task = EvaluationTask(
    task_id="tv_001",
    query="What evidence links EGFR to lung cancer?",
    category=TaskCategory.TARGET_VALIDATION,
    difficulty=TaskDifficulty.EASY,
    assertions=[
        HasProvenance(),
        SourceIs("Open Targets"),
        ContainsAnyEntity(["EGFR", "epidermal growth factor receptor"]),
        ContainsAnyEntity(["lung cancer", "NSCLC", "non-small cell"]),
        HasAssociationScore(),
        NoHallucination(),
    ]
)

# Result: ✅ 6/6 assertions passed in 1288ms
```

**Task Categories:**
- TARGET_VALIDATION (4 tasks)
- DISEASE_ASSOCIATION (1 task)
- COMPOUND_LOOKUP (4 tasks)
- PROPERTY_CALCULATION (2 tasks)
- SIMILARITY_SEARCH (2 tasks)
- BIOACTIVITY (2 tasks)
- MULTI_STEP (2 tasks)
- EDGE_CASE (3 tasks)

### Phase D: Verifier Gate (Weeks 7-8) ✅ COMPLETE
- [x] Implement claim extraction from LLM responses
  - ClaimExtractor with regex patterns for IC50, Ki, Kd, molecular weight, LogP, PSA
  - ClaimType enum: NUMERIC, ENTITY, ASSOCIATION, PROPERTY, SOURCE
  - Deduplication of similar claims
- [x] Cross-reference claims against tool results
  - ClaimVerifier with evidence extraction from ChEMBL, Open Targets, RDKit results
  - Support for both list and dict data formats
  - First-result priority for multi-compound searches
- [x] Reject responses with unsupported claims
  - VerifierGate with three modes: reject, annotate, flag
  - Configurable confidence threshold (default 0.5)
  - Clear rejection messages for low-confidence responses
- [x] "Confidence" scoring based on evidence strength
  - Weighted scoring: verified=1.0, unverified=0.6, contradicted=0.0
  - Trust calculation based on contradiction ratio
  - Integrated into OptimalAgent fast_path and smart_path

**Implementation Details**:
- `src/chemagent/core/verifier.py` (~870 lines)
- 20 unit tests in `tests/unit/test_verifier.py`
- Verification badge appended to responses (✅ Verified, ⚠️ Low confidence)
- Footer stripping to prevent recursive extraction

### Phase E: Advanced Features (Future)
- [ ] Query plan persistence
- [ ] User workspaces
- [ ] Export to reference managers
- [ ] Structure-based screening (Plan 3)

---

## What We Should STOP Doing

1. **❌ Multi-agent with separate LLMs per tool**
   - Current: CompoundAgent → LLM → chembl_search
   - Better: Single Agent → chembl_search directly

2. **❌ Building more agents before evaluation**
   - Can't improve what you can't measure

3. **❌ Focusing on architecture over provenance**
   - Users need trust, not elegant code

---

## What We Should START Doing

1. **✅ Add provenance to every tool**
   - Every numeric value has source + record ID

2. **✅ Build evaluation harness**
   - 100+ test cases with constraints
   - CI/CD runs evaluation on changes

3. **✅ Integrate Open Targets**
   - Target-disease evidence is killer feature
   - Differentiates from ChemCrow/AIAgents4Pharma

4. **✅ Add Verifier gate**
   - System refuses to answer without evidence
   - Builds user trust

---

## Comparison: Current vs Target Architecture

| Aspect | Current | Target |
|--------|---------|--------|
| Agent pattern | Multi-agent (overkill) | Single orchestrator + tools |
| Provenance | None | Every claim traceable |
| Evaluation | Ad-hoc testing | 100+ task suite |
| Evidence | Not required | Required for response |
| Query reproducibility | No | Saved query plans |
| Data sources | ChEMBL, RDKit | +Open Targets, BindingDB, UniProt |

---

## Success Metrics

### Deployment Ready When:
1. ✅ 95% of responses have full provenance
2. ✅ Evaluation suite passes 90%+
3. ✅ Average response time < 5 seconds
4. ✅ Zero unsupported claims in production

### KPIs to Track:
- Tool call success rate
- Provenance attachment rate
- Unsupported claim rate
- User satisfaction (if deployed)
- Query plan reuse rate

---

## Conclusion

The most valuable thing we can build is not more agents—it's **trustworthy answers**.

**Priority Order**:
1. **Provenance layer** - Trace every claim
2. **Evaluation harness** - Measure quality
3. **Verifier gate** - Refuse unsupported answers
4. **Open Targets integration** - Target-disease evidence
5. **Query planning** - Reproducible searches

This turns ChemAgent from a demo into infrastructure that scientists can actually trust.
