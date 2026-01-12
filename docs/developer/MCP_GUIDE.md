# Model Context Protocol (MCP) - Complete Guide for ChemAgent

**Date**: January 12, 2026  
**Author**: Sanjeeva Reddy Dodlapati  
**Status**: Educational Reference

---

## Table of Contents

1. [What is MCP?](#1-what-is-mcp)
2. [Why Does MCP Exist?](#2-why-does-mcp-exist)
3. [How MCP Works](#3-how-mcp-works)
4. [MCP Architecture](#4-mcp-architecture)
5. [Key Concepts](#5-key-concepts)
6. [Real-World Examples](#6-real-world-examples)
7. [How MCP Benefits ChemAgent](#7-how-mcp-benefits-chemagent)
8. [Implementation Options](#8-implementation-options)
9. [Step-by-Step Implementation Guide](#9-step-by-step-implementation-guide)
10. [Comparison: With vs Without MCP](#10-comparison-with-vs-without-mcp)
11. [Decision Framework](#11-decision-framework)

---

## 1. What is MCP?

### Simple Definition

**Model Context Protocol (MCP)** is an open standard created by Anthropic that allows AI assistants (like Claude) to connect to external tools, data sources, and services in a standardized way.

Think of it like **USB for AI** - just as USB provides a universal way to connect any device to any computer, MCP provides a universal way to connect any data source to any AI assistant.

### Official Definition

> MCP is an open protocol that standardizes how applications provide context to LLMs. Think of MCP like a USB-C port for AI applications. Just as USB-C provides a standardized way to connect your devices to various peripherals and accessories, MCP provides a standardized way to connect AI models to different data sources and tools.
> — Anthropic

### Key Characteristics

| Aspect | Description |
|--------|-------------|
| **Open Standard** | Free to use, not proprietary |
| **Language Agnostic** | Works with Python, TypeScript, etc. |
| **Bidirectional** | Both client and server can initiate communication |
| **Stateful** | Maintains context across interactions |
| **Secure** | Built-in security model for permissions |

---

## 2. Why Does MCP Exist?

### The Problem Before MCP

Before MCP, connecting AI to external tools was fragmented:

```
┌─────────────┐     Custom Integration      ┌─────────────┐
│   Claude    │ ─────────────────────────── │  Database   │
└─────────────┘                             └─────────────┘
       │
       │        Different Integration       ┌─────────────┐
       └─────────────────────────────────── │   GitHub    │
                                            └─────────────┘
       │
       │        Another Integration         ┌─────────────┐
       └─────────────────────────────────── │  Your API   │
                                            └─────────────┘

Problem: Every integration is custom, different, and incompatible
```

### The Solution with MCP

```
┌─────────────┐                             ┌─────────────┐
│   Claude    │                             │  Database   │
├─────────────┤     ┌─────────────────┐     ├─────────────┤
│  MCP Client │ ─── │  MCP Protocol   │ ─── │ MCP Server  │
└─────────────┘     └─────────────────┘     └─────────────┘
                            │
                            │               ┌─────────────┐
                            │               │   GitHub    │
                            │               ├─────────────┤
                            └────────────── │ MCP Server  │
                                            └─────────────┘
                            │
                            │               ┌─────────────┐
                            │               │ ChemAgent   │
                            │               ├─────────────┤
                            └────────────── │ MCP Server  │
                                            └─────────────┘

Solution: One protocol, many integrations
```

### Benefits

1. **Write Once, Use Everywhere**: Build one MCP server, use it with Claude, VS Code, and future AI tools
2. **Standardized Interface**: All tools follow the same patterns
3. **Community Ecosystem**: Reuse existing MCP servers built by others
4. **Future-Proof**: As new AI assistants adopt MCP, your integration works automatically

---

## 3. How MCP Works

### Communication Flow

```
┌─────────────────────────────────────────────────────────────┐
│                      MCP Host                                │
│  (Claude Desktop, VS Code, IDE, Custom App)                 │
│                                                              │
│   ┌──────────────┐                                          │
│   │  MCP Client  │ ◄──── Manages connection to servers      │
│   └──────┬───────┘                                          │
└──────────┼──────────────────────────────────────────────────┘
           │
           │  JSON-RPC over stdio/SSE/WebSocket
           │
           ▼
┌──────────────────────────────────────────────────────────────┐
│                      MCP Server                               │
│  (Your Application - e.g., ChemAgent)                        │
│                                                               │
│   ┌────────────┐  ┌────────────┐  ┌────────────┐            │
│   │ Resources  │  │   Tools    │  │  Prompts   │            │
│   │ (Data)     │  │ (Actions)  │  │ (Templates)│            │
│   └────────────┘  └────────────┘  └────────────┘            │
│         │               │               │                    │
│         ▼               ▼               ▼                    │
│   ┌─────────────────────────────────────────────────────┐   │
│   │              Your Application Logic                  │   │
│   │              (ChemAgent Core)                        │   │
│   └─────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

### Message Types (JSON-RPC)

MCP uses JSON-RPC 2.0 for communication:

```json
// Client → Server: Request
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "chemagent_query",
    "arguments": {
      "query": "What is aspirin?"
    }
  }
}

// Server → Client: Response
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "Aspirin (CHEMBL25) is an anti-inflammatory drug..."
      }
    ]
  }
}
```

---

## 4. MCP Architecture

### Components

#### 1. MCP Host
The application that wants to use AI capabilities:
- Claude Desktop app
- VS Code with GitHub Copilot
- Your custom application
- IDE plugins

#### 2. MCP Client
Built into the host, manages:
- Server discovery
- Connection lifecycle
- Message routing
- Permission handling

#### 3. MCP Server
Your application exposing capabilities:
- **Resources**: Data the AI can read
- **Tools**: Actions the AI can perform
- **Prompts**: Pre-built conversation templates

### Transport Layers

| Transport | Use Case | Example |
|-----------|----------|---------|
| **stdio** | Local processes | Claude Desktop → Local MCP server |
| **HTTP/SSE** | Remote servers | Web app → Cloud API |
| **WebSocket** | Real-time bidirectional | Chat applications |

---

## 5. Key Concepts

### 5.1 Resources

**Resources** are data that the AI can read. Think of them as "files" or "documents" the AI can access.

```python
# Example: Compound resource
@server.resource("compound://{chembl_id}")
async def get_compound(chembl_id: str) -> Resource:
    """Get compound data from ChEMBL"""
    compound = chembl_client.get_compound(chembl_id)
    return Resource(
        uri=f"compound://{chembl_id}",
        name=f"Compound {chembl_id}",
        mimeType="application/json",
        text=json.dumps(compound)
    )
```

**Use cases for ChemAgent**:
- `compound://CHEMBL25` → Aspirin data
- `target://P00734` → Thrombin protein info
- `result://query_abc123` → Cached query result

### 5.2 Tools

**Tools** are actions the AI can perform. They have defined inputs and outputs.

```python
# Example: Query tool
@server.tool()
async def chemagent_query(query: str, verbose: bool = False) -> str:
    """
    Execute a natural language chemistry query.
    
    Args:
        query: The chemistry question to answer
        verbose: Include detailed execution info
    
    Returns:
        Answer with provenance information
    """
    agent = ChemAgent()
    result = agent.query(query)
    return result.answer
```

**Use cases for ChemAgent**:
- `chemagent_query` → Natural language queries
- `chemagent_similarity` → Find similar compounds
- `chemagent_properties` → Calculate molecular properties
- `chemagent_activity` → Get bioactivity data

### 5.3 Prompts

**Prompts** are pre-built conversation templates that guide AI behavior.

```python
# Example: Expert prompt
@server.prompt()
async def drug_discovery_expert() -> Prompt:
    """Expert mode for drug discovery questions"""
    return Prompt(
        name="drug_discovery_expert",
        description="Expert pharmaceutical researcher mode",
        messages=[
            {
                "role": "system",
                "content": """You are an expert pharmaceutical researcher 
                with access to ChemAgent tools. For each query:
                1. Search for relevant compounds
                2. Calculate key properties
                3. Check drug-likeness
                4. Cite all sources"""
            }
        ]
    )
```

**Use cases for ChemAgent**:
- Drug discovery workflow prompt
- ADMET analysis prompt
- Literature review prompt

### 5.4 Sampling (Advanced)

**Sampling** allows the server to request LLM completions from the client.

```python
# Server asks client to generate text
result = await server.request_sampling(
    messages=[
        {"role": "user", "content": "Summarize this compound data..."}
    ],
    max_tokens=500
)
```

---

## 6. Real-World Examples

### 6.1 Claude Desktop + Filesystem

```
User: "Read the contents of /project/data.csv and analyze it"

Claude Desktop (MCP Client)
    │
    ├─── MCP Request: resources/read
    │    uri: "file:///project/data.csv"
    │
    ▼
Filesystem MCP Server
    │
    ├─── Reads file from disk
    │
    ▼
Returns file contents to Claude
    │
    ▼
Claude analyzes and responds
```

### 6.2 VS Code + GitHub

```
User: "Create a PR with my current changes"

VS Code (MCP Client)
    │
    ├─── MCP Request: tools/call
    │    name: "create_pull_request"
    │    args: {title: "...", body: "..."}
    │
    ▼
GitHub MCP Server
    │
    ├─── GitHub API call
    │
    ▼
Returns PR URL to VS Code
```

### 6.3 Claude + ChemAgent (What We'd Build)

```
User: "Find compounds similar to aspirin that might be safer for stomach"

Claude Desktop (MCP Client)
    │
    ├─── MCP Request: tools/call
    │    name: "chemagent_query"
    │    args: {query: "Find compounds similar to aspirin..."}
    │
    ▼
ChemAgent MCP Server
    │
    ├─── IntentParser → QueryPlanner → Executor
    ├─── ChEMBL API calls
    ├─── Property calculations
    │
    ▼
Returns structured answer with sources
    │
    ▼
Claude formats and presents to user
```

---

## 7. How MCP Benefits ChemAgent

### 7.1 Direct Benefits

| Benefit | Description | Impact |
|---------|-------------|--------|
| **Claude Integration** | Use ChemAgent directly in Claude Desktop | Users can ask chemistry questions in Claude |
| **VS Code Integration** | Access ChemAgent while coding | Researchers get inline chemistry help |
| **Multi-Client Support** | One server, many clients | Build once, deploy everywhere |
| **Context Sharing** | AI remembers compound context | "Now compare it to ibuprofen" works |

### 7.2 Use Case Scenarios

#### Scenario 1: Researcher in Claude Desktop

```
Researcher: "I'm working on COX-2 inhibitors. What's the structure 
            of celecoxib and how does it compare to rofecoxib?"

Claude (with ChemAgent MCP):
├── Calls chemagent_query("structure of celecoxib")
├── Calls chemagent_query("compare celecoxib and rofecoxib")
├── Synthesizes results with Claude's reasoning
└── Provides comprehensive answer with sources
```

#### Scenario 2: Developer in VS Code

```
Developer writing code:
"""
# TODO: Get the SMILES for aspirin and calculate LogP
smiles = ???
"""

GitHub Copilot (with ChemAgent MCP):
├── Detects chemistry context
├── Calls chemagent_query("SMILES for aspirin")
├── Calls chemagent_properties(smiles)
└── Suggests: smiles = "CC(=O)Oc1ccccc1C(=O)O"  # LogP: 1.31
```

#### Scenario 3: Automated Pipeline

```python
# Your script using MCP client
async with MCPClient("chemagent-server") as client:
    compounds = ["aspirin", "ibuprofen", "naproxen"]
    
    for compound in compounds:
        result = await client.call_tool(
            "chemagent_properties",
            {"compound": compound}
        )
        print(f"{compound}: {result}")
```

### 7.3 What ChemAgent Would Expose via MCP

#### Resources (Data Access)
```
compound://CHEMBL25        → Aspirin compound data
target://P00734           → Thrombin target info
activity://CHEMBL25/P00734 → Activity data
plan://abc123             → Saved query plan
result://xyz789           → Cached query result
```

#### Tools (Actions)
```
chemagent_query           → Natural language queries
chemagent_search          → Search compounds/targets
chemagent_properties      → Calculate properties
chemagent_similarity      → Similarity search
chemagent_activity        → Get bioactivity data
chemagent_lipinski        → Drug-likeness check
chemagent_compare         → Compare compounds
chemagent_export          → Export to BibTeX/RIS
```

#### Prompts (Templates)
```
drug_discovery_expert     → Expert researcher mode
admet_analysis           → ADMET property focus
literature_review        → Citation-heavy responses
batch_analysis           → Process multiple compounds
```

---

## 8. Implementation Options

### Option A: Full MCP Server (Recommended)

Create a complete MCP server that exposes all ChemAgent capabilities.

**Pros**:
- Full feature access
- Works with any MCP client
- Future-proof

**Cons**:
- More development time
- Need to maintain MCP layer

**Effort**: 2-3 weeks

### Option B: Minimal MCP Wrapper

Expose only the main query endpoint.

**Pros**:
- Quick to implement
- Simple to maintain

**Cons**:
- Limited functionality
- Less useful for complex workflows

**Effort**: 3-5 days

### Option C: No MCP (Continue as-is)

Keep using REST API only.

**Pros**:
- No new development
- Works today

**Cons**:
- No Claude/VS Code integration
- Manual API calls required
- Miss ecosystem benefits

**Effort**: 0

### Recommendation

**Start with Option B** (minimal wrapper), then expand to **Option A** based on usage.

---

## 9. Step-by-Step Implementation Guide

### Step 1: Install MCP SDK

```bash
pip install mcp
```

### Step 2: Create Basic Server Structure

```python
# src/chemagent/mcp/__init__.py
"""MCP Server for ChemAgent"""

# src/chemagent/mcp/server.py
from mcp.server import Server
from mcp.types import Resource, Tool, TextContent

# Create server instance
server = Server("chemagent")

@server.tool()
async def chemagent_query(query: str) -> list[TextContent]:
    """Execute a chemistry query using ChemAgent."""
    from chemagent import ChemAgent
    
    agent = ChemAgent()
    result = agent.query(query)
    
    return [TextContent(
        type="text",
        text=result.answer
    )]

@server.resource("compound://{chembl_id}")
async def get_compound(chembl_id: str) -> Resource:
    """Get compound data by ChEMBL ID."""
    from chemagent.tools.chembl_client import ChEMBLClient
    
    client = ChEMBLClient()
    compound = client.get_compound(chembl_id)
    
    return Resource(
        uri=f"compound://{chembl_id}",
        name=compound.get("pref_name", chembl_id),
        mimeType="application/json",
        text=json.dumps(compound, indent=2)
    )

# Entry point
async def main():
    from mcp.server.stdio import stdio_server
    async with stdio_server() as (read, write):
        await server.run(read, write)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

### Step 3: Configure for Claude Desktop

Create config file (`~/.config/claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "chemagent": {
      "command": "python",
      "args": ["-m", "chemagent.mcp.server"],
      "env": {
        "CHEMAGENT_CACHE_DIR": "/path/to/cache"
      }
    }
  }
}
```

### Step 4: Test the Integration

```
1. Restart Claude Desktop
2. Look for ChemAgent in available tools
3. Ask: "Using ChemAgent, what is the molecular weight of aspirin?"
4. Claude will call chemagent_query and return the answer
```

---

## 10. Comparison: With vs Without MCP

### Without MCP (Current State)

```
User wants to ask about aspirin properties:

1. Open browser
2. Navigate to ChemAgent API/UI
3. Type query
4. Copy result
5. Paste into their document/Claude chat

Or programmatically:

import requests
response = requests.post(
    "http://localhost:8000/query",
    json={"query": "What is aspirin?"}
)
print(response.json()["answer"])
```

### With MCP

```
User in Claude Desktop:

"What are the properties of aspirin and how does it compare 
to ibuprofen for COX selectivity?"

Claude automatically:
├── Calls chemagent_query for aspirin
├── Calls chemagent_query for ibuprofen  
├── Calls chemagent_compare
├── Synthesizes with Claude's reasoning
└── Provides comprehensive answer

No copy-paste, no context switching, no API calls to write.
```

### Feature Comparison

| Feature | REST API | MCP |
|---------|----------|-----|
| Claude Desktop integration | ❌ Manual | ✅ Native |
| VS Code integration | ❌ Manual | ✅ Native |
| Context retention | ❌ Stateless | ✅ Stateful |
| Multi-step workflows | ❌ Manual | ✅ Automatic |
| Permission handling | ❌ Custom | ✅ Built-in |
| Future AI tool support | ❌ Each separate | ✅ Automatic |

---

## 11. Decision Framework

### Should ChemAgent Implement MCP?

#### Answer: **Yes, but strategically**

### When to Implement

| Scenario | Recommendation |
|----------|----------------|
| Want Claude Desktop users | ✅ Implement now |
| Target VS Code developers | ✅ Implement now |
| Only REST API users | ⏳ Can wait |
| Building AI-powered pipelines | ✅ Implement now |

### Recommended Approach

```
Phase 1 (Week 1): Minimal MCP
├── Single tool: chemagent_query
├── Test with Claude Desktop
└── Gather feedback

Phase 2 (Week 2-3): Full MCP
├── All tools exposed
├── Resources for compounds/targets
├── Prompts for workflows
└── Documentation
```

### Success Criteria

| Metric | Target |
|--------|--------|
| Claude Desktop working | ✅ Can query ChemAgent |
| Response time | < 5 seconds |
| All query types work | 100% of existing intents |
| Documentation complete | User guide published |

---

## 📚 References

1. **Official MCP Documentation**: https://modelcontextprotocol.io/
2. **MCP GitHub Repository**: https://github.com/modelcontextprotocol
3. **MCP Python SDK**: https://github.com/modelcontextprotocol/python-sdk
4. **Anthropic MCP Announcement**: https://www.anthropic.com/news/model-context-protocol
5. **Example MCP Servers**: https://github.com/modelcontextprotocol/servers

---

## 🎯 Summary

**MCP is:**
- A standardized protocol for AI-tool integration
- Like "USB for AI applications"
- Created by Anthropic, but open standard

**For ChemAgent, MCP would:**
- Enable direct Claude Desktop integration
- Allow VS Code chemistry assistance
- Future-proof for new AI tools
- Reduce friction for researchers

**Next Steps:**
1. Review this document
2. Decide on implementation scope
3. Start with minimal MCP server
4. Expand based on user feedback

---

*Questions? The MCP ecosystem is growing rapidly. This document will be updated as new capabilities emerge.*
