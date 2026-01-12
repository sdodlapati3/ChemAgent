# ChemAgent Roadmap v2.0

**Date**: January 12, 2026  
**Version**: 1.0.0 (Released)  
**Status**: Production Ready → Planning Next Phase  
**Author**: Sanjeeva Reddy Dodlapati

---

## 🎯 Executive Summary

ChemAgent v1.0.0 has been released with all core features complete:
- ✅ 290 tests passing, 96.2% query success rate
- ✅ 26 integrated tools across 6 databases
- ✅ Hybrid LLM router with Groq/Gemini fallback
- ✅ Query persistence and export functionality
- ✅ Verifier gate for hallucination prevention

This roadmap outlines **future enhancements** organized into strategic phases.

---

## 📊 Current State (v1.0.0)

### Completed Phases
| Phase | Description | Status |
|-------|-------------|--------|
| A | Foundation (OptimalAgent, Tools, Parser) | ✅ Complete |
| B | Provenance Layer (Evidence, Open Targets) | ✅ Complete |
| C | Evaluation Harness (Assertions, Task Suite) | ✅ Complete |
| D | Verifier Gate (Claims, Hallucination Prevention) | ✅ Complete |
| E | Polish (LLM Router, Persistence, Export) | ✅ Complete |

### Key Metrics
- **Query Success Rate**: 96.2% (460/478 queries)
- **Test Coverage**: 92% (290/292 tests)
- **Average Query Time**: 312ms
- **Database Coverage**: 6 sources, 26 tools

---

## 🔮 Future Phases

### Phase F: Model Context Protocol (MCP) Integration
**Timeline**: 2-3 weeks  
**Priority**: High  
**Goal**: Enable ChemAgent as an MCP server for integration with Claude, VS Code, and other AI systems

#### F.1 MCP Server Implementation
```
ChemAgent as MCP Server
    ↓
┌─────────────────────────────────────────┐
│         MCP Protocol Layer              │
├─────────────────────────────────────────┤
│  Resources    │  Tools      │  Prompts  │
│  - compounds  │  - search   │  - query  │
│  - targets    │  - analyze  │  - batch  │
│  - results    │  - compare  │  - expert │
└─────────────────────────────────────────┘
    ↓
Claude Desktop / VS Code / Other MCP Clients
```

#### Tasks
- [ ] **F.1.1**: Create MCP server wrapper (`src/chemagent/mcp/server.py`)
- [ ] **F.1.2**: Define MCP resources (compounds, targets, query results)
- [ ] **F.1.3**: Expose tools via MCP protocol
- [ ] **F.1.4**: Create MCP prompts for common workflows
- [ ] **F.1.5**: Integration tests with Claude Desktop
- [ ] **F.1.6**: Documentation for MCP setup

#### MCP Resources
| Resource | URI Pattern | Description |
|----------|-------------|-------------|
| Compound | `compound://{chembl_id}` | Compound data from ChEMBL |
| Target | `target://{uniprot_id}` | Protein target information |
| Result | `result://{query_id}` | Cached query results |
| Plan | `plan://{plan_id}` | Saved query plans |

#### MCP Tools
| Tool | Description | Parameters |
|------|-------------|------------|
| `chemagent_query` | Natural language query | query, verbose |
| `chemagent_search` | Compound/target search | entity, type |
| `chemagent_properties` | Calculate properties | smiles |
| `chemagent_similarity` | Similarity search | smiles, threshold |
| `chemagent_activity` | Bioactivity lookup | compound_id |

---

### Phase G: Literature & RAG Integration
**Timeline**: 3-4 weeks  
**Priority**: High  
**Goal**: Ground responses in scientific literature

#### G.1 PubMed Integration
- [ ] PubMed API client with caching
- [ ] Citation extraction from responses
- [ ] Paper summary generation
- [ ] Link compounds to publications

#### G.2 RAG Pipeline
```
Query → Vector Search → Context Retrieval → LLM + Context → Response
              ↓
    ┌─────────────────┐
    │  Vector Store   │
    │  - PubMed       │
    │  - ChEMBL docs  │
    │  - Drug labels  │
    └─────────────────┘
```

- [ ] ChromaDB or Pinecone vector store
- [ ] Embedding pipeline for literature
- [ ] Context injection into LLM prompts
- [ ] Source citation in responses

---

### Phase H: Advanced Drug Discovery Features
**Timeline**: 4-6 weeks  
**Priority**: High  
**Goal**: Add critical drug discovery capabilities

#### H.1 ADMET Predictions
- [ ] Absorption prediction models
- [ ] Distribution modeling
- [ ] Metabolism prediction
- [ ] Excretion modeling
- [ ] Toxicity alerts (Brenk, PAINS)

#### H.2 DrugBank Integration
- [ ] Drug interaction lookup
- [ ] Indication/contraindication data
- [ ] FDA approval status
- [ ] Drug-target relationships

#### H.3 Molecular Docking (Optional)
- [ ] AutoDock Vina integration
- [ ] Binding affinity predictions
- [ ] Docking visualization

---

### Phase I: Production Hardening
**Timeline**: 2-3 weeks  
**Priority**: Medium  
**Goal**: Enterprise-ready deployment

#### I.1 Monitoring & Observability
- [ ] Prometheus metrics endpoint
- [ ] Grafana dashboard templates
- [ ] Structured logging (JSON)
- [ ] Distributed tracing (OpenTelemetry)

#### I.2 Security & Rate Limiting
- [ ] API key authentication
- [ ] Per-user rate limiting
- [ ] Input sanitization
- [ ] Audit logging

#### I.3 Scalability
- [ ] Redis for distributed caching
- [ ] Connection pooling
- [ ] Horizontal scaling guide
- [ ] Load testing results

---

### Phase J: User Experience Enhancements
**Timeline**: 2-3 weeks  
**Priority**: Medium  
**Goal**: Improved researcher workflow

#### J.1 Batch Processing
- [ ] Batch query API endpoint
- [ ] Progress tracking for batches
- [ ] CSV/Excel import/export
- [ ] Result aggregation

#### J.2 Interactive Features
- [ ] Query history in web UI
- [ ] Saved query templates
- [ ] Collaborative workspaces
- [ ] Annotation support

#### J.3 Visualization
- [ ] Molecule structure rendering
- [ ] Interactive data tables
- [ ] Chart generation for activities
- [ ] Network visualization for targets

---

### Phase K: Multi-Agent Orchestration
**Timeline**: 4-6 weeks  
**Priority**: Low (Future)  
**Goal**: Specialized agents for complex workflows

#### Architecture Vision
```
                    Coordinator Agent
                          ↓
        ┌─────────────────┼─────────────────┐
        ↓                 ↓                 ↓
  CompoundAgent      TargetAgent      LiteratureAgent
        ↓                 ↓                 ↓
   ChEMBL/PubChem    UniProt/OT         PubMed/RAG
```

#### Tasks
- [ ] Agent abstraction layer
- [ ] Inter-agent communication protocol
- [ ] Task decomposition and routing
- [ ] Result synthesis from multiple agents
- [ ] CrewAI or AutoGen integration (optional)

---

## 📅 Implementation Timeline

```
Q1 2026 (Jan-Mar)
├── Phase F: MCP Integration (High Priority)
│   └── Weeks 1-3: MCP server, resources, tools
│
├── Phase G: RAG Integration (High Priority)
│   └── Weeks 4-7: PubMed, vector store, citations
│
└── Phase H.1: ADMET Predictions (Start)
    └── Weeks 8-10: Toxicity alerts, basic predictions

Q2 2026 (Apr-Jun)
├── Phase H: Drug Discovery Features (Complete)
│   └── Weeks 11-16: DrugBank, full ADMET
│
├── Phase I: Production Hardening
│   └── Weeks 17-19: Monitoring, security
│
└── Phase J: UX Enhancements
    └── Weeks 20-22: Batch, visualization

Q3 2026 (Jul-Sep)
└── Phase K: Multi-Agent (If needed)
    └── Weeks 23-28: Agent orchestration
```

---

## 🎯 Priority Matrix

| Phase | Impact | Effort | Priority |
|-------|--------|--------|----------|
| **F: MCP** | High | Medium | 🔴 P1 |
| **G: RAG** | High | High | 🔴 P1 |
| **H: ADMET** | High | High | 🔴 P1 |
| **I: Production** | Medium | Medium | 🟡 P2 |
| **J: UX** | Medium | Low | 🟡 P2 |
| **K: Multi-Agent** | Low | High | 🟢 P3 |

---

## 🛠️ Technical Requirements

### Phase F (MCP)
```
Dependencies:
- mcp-server-python (Anthropic MCP SDK)
- uvicorn (async server)

New Files:
- src/chemagent/mcp/__init__.py
- src/chemagent/mcp/server.py
- src/chemagent/mcp/resources.py
- src/chemagent/mcp/tools.py
- src/chemagent/mcp/prompts.py
```

### Phase G (RAG)
```
Dependencies:
- chromadb or pinecone-client
- sentence-transformers
- biopython (PubMed)

New Files:
- src/chemagent/rag/__init__.py
- src/chemagent/rag/embeddings.py
- src/chemagent/rag/retriever.py
- src/chemagent/tools/pubmed_client.py
```

### Phase H (ADMET)
```
Dependencies:
- rdkit (already installed)
- chembl_structure_pipeline (optional)

New Files:
- src/chemagent/tools/admet.py
- src/chemagent/tools/drugbank_client.py
```

---

## 📈 Success Metrics

| Phase | Metric | Target |
|-------|--------|--------|
| F | MCP clients connected | 3+ (Claude, VS Code, etc.) |
| G | Citation coverage | 80% of responses |
| H | ADMET accuracy | 85%+ vs experimental |
| I | API uptime | 99.9% |
| J | User satisfaction | 4.5/5 rating |

---

## 🔗 Related Documents

- [Architecture](developer/ARCHITECTURE.md) - Current system design
- [Multi-Agent Strategy](developer/MULTI_AGENT_ARCHITECTURE.md) - Future agent design
- [API Documentation](user-guide/API_DOCUMENTATION.md) - REST API reference
- [Archived: Future Enhancements v1](archive/planning/FUTURE_ENHANCEMENTS_PLAN_v1.md) - Previous roadmap

---

## 📝 Change Log

| Date | Version | Changes |
|------|---------|---------|
| 2026-01-12 | 2.0 | Complete rewrite with MCP focus |
| 2026-01-11 | 1.0 | Initial enhancement plan |

---

**Next Steps**: Begin Phase F (MCP Integration) - Create MCP server wrapper
