# Claude Desktop Integration Guide

This guide explains how to integrate ChemAgent with Claude Desktop using the Model Context Protocol (MCP).

## Prerequisites

1. **ChemAgent installed** with MCP support:
   ```bash
   pip install chemagent[mcp]
   ```

2. **Claude Desktop** installed on your system
   - macOS: Download from [claude.ai/download](https://claude.ai/download)
   - Windows: Download from [claude.ai/download](https://claude.ai/download)

3. **Verify ChemAgent MCP server works**:
   ```bash
   # This should show "Starting ChemAgent MCP server..." then wait for input
   chemagent-mcp
   # Press Ctrl+C to exit
   ```

## Configuration

### Step 1: Locate Claude Desktop Config File

| OS | Config Path |
|----|-------------|
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |
| Linux | `~/.config/claude/claude_desktop_config.json` |

### Step 2: Add ChemAgent to Configuration

Edit the config file and add the ChemAgent server:

```json
{
  "mcpServers": {
    "chemagent": {
      "command": "chemagent-mcp"
    }
  }
}
```

If you have other MCP servers already configured, just add the `chemagent` entry:

```json
{
  "mcpServers": {
    "existing-server": { ... },
    "chemagent": {
      "command": "chemagent-mcp"
    }
  }
}
```

### Step 3: Advanced Configuration (Optional)

For more control, you can add environment variables:

```json
{
  "mcpServers": {
    "chemagent": {
      "command": "chemagent-mcp",
      "env": {
        "CHEMAGENT_CACHE_DIR": "~/.cache/chemagent",
        "CHEMAGENT_LOG_LEVEL": "INFO"
      }
    }
  }
}
```

If using a Python virtual environment:

```json
{
  "mcpServers": {
    "chemagent": {
      "command": "/path/to/venv/bin/chemagent-mcp"
    }
  }
}
```

Or using conda:

```json
{
  "mcpServers": {
    "chemagent": {
      "command": "conda",
      "args": ["run", "-n", "chemagent", "chemagent-mcp"]
    }
  }
}
```

### Step 4: Restart Claude Desktop

After editing the config:
1. Quit Claude Desktop completely (not just close the window)
2. Reopen Claude Desktop
3. Look for the MCP tools icon (hammer 🔨) in the chat interface

## Verifying the Integration

### Check Available Tools

In Claude Desktop, you should see ChemAgent tools available:

1. Click the tools icon (🔨) in the chat input area
2. You should see tools like:
   - `chemagent_query`
   - `chemagent_properties`
   - `chemagent_similarity`
   - `chemagent_lipinski`
   - `chemagent_compound`
   - `chemagent_target`

### Test Queries

Try these example prompts in Claude Desktop:

**Basic Property Calculation:**
```
Calculate the molecular properties of aspirin (CC(=O)Oc1ccccc1C(=O)O)
```

**Drug-likeness Check:**
```
Is ibuprofen drug-like according to Lipinski's rules?
```

**Compound Information:**
```
What can you tell me about metformin?
```

**Similarity Search:**
```
Find compounds similar to caffeine
```

**Target Lookup:**
```
Tell me about the EGFR protein target
```

## Troubleshooting

### Server Not Starting

1. **Check if chemagent-mcp is in PATH:**
   ```bash
   which chemagent-mcp
   ```

2. **Check MCP SDK is installed:**
   ```bash
   pip show mcp
   ```

3. **Check logs:**
   - macOS/Linux: `~/.config/claude/logs/`
   - Windows: `%APPDATA%\Claude\logs\`

### Tools Not Appearing

1. Ensure config file is valid JSON
2. Verify Claude Desktop was fully restarted
3. Check the MCP server name matches exactly: `chemagent`

### Connection Errors

1. **Test server manually:**
   ```bash
   echo '{"jsonrpc":"2.0","method":"initialize","params":{},"id":1}' | chemagent-mcp
   ```

2. **Check for port conflicts** if using network transport

### Slow Responses

Some queries (like database lookups) require network calls. For faster responses:
- Use local-only queries (property calculations, Lipinski checks)
- ChemAgent caches results automatically

## Example Sessions

### Drug Discovery Workflow

```
You: I'm researching compounds for a COX-2 inhibitor project. 
     Can you analyze celecoxib and find similar compounds?

Claude: I'll help you analyze celecoxib and find similar structures.
        [Uses chemagent_compound to get celecoxib info]
        [Uses chemagent_properties to calculate properties]
        [Uses chemagent_similarity to find similar compounds]
        
        Here's what I found...
```

### Lead Optimization

```
You: Check if this compound is drug-like: 
     CC(C)Cc1ccc(cc1)C(C)C(=O)O

Claude: I'll analyze this compound for drug-likeness.
        [Uses chemagent_lipinski tool]
        
        This compound passes Lipinski's Rule of Five...
```

## Resources

- [ChemAgent Documentation](../README.md)
- [MCP Protocol Specification](https://modelcontextprotocol.io/)
- [MCP Guide](MCP_GUIDE.md) - Detailed MCP explanation

## Support

If you encounter issues:
1. Check the [GitHub Issues](https://github.com/sdodlapati3/ChemAgent/issues)
2. Review logs in Claude Desktop's log directory
3. Test the MCP server independently before Claude integration
