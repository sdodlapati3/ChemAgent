# VS Code Copilot MCP Integration Guide

This guide explains how to integrate ChemAgent with VS Code using the Model Context Protocol (MCP) for GitHub Copilot Chat.

## Prerequisites

1. **ChemAgent installed** with MCP support:
   ```bash
   pip install chemagent[mcp]
   ```

2. **VS Code** with GitHub Copilot extension installed
   - [GitHub Copilot](https://marketplace.visualstudio.com/items?itemName=GitHub.copilot)
   - [GitHub Copilot Chat](https://marketplace.visualstudio.com/items?itemName=GitHub.copilot-chat)

3. **Verify ChemAgent MCP server works**:
   ```bash
   chemagent-mcp  # Should start and wait for input
   # Press Ctrl+C to exit
   ```

## Configuration

### Option 1: Workspace Configuration (Recommended)

Create a `.vscode/mcp.json` file in your workspace:

```json
{
  "servers": {
    "chemagent": {
      "type": "stdio",
      "command": "chemagent-mcp"
    }
  }
}
```

### Option 2: User Settings

Add to your VS Code `settings.json`:

```json
{
  "github.copilot.chat.mcpServers": {
    "chemagent": {
      "command": "chemagent-mcp"
    }
  }
}
```

### Option 3: Using Virtual Environment

If ChemAgent is in a virtual environment:

```json
{
  "servers": {
    "chemagent": {
      "type": "stdio",
      "command": "/path/to/venv/bin/chemagent-mcp"
    }
  }
}
```

### Option 4: Using Conda

```json
{
  "servers": {
    "chemagent": {
      "type": "stdio",
      "command": "conda",
      "args": ["run", "-n", "chemagent", "chemagent-mcp"]
    }
  }
}
```

## Setup Steps

### Step 1: Create Configuration File

In your workspace root, create `.vscode/mcp.json`:

```bash
mkdir -p .vscode
cat > .vscode/mcp.json << 'EOF'
{
  "servers": {
    "chemagent": {
      "type": "stdio",
      "command": "chemagent-mcp"
    }
  }
}
EOF
```

### Step 2: Reload VS Code

Press `Ctrl+Shift+P` (or `Cmd+Shift+P` on macOS) and run:
```
Developer: Reload Window
```

### Step 3: Verify Connection

1. Open Copilot Chat (click the chat icon or press `Ctrl+Shift+I`)
2. Type `@` to see available agents
3. You should see ChemAgent tools available

## Using ChemAgent in Copilot Chat

### Direct Tool Usage

Reference ChemAgent directly in your prompts:

```
@workspace Calculate the molecular properties of this SMILES: CCO

@workspace Is this compound drug-like? CC(=O)Oc1ccccc1C(=O)O

@workspace Find compounds similar to aspirin
```

### Natural Language Queries

Copilot will automatically use ChemAgent tools when relevant:

```
What are the properties of caffeine?

Check if metformin passes Lipinski's rules

Tell me about the EGFR protein target
```

### In Code Context

When working on chemistry-related code, Copilot can use ChemAgent:

```python
# Ask Copilot: "What are the properties of this molecule?"
smiles = "CC(=O)Oc1ccccc1C(=O)O"  # Aspirin

# Copilot will use chemagent_properties tool and provide:
# MW: 180.16, LogP: 1.19, HBD: 1, HBA: 4, etc.
```

## Available Tools in VS Code

| Tool | Description | Example Use |
|------|-------------|-------------|
| `chemagent_query` | Natural language chemistry queries | "What is aspirin?" |
| `chemagent_properties` | Calculate molecular properties | Properties of SMILES |
| `chemagent_similarity` | Find similar compounds | Similar to caffeine |
| `chemagent_lipinski` | Drug-likeness check | Is X drug-like? |
| `chemagent_compound` | Compound database lookup | Info about CHEMBL25 |
| `chemagent_target` | Protein target lookup | About EGFR target |

## Example Workflows

### Drug Discovery Research

```
User: I'm analyzing potential drug candidates. Can you help me 
      evaluate this compound: CN1C=NC2=C1C(=O)N(C(=O)N2C)C

Copilot: [Uses chemagent_properties]
         [Uses chemagent_lipinski]
         
         This is caffeine. Here are its properties:
         - Molecular Weight: 194.19
         - LogP: -0.07
         - Drug-likeness: Passes all Lipinski rules
         ...
```

### Code Generation with Chemistry Context

```python
# In your Python file, ask Copilot:
# "Generate code to check if molecules in this list are drug-like"

molecules = [
    "CC(=O)Oc1ccccc1C(=O)O",  # Aspirin
    "CC(C)Cc1ccc(cc1)C(C)C(=O)O",  # Ibuprofen
]

# Copilot generates code using ChemAgent knowledge
```

### Documentation Assistance

```
# In a markdown file:
# "Document the properties of common NSAIDs"

Copilot will use ChemAgent to look up actual property data
and generate accurate documentation.
```

## Troubleshooting

### MCP Server Not Detected

1. **Check configuration path:**
   - Workspace: `.vscode/mcp.json`
   - User: `settings.json`

2. **Verify command is accessible:**
   ```bash
   which chemagent-mcp
   ```

3. **Check VS Code Output:**
   - Open Output panel (`Ctrl+Shift+U`)
   - Select "GitHub Copilot Chat" from dropdown
   - Look for MCP-related messages

### Connection Errors

1. **Test server independently:**
   ```bash
   chemagent-mcp
   ```

2. **Check Python environment:**
   - Ensure `mcp` package is installed
   - Verify correct Python interpreter

### Slow Responses

Some operations require network calls:
- Compound lookups (ChEMBL, PubChem)
- Target searches (UniProt)
- Similarity searches (database queries)

Local operations are fast:
- Property calculations
- Lipinski checks
- SMILES validation

## Tips for Best Results

1. **Be Specific:** "Calculate properties of SMILES CC(=O)O" works better than "analyze this"

2. **Use Technical Terms:** Copilot understands chemistry terminology

3. **Provide Context:** When working on specific research, mention the context

4. **Combine with Code:** ChemAgent works well when you're writing chemistry code

## Advanced Configuration

### Environment Variables

```json
{
  "servers": {
    "chemagent": {
      "type": "stdio",
      "command": "chemagent-mcp",
      "env": {
        "CHEMAGENT_CACHE_DIR": "${workspaceFolder}/.cache",
        "CHEMAGENT_LOG_LEVEL": "DEBUG"
      }
    }
  }
}
```

### Multiple Environments

```json
{
  "servers": {
    "chemagent-dev": {
      "type": "stdio",
      "command": "chemagent-mcp",
      "env": {
        "CHEMAGENT_LOG_LEVEL": "DEBUG"
      }
    },
    "chemagent-prod": {
      "type": "stdio",
      "command": "chemagent-mcp",
      "env": {
        "CHEMAGENT_LOG_LEVEL": "WARNING"
      }
    }
  }
}
```

## Resources

- [ChemAgent Documentation](../../README.md)
- [MCP Protocol Specification](https://modelcontextprotocol.io/)
- [VS Code MCP Documentation](https://code.visualstudio.com/docs/copilot/chat/mcp-servers)
- [MCP Guide](MCP_GUIDE.md) - Detailed MCP explanation

## Support

For issues:
1. Check [GitHub Issues](https://github.com/sdodlapati3/ChemAgent/issues)
2. Review VS Code's Output panel for errors
3. Test MCP server independently
