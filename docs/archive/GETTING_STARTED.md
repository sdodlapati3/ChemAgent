# Getting Started with ChemAgent

This guide will help you set up and start using ChemAgent.

## Quick Start (5 minutes)

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd ChemAgent
```

### 2. Set Up Environment

**Option A: Using Conda (Recommended)**
```bash
conda env create -f environment.yml
conda activate chemagent
pip install -e ".[dev]"
```

**Option B: Using pip + virtualenv**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e ".[dev,llm,web]"
```

### 3. Verify Installation

```bash
python -c "from chemagent import ChemAgent; print('✓ Installation successful!')"
```

### 4. Run Your First Example

```bash
python examples/basic_usage.py
```

You should see output demonstrating SMILES standardization, property calculation, Lipinski evaluation, similarity search, and more.

## Development Setup

### Running Tests

```bash
# Run all tests
make test

# Run fast tests only (skip slow tests)
make test-fast

# Run with coverage
make test-cov
```

### Code Quality

```bash
# Format code
make format

# Run linters
make lint
```

### Docker Deployment

```bash
# Build Docker image
make docker-build

# Run with Docker Compose
make docker-run

# Stop containers
make docker-stop
```

## Usage Examples

### Basic Chemistry Operations

```python
from chemagent.tools.rdkit_tools import RDKitTools
from rdkit import Chem

tools = RDKitTools()

# Standardize SMILES
result = tools.standardize_smiles("CC(=O)Oc1ccccc1C(=O)O")
print(f"Canonical: {result.smiles}")
print(f"InChI Key: {result.inchi_key}")

# Calculate properties
mol = Chem.MolFromSmiles(result.smiles)
props = tools.calc_molecular_properties(mol)
print(f"MW: {props.molecular_weight:.2f}")
print(f"LogP: {props.logp:.2f}")

# Check drug-likeness
lipinski = tools.calc_lipinski(mol)
print(f"Drug-like: {lipinski.passes}")
```

### Similarity Search

```python
from rdkit import Chem

query = Chem.MolFromSmiles("CCO")  # Ethanol
database = [
    Chem.MolFromSmiles("CCCO"),    # Propanol
    Chem.MolFromSmiles("c1ccccc1"), # Benzene
]

results = tools.similarity_search(query, database, threshold=0.5)
for r in results:
    print(f"Match {r.index}: similarity = {r.similarity:.3f}")
```

## Project Structure

```
ChemAgent/
├── src/chemagent/          # Main package
│   ├── __init__.py         # Package entry point & facade
│   ├── core/               # Core orchestration (TODO)
│   ├── tools/              # Chemistry tools
│   │   └── rdkit_tools.py  # RDKit operations (COMPLETE)
│   ├── database/           # Database clients (TODO)
│   ├── llm/                # LLM routing (TODO)
│   └── web/                # Web interface (TODO)
├── tests/                  # Test suite
│   ├── unit/               # Unit tests
│   └── integration/        # Integration tests (TODO)
├── docs/                   # Documentation
│   ├── ARCHITECTURE.md     # System architecture
│   ├── IMPLEMENTATION_PLAN.md  # 9-week roadmap
│   └── COMPARISON.md       # vs existing systems
├── examples/               # Usage examples
└── data/                   # Data directories
```

## Current Status

### ✅ Completed (Phase 1, Week 1)

- [x] Project scaffold with BioPipelines-inspired architecture
- [x] RDKit tools with provenance tracking (600+ lines)
- [x] Comprehensive test suite (400+ lines, 50+ tests)
- [x] Documentation (README, ARCHITECTURE, IMPLEMENTATION_PLAN, COMPARISON)
- [x] Package configuration (pyproject.toml, environment.yml)
- [x] Docker setup (Dockerfile, docker-compose.yml)
- [x] Development tooling (Makefile, pytest, black, mypy, ruff)

### 🚧 In Progress (Phase 1, Weeks 2-3)

- [ ] Database clients (ChEMBL, BindingDB, UniProt, Open Targets)
- [ ] Intent parser with 50+ chemistry query patterns
- [ ] Query planner with dependency resolution
- [ ] ChemOrchestrator for coordinating tool execution
- [ ] Provenance system with audit trail
- [ ] 150+ unit tests for core functionality

### 📋 Planned (Phases 2-3)

- Phase 2 (Weeks 4-6): RAG system, LLM orchestration, evaluation suite
- Phase 3 (Weeks 7-9): Project workspaces, Gradio web UI, MCP server

## Configuration

### Environment Variables

Create a `.env` file:

```bash
# LLM API Keys (optional for Phase 1)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GROQ_API_KEY=gsk_...

# Database Configuration
CHEMAGENT_CACHE_DIR=~/.cache/chemagent
CHEMAGENT_LOG_LEVEL=INFO

# Production Settings
CHEMAGENT_ENV=development
```

### LLM Provider Setup (Phase 2+)

ChemAgent will support multiple LLM providers with automatic cost-optimized routing:

1. **Free/Local Models** (Groq, Cerebras, Ollama)
2. **Cloud Models** (GPT-4o-mini, Claude-3-Haiku)
3. **Fallback Chain** (automatic failover)

Configuration in `config/provider_models.yaml` (to be created in Phase 2).

## Testing

### Unit Tests

```bash
# Run all unit tests
pytest tests/unit/

# Run specific test file
pytest tests/unit/test_rdkit_tools.py -v

# Run specific test
pytest tests/unit/test_rdkit_tools.py::TestStandardization::test_standardize_valid_smiles -v
```

### Coverage

```bash
pytest --cov=src/chemagent --cov-report=html
open htmlcov/index.html
```

## Troubleshooting

### RDKit Installation Issues

If RDKit fails to install via pip:

```bash
# Use conda instead
conda install -c conda-forge rdkit
```

### Import Errors

Make sure package is installed in editable mode:

```bash
pip install -e .
```

### Test Failures

Ensure all dependencies are installed:

```bash
pip install -e ".[dev]"
```

## Next Steps

1. **Read the Documentation**
   - [ARCHITECTURE.md](docs/ARCHITECTURE.md) - System design
   - [IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md) - Development roadmap
   - [COMPARISON.md](docs/COMPARISON.md) - vs ChemCrow, DEDA, etc.

2. **Run Examples**
   - `examples/basic_usage.py` - Chemistry operations
   - More examples coming in Phase 2-3

3. **Contribute**
   - Check [IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md) for tasks
   - Follow Phase 1 → Phase 2 → Phase 3 order
   - Start with database clients (Week 1, Days 3-5)

4. **Stay Updated**
   - Follow the 9-week implementation roadmap
   - Phase 1 target: 3 weeks (Core functionality)
   - Phase 2 target: 3 weeks (LLM + RAG)
   - Phase 3 target: 3 weeks (UI + Deployment)

## Support

- **Documentation**: See `docs/` directory
- **Issues**: Open GitHub issues for bugs/features
- **Architecture Questions**: See [ARCHITECTURE.md](docs/ARCHITECTURE.md)
- **Implementation Details**: See [IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md)

## License

[Add your license here]

---

**Status**: Phase 1, Week 1 Complete ✅  
**Next Milestone**: Database clients (ChEMBL, BindingDB) - Week 1, Days 3-5
