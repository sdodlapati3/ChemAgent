# ChemAgent

> **AI-Powered Pharmaceutical Research Assistant**  
> Natural language → Evidence-grounded chemical intelligence → Traceable insights

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## 🚀 Quick Start

```bash
# 1. Create environment
conda create -n chemagent python=3.10
conda activate chemagent

# 2. Install dependencies
pip install -e ".[dev]"

# 3. Set API keys (optional - for cloud LLMs)
export GEMINI_API_KEY="your-key"
export OPENAI_API_KEY="your-key"

# 4. Launch web interface
python -m chemagent.web

# 5. Try a query:
#    "Find ChEMBL compounds similar to aspirin with IC50 < 100nM"
#    "What's the evidence for EGFR in lung cancer?"
```

---

## 🎯 What is ChemAgent?

ChemAgent is a **production-grade agentic system** for pharmaceutical R&D that combines:

- **Evidence-grounded answers** - Every claim traced to ChEMBL ID, PubMed citation, or experimental data
- **Deterministic chemistry tools** - RDKit-powered property calculation, similarity search, filtering
- **Multi-source intelligence** - ChEMBL, BindingDB, Open Targets, UniProt, PubChem, PDB
- **Smart LLM orchestration** - Local models for fast queries, cloud for complex reasoning
- **Project workspaces** - Persistent sessions with reproducible query history

### Design Philosophy

1. **Tools First, Agents Second** - Build deterministic chemistry functions before adding LLM reasoning
2. **Provenance First** - Never return a claim without source evidence (ChEMBL ID, paper, etc.)
3. **Single Orchestrator** - Avoid multi-agent complexity unless it demonstrably helps
4. **Evaluation Driven** - 100+ golden queries with automated testing
5. **Production Ready** - Audit logs, security boundaries, reproducible runs

---

## ✨ Features

### 🔬 Evidence-Grounded Target Intelligence

```python
from chemagent import ChemAgent

agent = ChemAgent()

# Query with automatic provenance
result = agent.query(
    "What's the evidence that EGFR is implicated in lung cancer?"
)

print(result.answer)
# Evidence score: 0.89
# Key findings:
# - 127 associations in Open Targets (ENSG00000146648)
# - Phase 3 clinical trials for EGFR inhibitors (PMIDs: ...)
# - Structural mutations in 15% of NSCLC (ClinVar: ...)

print(result.provenance)
# [
#   {"source": "opentargets", "id": "ENSG00000146648", "score": 0.89},
#   {"source": "pubmed", "pmid": "12345678", "relevance": 0.95},
#   ...
# ]
```

### 🧪 Compound Intelligence & SAR

```python
# Find similar compounds with bioactivity
result = agent.query(
    "Find ChEMBL compounds similar to aspirin with antiplatelet activity"
)

# Returns: Tanimoto similarity + IC50 data + target info
for compound in result.compounds[:5]:
    print(f"{compound.chembl_id}: {compound.similarity:.2f}")
    print(f"  IC50: {compound.ic50} {compound.units}")
    print(f"  Target: {compound.target_name}")
    print(f"  Reference: {compound.paper_doi}")
```

### 🎯 Property-Based Filtering

```python
# Drug-like molecules with specific constraints
result = agent.filter_compounds(
    input_smiles_file="candidates.smi",
    filters={
        "lipinski": True,
        "mw_range": (300, 500),
        "clogp_range": (0, 5),
        "tpsa_max": 140,
        "rotatable_bonds_max": 10,
    }
)

# Export with provenance
result.export("filtered_compounds.csv", include_provenance=True)
```

### 📊 Project Workspaces

```python
# Persistent investigation workspace
project = agent.create_project("EGFR_inhibitors_nov2025")

project.add_query("Find EGFR crystal structures in PDB")
project.add_query("Get known EGFR inhibitors from ChEMBL")
project.add_compounds(smiles_list)
project.apply_filter("lipinski")

# Export reproducible notebook
project.export_notebook("EGFR_analysis.ipynb")
```

---

## 🏗️ Architecture

ChemAgent is built on proven patterns from [BioPipelines](https://github.com/sdodlapa/BioPipelines):

```
┌─────────────────────────────────────────────────────────────┐
│                   ChemAgent Architecture                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Interface Layer                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐   │
│  │   Web UI     │  │  MCP Server  │  │  Python API     │   │
│  │  (Gradio)    │  │ (Claude Code)│  │                 │   │
│  └──────┬───────┘  └──────┬───────┘  └────────┬────────┘   │
│         └─────────────────┼──────────────────┬─┘            │
│                           ▼                                  │
│  ╔════════════════════════════════════════════════════╗     │
│  ║          ChemAgent Facade (single entry)           ║     │
│  ║  query() | search() | filter() | report()          ║     │
│  ╚════════════════════════════════════════════════════╝     │
│                           │                                  │
│  ┌────────────────────────────────────────────────────┐     │
│  │      Intent Parser (2-stage hybrid)                │     │
│  │  Stage 1: Pattern matching (80% fast path, <15ms) │     │
│  │  Stage 2: LLM arbiter (20% complex queries)       │     │
│  └────────────────────────────────────────────────────┘     │
│                           │                                  │
│  ┌────────────────────────────────────────────────────┐     │
│  │    Orchestrator Agent (single agent)               │     │
│  │    • Query planner                                 │     │
│  │    • Tool selector (RAG-enhanced)                  │     │
│  │    • Execution engine                              │     │
│  │    • Provenance tracker                            │     │
│  └────────────────────────────────────────────────────┘     │
│                           │                                  │
│  ┌────────────────────────────────────────────────────┐     │
│  │       ChemOps Toolbelt (deterministic)             │     │
│  │                                                     │     │
│  │  RDKit Tools          │  DB Connectors             │     │
│  │  • standardize()      │  • ChEMBLClient            │     │
│  │  • calc_properties()  │  • BindingDBClient         │     │
│  │  • similarity()       │  • OpenTargetsClient       │     │
│  │  • substructure()     │  • UniProtClient           │     │
│  │  • filter_druglike()  │  • PubChemClient           │     │
│  └────────────────────────────────────────────────────┘     │
│                           │                                  │
│  ┌────────────────────────────────────────────────────┐     │
│  │       Verifier Layer (provenance gate)             │     │
│  │  • Reject claims without source IDs                │     │
│  │  • Cross-check numeric values                      │     │
│  │  • Flag unsupported assertions                     │     │
│  └────────────────────────────────────────────────────┘     │
│                           │                                  │
│  ┌────────────────────────────────────────────────────┐     │
│  │       LLM Provider Cascade                         │     │
│  │  Local (Qwen-Coder) → Gemini → DeepSeek → GPT     │     │
│  │  Task-aware routing: fast vs complex              │     │
│  └────────────────────────────────────────────────────┘     │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## 📚 Data Sources

All public, high-quality chemistry/pharma databases:

| Source | Purpose | API | Records |
|--------|---------|-----|---------|
| **ChEMBL** | Bioactivity data | REST + Python client | 2.3M compounds |
| **BindingDB** | Protein-ligand affinities | REST | 2.8M measurements |
| **Open Targets** | Target-disease associations | GraphQL | 24k targets |
| **UniProt** | Protein information | REST | 245M proteins |
| **PubChem** | Chemical structures | REST | 114M compounds |
| **PDB** | Protein structures | REST | 210k structures |
| **AlphaFold DB** | Predicted structures | Bulk/API | 214M predictions |
| **ZINC** | Purchasable compounds | Search | 230M compounds |

---

## 🛠️ Components

### Core Modules

```
chemagent/
├── core/
│   ├── intent_parser.py      # 2-stage NL understanding
│   ├── orchestrator.py        # Main agent logic
│   ├── query_planner.py       # Query → tool execution plan
│   └── verifier.py            # Provenance enforcement
├── tools/
│   ├── rdkit_tools.py         # Chemistry operations
│   ├── chembl_client.py       # ChEMBL API wrapper
│   ├── bindingdb_client.py    # BindingDB API wrapper
│   ├── opentargets_client.py  # Open Targets GraphQL
│   └── uniprot_client.py      # UniProt REST API
├── llm/
│   ├── providers.py           # LLM provider adapters
│   ├── orchestrator.py        # Smart routing logic
│   └── strategies.py          # Local-first, cloud, etc.
├── rag/
│   ├── knowledge_base.py      # Indexed chem knowledge
│   ├── retriever.py           # Hybrid search
│   └── sources/               # RDKit docs, MedChem rules
├── workspace/
│   ├── project.py             # Persistent workspaces
│   ├── history.py             # Query history
│   └── export.py              # Jupyter notebook export
└── evaluation/
    ├── golden_queries.py      # Test suite
    ├── metrics.py             # Accuracy tracking
    └── runner.py              # Evaluation harness
```

---

## 🧪 Testing

ChemAgent has comprehensive testing inspired by BioPipelines:

```bash
# Run all tests
pytest tests/

# Run specific test suites
pytest tests/unit/              # Unit tests (fast)
pytest tests/integration/       # Integration tests
pytest tests/evaluation/        # Golden query evaluation

# Run with coverage
pytest --cov=chemagent --cov-report=html
```

### Golden Query Evaluation

```python
# 100+ pre-defined queries with expected behavior
from chemagent.evaluation import GoldenQueryRunner

runner = GoldenQueryRunner()
results = runner.run_all()

print(f"Accuracy: {results.accuracy:.1%}")
print(f"Provenance completeness: {results.provenance_rate:.1%}")
print(f"Avg latency: {results.avg_latency_ms:.0f}ms")
print(f"Cost per query: ${results.avg_cost:.4f}")
```

---

## 📖 Documentation

- [**Architecture Guide**](docs/ARCHITECTURE.md) - System design deep-dive
- [**Implementation Plan**](docs/IMPLEMENTATION_PLAN.md) - Development roadmap
- [**Comparison Analysis**](docs/COMPARISON.md) - ChemAgent vs ChemCrow/DEDA/etc.
- [**API Reference**](docs/API.md) - Complete API documentation
- [**Contributing Guide**](CONTRIBUTING.md) - How to contribute

---

## 🗺️ Roadmap

### Phase 1: Foundation ✅ (Weeks 1-3)
- [x] ChemOps toolbelt (RDKit wrappers)
- [x] Database clients (ChEMBL, BindingDB, etc.)
- [x] Intent parser with pattern matching
- [x] Simple orchestrator
- [x] Provenance tracking
- [x] 100+ unit tests

### Phase 2: Intelligence (Weeks 4-6)
- [ ] RAG system for chemistry knowledge
- [ ] LLM provider routing (local + cloud)
- [ ] Evaluation harness (100 golden queries)
- [ ] Query optimization

### Phase 3: Production (Weeks 7-9)
- [ ] Project workspaces
- [ ] Web UI (Gradio)
- [ ] MCP server (Claude Code integration)
- [ ] Deployment (Docker)
- [ ] Security & audit logs

### Future Enhancements
- [ ] Multi-modal support (structure visualization)
- [ ] Synthesis planning integration
- [ ] ADMET prediction
- [ ] Patent landscape analysis
- [ ] Hypothesis generation mode

---

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

Key areas:
- 🧪 **Chemistry tools** - More RDKit functions, new APIs
- 🗄️ **Data sources** - Additional databases (Reaxys, SciFinder, etc.)
- 🤖 **LLM improvements** - Better prompts, new providers
- 📊 **Evaluation** - More golden queries, better metrics
- 📚 **Documentation** - Tutorials, examples

---

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

- Architecture inspired by [BioPipelines](https://github.com/sdodlapa/BioPipelines)
- Built on [RDKit](https://www.rdkit.org/) for cheminformatics
- Powered by [ChEMBL](https://www.ebi.ac.uk/chembl/), [BindingDB](https://www.bindingdb.org/), and other public databases
- LLM orchestration patterns from production bioinformatics systems

---

## 📞 Contact

- **Issues**: [GitHub Issues](https://github.com/yourusername/ChemAgent/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/ChemAgent/discussions)
- **Email**: your.email@institution.edu

---

**Status**: 🚧 Active development - Phase 1 in progress
