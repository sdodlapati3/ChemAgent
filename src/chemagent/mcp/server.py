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
            # =====================================================================
            # ADVANCED COMBINED TOOLS (Phase F.4)
            # =====================================================================
            Tool(
                name="chemagent_drug_analysis",
                description="""Comprehensive drug candidate analysis.
                
Performs a complete drug-likeness evaluation including:
- Molecular properties calculation
- Lipinski's Rule of Five check
- Veber rules (rotatable bonds, TPSA)
- Lead-likeness assessment
- PAINS filter check (if available)

Returns a detailed report suitable for drug discovery workflows.""",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "smiles": {
                            "type": "string",
                            "description": "SMILES string of the compound to analyze"
                        },
                        "name": {
                            "type": "string",
                            "description": "Optional compound name for the report"
                        }
                    },
                    "required": ["smiles"]
                }
            ),
            Tool(
                name="chemagent_compare_compounds",
                description="""Compare two compounds side-by-side.
                
Compares molecular properties, drug-likeness, and structural features
of two compounds. Useful for lead optimization and SAR analysis.""",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "smiles1": {
                            "type": "string",
                            "description": "SMILES of first compound"
                        },
                        "smiles2": {
                            "type": "string",
                            "description": "SMILES of second compound"
                        },
                        "name1": {
                            "type": "string",
                            "description": "Optional name for first compound"
                        },
                        "name2": {
                            "type": "string",
                            "description": "Optional name for second compound"
                        }
                    },
                    "required": ["smiles1", "smiles2"]
                }
            ),
            Tool(
                name="chemagent_batch_properties",
                description="""Calculate properties for multiple compounds at once.
                
Efficiently processes a list of SMILES strings and returns
properties for all compounds in a structured format.""",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "smiles_list": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of SMILES strings to analyze"
                        }
                    },
                    "required": ["smiles_list"]
                }
            ),
            Tool(
                name="chemagent_scaffold_analysis",
                description="""Analyze the molecular scaffold of a compound.
                
Extracts and analyzes the core scaffold structure, identifies
functional groups, and provides scaffold-based insights.""",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "smiles": {
                            "type": "string",
                            "description": "SMILES string to analyze"
                        }
                    },
                    "required": ["smiles"]
                }
            ),
            Tool(
                name="chemagent_target_compounds",
                description="""Find compounds that interact with a specific target.
                
Searches databases for known compounds targeting a specific
protein. Useful for competitive analysis and drug repurposing.""",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "target": {
                            "type": "string",
                            "description": "Target name, gene symbol, or UniProt ID"
                        },
                        "activity_type": {
                            "type": "string",
                            "description": "Activity type filter (e.g., IC50, Ki, EC50)",
                            "default": "IC50"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of compounds to return",
                            "default": 10
                        }
                    },
                    "required": ["target"]
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
            
            # =================================================================
            # ADVANCED COMBINED TOOLS (Phase F.4)
            # =================================================================
            
            elif name == "chemagent_drug_analysis":
                smiles = arguments.get("smiles", "")
                name_arg = arguments.get("name", "Compound")
                
                # Perform comprehensive analysis
                from rdkit import Chem
                from chemagent.tools.rdkit_tools import RDKitTools
                
                rdkit = RDKitTools()
                mol = Chem.MolFromSmiles(smiles)
                
                if mol is None:
                    return [TextContent(
                        type="text",
                        text=f"Error: Invalid SMILES string: {smiles}"
                    )]
                
                # Calculate properties
                props = rdkit.calc_molecular_properties(mol)
                lipinski = rdkit.calc_lipinski(mol)
                
                # Build comprehensive report
                report = {
                    "compound_name": name_arg,
                    "smiles": smiles,
                    "molecular_properties": {
                        "molecular_weight": props.molecular_weight,
                        "logp": props.logp,
                        "tpsa": props.tpsa,
                        "num_h_donors": props.num_h_donors,
                        "num_h_acceptors": props.num_h_acceptors,
                        "num_rotatable_bonds": props.num_rotatable_bonds,
                        "num_rings": props.num_rings,
                        "fraction_csp3": props.fraction_csp3,
                    },
                    "drug_likeness": {
                        "lipinski_rule_of_5": {
                            "passes": lipinski.passes,
                            "violations": lipinski.violations,
                            "violation_details": lipinski.details,
                            "thresholds": {
                                "mw": f"{lipinski.molecular_weight:.1f} (limit: 500)",
                                "logp": f"{lipinski.logp:.2f} (limit: 5)",
                                "hbd": f"{lipinski.num_h_donors} (limit: 5)",
                                "hba": f"{lipinski.num_h_acceptors} (limit: 10)",
                            }
                        },
                        "veber_rules": {
                            "rotatable_bonds_ok": props.num_rotatable_bonds <= 10,
                            "tpsa_ok": props.tpsa <= 140,
                        },
                        "lead_likeness": {
                            "mw_range": 250 <= props.molecular_weight <= 350,
                            "logp_range": -1 <= props.logp <= 3,
                            "rotatable_bonds_ok": props.num_rotatable_bonds <= 7,
                        }
                    },
                    "assessment": "Drug-like" if lipinski.passes else f"Not drug-like ({lipinski.violations} Lipinski violations)"
                }
                
                return [TextContent(
                    type="text",
                    text=json.dumps(report, indent=2)
                )]
            
            elif name == "chemagent_compare_compounds":
                smiles1 = arguments.get("smiles1", "")
                smiles2 = arguments.get("smiles2", "")
                name1 = arguments.get("name1", "Compound 1")
                name2 = arguments.get("name2", "Compound 2")
                
                from rdkit import Chem
                from rdkit import DataStructs
                from rdkit.Chem import AllChem
                from chemagent.tools.rdkit_tools import RDKitTools
                
                rdkit = RDKitTools()
                mol1 = Chem.MolFromSmiles(smiles1)
                mol2 = Chem.MolFromSmiles(smiles2)
                
                if mol1 is None or mol2 is None:
                    return [TextContent(
                        type="text",
                        text="Error: Invalid SMILES string(s)"
                    )]
                
                # Calculate properties for both
                props1 = rdkit.calc_molecular_properties(mol1)
                props2 = rdkit.calc_molecular_properties(mol2)
                lip1 = rdkit.calc_lipinski(mol1)
                lip2 = rdkit.calc_lipinski(mol2)
                
                # Calculate similarity
                fp1 = AllChem.GetMorganFingerprintAsBitVect(mol1, 2, nBits=2048)
                fp2 = AllChem.GetMorganFingerprintAsBitVect(mol2, 2, nBits=2048)
                similarity = DataStructs.TanimotoSimilarity(fp1, fp2)
                
                comparison = {
                    "compound_1": {
                        "name": name1,
                        "smiles": smiles1,
                        "mw": props1.molecular_weight,
                        "logp": props1.logp,
                        "tpsa": props1.tpsa,
                        "hbd": props1.num_h_donors,
                        "hba": props1.num_h_acceptors,
                        "lipinski_passes": lip1.passes,
                    },
                    "compound_2": {
                        "name": name2,
                        "smiles": smiles2,
                        "mw": props2.molecular_weight,
                        "logp": props2.logp,
                        "tpsa": props2.tpsa,
                        "hbd": props2.num_h_donors,
                        "hba": props2.num_h_acceptors,
                        "lipinski_passes": lip2.passes,
                    },
                    "comparison": {
                        "tanimoto_similarity": round(similarity, 3),
                        "mw_difference": round(props2.molecular_weight - props1.molecular_weight, 2),
                        "logp_difference": round(props2.logp - props1.logp, 2),
                        "both_drug_like": lip1.passes and lip2.passes,
                    }
                }
                
                return [TextContent(
                    type="text",
                    text=json.dumps(comparison, indent=2)
                )]
            
            elif name == "chemagent_batch_properties":
                smiles_list = arguments.get("smiles_list", [])
                
                from rdkit import Chem
                from chemagent.tools.rdkit_tools import RDKitTools
                
                rdkit = RDKitTools()
                results = []
                
                for i, smiles in enumerate(smiles_list[:50]):  # Limit to 50
                    mol = Chem.MolFromSmiles(smiles)
                    if mol is None:
                        results.append({
                            "index": i,
                            "smiles": smiles,
                            "error": "Invalid SMILES"
                        })
                        continue
                    
                    props = rdkit.calc_molecular_properties(mol)
                    lip = rdkit.calc_lipinski(mol)
                    
                    results.append({
                        "index": i,
                        "smiles": smiles,
                        "mw": round(props.molecular_weight, 2),
                        "logp": round(props.logp, 2),
                        "tpsa": round(props.tpsa, 2),
                        "hbd": props.num_h_donors,
                        "hba": props.num_h_acceptors,
                        "lipinski_passes": lip.passes,
                    })
                
                return [TextContent(
                    type="text",
                    text=json.dumps({"compounds": results, "total": len(results)}, indent=2)
                )]
            
            elif name == "chemagent_scaffold_analysis":
                smiles = arguments.get("smiles", "")
                
                from rdkit import Chem
                from rdkit.Chem.Scaffolds import MurckoScaffold
                from chemagent.tools.rdkit_tools import RDKitTools
                
                rdkit = RDKitTools()
                mol = Chem.MolFromSmiles(smiles)
                
                if mol is None:
                    return [TextContent(
                        type="text",
                        text=f"Error: Invalid SMILES: {smiles}"
                    )]
                
                # Extract scaffolds
                try:
                    core = MurckoScaffold.GetScaffoldForMol(mol)
                    generic = MurckoScaffold.MakeScaffoldGeneric(core)
                    core_smiles = Chem.MolToSmiles(core)
                    generic_smiles = Chem.MolToSmiles(generic)
                except Exception:
                    core_smiles = "Could not extract"
                    generic_smiles = "Could not extract"
                
                # Get properties
                props = rdkit.calc_molecular_properties(mol)
                
                analysis = {
                    "input_smiles": smiles,
                    "murcko_scaffold": core_smiles,
                    "generic_scaffold": generic_smiles,
                    "properties": {
                        "num_rings": props.num_rings,
                        "num_aromatic_rings": props.num_aromatic_rings,
                        "num_heteroatoms": props.num_heteroatoms,
                        "fraction_csp3": round(props.fraction_csp3, 3),
                    },
                    "scaffold_complexity": "High" if props.num_rings > 3 else "Medium" if props.num_rings > 1 else "Low"
                }
                
                return [TextContent(
                    type="text",
                    text=json.dumps(analysis, indent=2)
                )]
            
            elif name == "chemagent_target_compounds":
                target = arguments.get("target", "")
                activity_type = arguments.get("activity_type", "IC50")
                limit = arguments.get("limit", 10)
                
                # Use ChemAgent to query for target compounds
                query = f"Find compounds with {activity_type} activity against {target}, limit {limit}"
                result = agent.query(query)
                
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
