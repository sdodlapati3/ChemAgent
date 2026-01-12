# Multi-Agent Orchestration Architecture

## Overview

ChemAgent now supports a multi-agent orchestration system where a **Coordinator Agent** (powered by a large orchestration model) delegates tasks to specialized agents for handling complex pharmaceutical research queries.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    USER QUERY                                   │
└─────────────────────────────────┬───────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│               COORDINATOR AGENT (Nemotron/Groq-70B)             │
│                                                                 │
│  • Analyzes query intent                                        │
│  • Decomposes into sub-tasks                                    │
│  • Routes to specialists                                        │
│  • Handles dependencies                                         │
│  • Synthesizes final response                                   │
└───────┬──────────┬──────────┬──────────┬────────────────────────┘
        │          │          │          │
        ▼          ▼          ▼          ▼
┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐
│ COMPOUND  │ │ ACTIVITY  │ │ PROPERTY  │ │  TARGET   │
│   AGENT   │ │   AGENT   │ │   AGENT   │ │   AGENT   │
│           │ │           │ │           │ │           │
│ • Search  │ │ • IC50    │ │ • Lipinski│ │ • UniProt │
│ • Lookup  │ │ • Ki      │ │ • LogP    │ │ • Targets │
│ • Similar │ │ • Targets │ │ • MW      │ │ • Proteins│
└───────────┘ └───────────┘ └───────────┘ └───────────┘
        │          │          │          │
        ▼          ▼          ▼          ▼
┌─────────────────────────────────────────────────────────────────┐
│                         TOOL REGISTRY                           │
│  chembl_search | chembl_get_activities | rdkit_calculate | ...  │
└─────────────────────────────────────────────────────────────────┘
```

## Agent Roles

### Coordinator Agent
- **Model**: `groq/llama-3.3-70b-versatile` (with Nemotron planned)
- **Role**: Orchestration, task decomposition, result synthesis
- **Capabilities**:
  - Analyzes complex queries
  - Plans multi-step execution
  - Routes to appropriate specialists
  - Handles task dependencies
  - Synthesizes coherent responses

### CompoundAgent (compound_specialist)
- **Model**: `groq/llama-3.1-8b-instant`
- **Role**: Chemical compound expert
- **Tools**:
  - `chembl_search_by_name` - Search compounds
  - `chembl_get_compound` - Lookup by ID
  - `chembl_similarity_search` - Find similar compounds

### ActivityAgent (activity_specialist)
- **Model**: `groq/llama-3.1-8b-instant`  
- **Role**: Bioactivity data expert
- **Tools**:
  - `chembl_get_activities` - IC50, Ki, EC50 data
  - `chembl_get_targets` - Target interactions

### PropertyAgent (property_specialist)
- **Model**: `groq/llama-3.1-8b-instant`
- **Role**: Molecular properties expert
- **Tools**:
  - `rdkit_calculate_properties` - Calculate all properties
  - `rdkit_check_lipinski` - Lipinski Rule of Five

### TargetAgent (target_specialist)
- **Model**: `groq/llama-3.1-8b-instant`
- **Role**: Drug targets expert
- **Tools**:
  - `uniprot_get_protein` - Protein details
  - `uniprot_search` - Search proteins

## Usage

### Enable Multi-Agent Mode

```bash
export CHEMAGENT_USE_MULTI_AGENT=true
./scripts/server.sh restart 8000
```

### API Endpoint

```bash
# Multi-agent query
curl -X POST http://localhost:8000/query/multi-agent \
  -H "Content-Type: application/json" \
  -d '{"query": "Find targets and activities of ibuprofen", "verbose": true}'
```

### Response Format

```json
{
  "success": true,
  "query": "Find targets and activities of ibuprofen",
  "answer": "### Ibuprofen Overview...",
  "orchestration_type": "multi_agent",
  "tasks_executed": 2,
  "agents_used": ["compound_specialist", "activity_specialist"],
  "execution_time_ms": 4222.57,
  "details": {
    "coordinator_stats": {
      "total_queries": 2,
      "tasks_delegated": 3,
      "successful_orchestrations": 2,
      "specialists": {...}
    }
  }
}
```

### Python API

```python
from chemagent.core.executor import ToolRegistry
from chemagent.core.multi_agent import create_multi_agent_system

# Create system
registry = ToolRegistry(use_real_tools=True)
coordinator = create_multi_agent_system(tool_registry=registry)

# Process query
result = coordinator.process("What are the targets of aspirin?")

print(f"Success: {result['success']}")
print(f"Agents used: {result['agents_used']}")
print(f"Answer: {result['answer']}")
```

## Model Configuration

The system uses different models for different roles:

| Agent | Model | Purpose |
|-------|-------|---------|
| Coordinator | `groq/llama-3.3-70b-versatile` | Complex reasoning, orchestration |
| Specialists | `groq/llama-3.1-8b-instant` | Fast, focused responses |

### Future: NVIDIA Nemotron

NVIDIA Nemotron models are specifically trained for tool calling and agentic workflows:
- `nvidia/llama-3.3-nemotron-super-49b-v1.5` (NVIDIA API)
- `nvidia/NVIDIA-Nemotron-Nano-9B-v2` (Together.ai)

To use Nemotron as coordinator (when configured):
```python
from chemagent.core.multi_agent import ModelConfig

# Configure for Nemotron (requires NVIDIA API key)
ModelConfig.COORDINATOR_MODEL = "nvidia/llama-3.3-nemotron-super-49b-v1"
```

## Query Routing Logic

The Coordinator uses LLM reasoning to determine which agents to use:

| Query Type | Agents Involved |
|------------|-----------------|
| "What is aspirin?" | CompoundAgent |
| "Find IC50 for CHEMBL25" | CompoundAgent → ActivityAgent |
| "Calculate LogP of..." | PropertyAgent |
| "What targets does X hit?" | CompoundAgent → ActivityAgent |
| "Find COX-2 inhibitors" | TargetAgent → ActivityAgent → CompoundAgent |

## Task Dependencies

The coordinator handles task dependencies automatically:

```
Query: "Find similar compounds to aspirin and compare their IC50"

Task 1: CompoundAgent - Look up aspirin          [no dependencies]
Task 2: CompoundAgent - Find similar compounds   [depends on Task 1]
Task 3: ActivityAgent - Get IC50 for compounds   [depends on Task 2]
```

## Comparison: OptimalAgent vs Multi-Agent

| Feature | OptimalAgent | Multi-Agent |
|---------|--------------|-------------|
| Speed | Faster (single agent) | Slower (multiple LLM calls) |
| Complex queries | Limited | Excellent |
| Reasoning depth | Good | Better |
| Cost | Lower | Higher (more API calls) |
| Best for | Simple queries | Complex multi-step queries |

## Files

- `src/chemagent/core/multi_agent.py` - Multi-agent implementation
- `examples/multi_agent_demo.py` - Demo script
- `docs/MULTI_AGENT_GUIDE.md` - This documentation

## Status

✅ **Implemented**:
- Coordinator Agent
- 4 Specialist Agents
- Task decomposition & routing
- Result synthesis
- API endpoint `/query/multi-agent`

⏳ **Planned**:
- Switch to NVIDIA Nemotron
- Parallel specialist execution
- Agent memory/learning
- CrewAI integration (Phase 7)
