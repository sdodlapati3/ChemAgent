"""
MCP Server implementation for ChemAgent.

This server exposes ChemAgent functionality via the Model Context Protocol,
allowing AI assistants like Claude to directly access chemistry tools.

Architecture:
    MCP Client (Claude/VS Code)
           │
           ▼
    ┌──────────────────┐
    │  MCP Server      │  ◄── This module
    │  (Protocol Layer)│
    └────────┬─────────┘
             │
             ▼
    ┌──────────────────┐
    │  ChemAgent Core  │  ◄── Existing system (unchanged)
    │  (Business Logic)│
    └──────────────────┘
             │
             ▼
    ChEMBL, PubChem, UniProt, etc.
"""

import json
import logging
from typing import Any, Optional

# MCP imports
from mcp.server import Server
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    Prompt,
    PromptMessage,
    GetPromptResult,
)
from mcp.server.stdio import stdio_server

# ChemAgent imports
from chemagent import ChemAgent
from chemagent.core import IntentParser, QueryPlanner

logger = logging.getLogger(__name__)

# =============================================================================
# MCP Server Instance
# =============================================================================

def create_mcp_server() -> Server:
    """
    Create and configure the MCP server with all ChemAgent tools.
    
    Returns:
        Configured MCP Server instance
    """
    server = Server("chemagent")
    
    # Lazy-loaded ChemAgent instance (created on first use)
    _agent: Optional[ChemAgent] = None
    
    def get_agent() -> ChemAgent:
        """Get or create the ChemAgent instance."""
        nonlocal _agent
        if _agent is None:
            _agent = ChemAgent()
            logger.info("ChemAgent instance created for MCP server")
        return _agent
    
    # =========================================================================
    # TOOLS - Actions the AI can perform
    # =========================================================================
    
    @server.list_tools()
    async def list_tools() -> list[Tool]:
        """List all available ChemAgent tools."""
        return [
            Tool(
                name="chemagent_query",
                description="""Execute a natural language chemistry query.
                
Supports queries like:
- "What is aspirin?" (compound lookup)
- "Calculate properties of CC(=O)Oc1ccccc1C(=O)O" (property calculation)
- "Find compounds similar to CHEMBL25" (similarity search)
- "Is metformin drug-like?" (Lipinski check)
- "What is the IC50 of atorvastatin?" (activity lookup)
- "What targets are associated with breast cancer?" (disease-target)

Returns structured answer with sources and provenance.""",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Natural language chemistry question"
                        },
                        "verbose": {
                            "type": "boolean",
                            "description": "Include detailed execution info",
                            "default": False
                        }
                    },
                    "required": ["query"]
                }
            ),
            Tool(
                name="chemagent_properties",
                description="""Calculate molecular properties for a SMILES string.
                
Returns:
- Molecular weight
- LogP (lipophilicity)
- H-bond donors/acceptors
- Polar surface area
- Rotatable bonds
- And more...""",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "smiles": {
                            "type": "string",
                            "description": "SMILES string of the molecule"
                        }
                    },
                    "required": ["smiles"]
                }
            ),
            Tool(
                name="chemagent_similarity",
                description="""Find compounds similar to a given SMILES structure.
                
Uses Tanimoto similarity on Morgan fingerprints.
Returns similar compounds from ChEMBL database.""",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "smiles": {
                            "type": "string",
                            "description": "SMILES string to search similar compounds"
                        },
                        "threshold": {
                            "type": "number",
                            "description": "Similarity threshold (0-1)",
                            "default": 0.7,
                            "minimum": 0,
                            "maximum": 1
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum results to return",
                            "default": 10
                        }
                    },
                    "required": ["smiles"]
                }
            ),
            Tool(
                name="chemagent_lipinski",
                description="""Check if a compound satisfies Lipinski's Rule of Five.
                
Evaluates drug-likeness based on:
- Molecular weight ≤ 500
- LogP ≤ 5
- H-bond donors ≤ 5
- H-bond acceptors ≤ 10""",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "identifier": {
                            "type": "string",
                            "description": "Compound name, ChEMBL ID, or SMILES"
                        }
                    },
                    "required": ["identifier"]
                }
            ),
            Tool(
                name="chemagent_compound",
                description="""Get detailed information about a compound.
                
Accepts compound name (aspirin) or ChEMBL ID (CHEMBL25).
Returns structure, properties, synonyms, and database links.""",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "identifier": {
                            "type": "string",
                            "description": "Compound name or ChEMBL ID"
                        }
                    },
                    "required": ["identifier"]
                }
            ),
            Tool(
                name="chemagent_target",
                description="""Get information about a protein target.
                
Accepts UniProt ID (P00734) or gene name (EGFR).
Returns protein info, function, and associated drugs.""",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "identifier": {
                            "type": "string",
                            "description": "UniProt ID or gene/target name"
                        }
                    },
                    "required": ["identifier"]
                }
            ),
        ]
    
    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute a ChemAgent tool."""
        agent = get_agent()
        
        try:
            if name == "chemagent_query":
                # Main natural language query
                query = arguments.get("query", "")
                verbose = arguments.get("verbose", False)
                
                result = agent.query(query)
                
                response = {
                    "answer": result.answer,
                    "success": result.success,
                    "execution_time_ms": result.execution_time_ms,
                    "intent_type": result.intent_type,
                }
                
                if verbose:
                    response["provenance"] = result.provenance
                    response["steps_taken"] = result.steps_taken
                
                return [TextContent(
                    type="text",
                    text=json.dumps(response, indent=2, default=str)
                )]
            
            elif name == "chemagent_properties":
                smiles = arguments.get("smiles", "")
                result = agent.query(f"Calculate properties of {smiles}")
                
                return [TextContent(
                    type="text",
                    text=result.answer
                )]
            
            elif name == "chemagent_similarity":
                smiles = arguments.get("smiles", "")
                threshold = arguments.get("threshold", 0.7)
                limit = arguments.get("limit", 10)
                
                query = f"Find compounds similar to {smiles} with >{int(threshold*100)}% similarity"
                result = agent.query(query)
                
                return [TextContent(
                    type="text",
                    text=result.answer
                )]
            
            elif name == "chemagent_lipinski":
                identifier = arguments.get("identifier", "")
                result = agent.query(f"Is {identifier} drug-like?")
                
                return [TextContent(
                    type="text",
                    text=result.answer
                )]
            
            elif name == "chemagent_compound":
                identifier = arguments.get("identifier", "")
                result = agent.query(f"What is {identifier}?")
                
                return [TextContent(
                    type="text",
                    text=result.answer
                )]
            
            elif name == "chemagent_target":
                identifier = arguments.get("identifier", "")
                result = agent.query(f"Tell me about target {identifier}")
                
                return [TextContent(
                    type="text",
                    text=result.answer
                )]
            
            else:
                return [TextContent(
                    type="text",
                    text=f"Unknown tool: {name}"
                )]
                
        except Exception as e:
            logger.error(f"Tool {name} failed: {e}")
            return [TextContent(
                type="text",
                text=f"Error executing {name}: {str(e)}"
            )]
    
    # =========================================================================
    # RESOURCES - Data the AI can read
    # =========================================================================
    
    @server.list_resources()
    async def list_resources() -> list[Resource]:
        """List available resource types."""
        return [
            Resource(
                uri="chemagent://help",
                name="ChemAgent Help",
                description="Available query types and examples",
                mimeType="text/markdown"
            ),
            Resource(
                uri="chemagent://databases",
                name="Database Coverage",
                description="Information about integrated databases",
                mimeType="text/markdown"
            ),
        ]
    
    @server.read_resource()
    async def read_resource(uri: str) -> str:
        """Read a resource by URI."""
        if uri == "chemagent://help":
            return """# ChemAgent Query Types

## Compound Queries
- "What is aspirin?" - Get compound information
- "Get SMILES for ibuprofen" - Structure lookup

## Property Calculations
- "Calculate properties of CC(=O)Oc1ccccc1C(=O)O" - Molecular properties
- "What is the molecular weight of CHEMBL25?" - Specific property

## Drug-likeness
- "Is metformin drug-like?" - Lipinski Rule of Five check
- "Check Lipinski for caffeine" - Drug-likeness evaluation

## Similarity Search
- "Find compounds similar to aspirin" - Structural similarity
- "Search for molecules like CHEMBL25 with >80% similarity"

## Bioactivity
- "What is the IC50 of atorvastatin?" - Activity data
- "Get bioactivity data for CHEMBL25" - All activities

## Target Information
- "What is P00734?" - UniProt protein info
- "Tell me about EGFR" - Target details

## Disease Associations
- "What targets are associated with breast cancer?"
- "What drugs target EGFR?"
"""
        
        elif uri == "chemagent://databases":
            return """# ChemAgent Database Coverage

| Database | Description | Data Size |
|----------|-------------|-----------|
| ChEMBL | Bioactivity database | 2.4M+ compounds |
| PubChem | Chemical structures | 115M+ compounds |
| UniProt | Protein sequences | 500K+ proteins |
| Open Targets | Disease associations | Genome-wide |
| PDB | Protein structures | 200K+ structures |
| AlphaFold | AI predictions | Proteome-wide |

## Tools per Database
- **ChEMBL**: search, compound, similarity, substructure, activities
- **PubChem**: search, compound, similarity, bioassays
- **UniProt**: search, protein details
- **Open Targets**: disease-target, target-drug, evidence
- **RDKit**: properties, Lipinski, standardization, scaffolds
"""
        
        else:
            return f"Resource not found: {uri}"
    
    # =========================================================================
    # PROMPTS - Pre-built conversation templates
    # =========================================================================
    
    @server.list_prompts()
    async def list_prompts() -> list[Prompt]:
        """List available prompts."""
        return [
            Prompt(
                name="drug_discovery",
                description="Expert mode for drug discovery questions",
                arguments=[
                    {
                        "name": "compound",
                        "description": "Starting compound to analyze",
                        "required": False
                    }
                ]
            ),
            Prompt(
                name="compound_analysis",
                description="Comprehensive compound analysis workflow",
                arguments=[
                    {
                        "name": "compound",
                        "description": "Compound name or SMILES to analyze",
                        "required": True
                    }
                ]
            ),
        ]
    
    @server.get_prompt()
    async def get_prompt(name: str, arguments: dict[str, str] | None = None) -> GetPromptResult:
        """Get a prompt by name."""
        if name == "drug_discovery":
            compound = (arguments or {}).get("compound", "")
            
            messages = [
                PromptMessage(
                    role="user",
                    content=TextContent(
                        type="text",
                        text=f"""You are an expert pharmaceutical researcher with access to ChemAgent tools.

For drug discovery questions:
1. First search for the compound in ChEMBL
2. Calculate molecular properties
3. Check Lipinski's Rule of Five for drug-likeness
4. Find similar compounds that might be alternatives
5. Look up bioactivity data if available

Always cite your data sources (ChEMBL, PubChem, etc.).

{f'Starting compound to analyze: {compound}' if compound else 'Ask me about any compound or drug discovery question.'}"""
                    )
                )
            ]
            
            return GetPromptResult(
                description="Drug discovery expert mode",
                messages=messages
            )
        
        elif name == "compound_analysis":
            compound = (arguments or {}).get("compound", "aspirin")
            
            messages = [
                PromptMessage(
                    role="user",
                    content=TextContent(
                        type="text",
                        text=f"""Please perform a comprehensive analysis of: {compound}

Include:
1. Basic compound information (structure, synonyms, IDs)
2. Molecular properties (MW, LogP, PSA, etc.)
3. Drug-likeness assessment (Lipinski, Veber rules)
4. Known bioactivities and targets
5. Similar compounds in the database

Use the ChemAgent tools to gather this information."""
                    )
                )
            ]
            
            return GetPromptResult(
                description=f"Comprehensive analysis of {compound}",
                messages=messages
            )
        
        else:
            raise ValueError(f"Unknown prompt: {name}")
    
    return server


# =============================================================================
# Server Runner
# =============================================================================

async def run_mcp_server():
    """Run the MCP server using stdio transport."""
    server = create_mcp_server()
    
    logger.info("Starting ChemAgent MCP server...")
    
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


def main():
    """Entry point for the MCP server."""
    import asyncio
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run the server
    asyncio.run(run_mcp_server())


if __name__ == "__main__":
    main()
