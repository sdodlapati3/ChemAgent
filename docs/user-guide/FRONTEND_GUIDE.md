# ChemAgent Frontend/UI Guide

## 🎯 Overview

ChemAgent includes a beautiful **Gradio-based web interface** for interacting with the pharmaceutical research assistant through a modern browser interface.

## ✅ Status

**All frontend tests passing: 4/4** ✓

- ✅ UI Module Import
- ✅ Gradio App Creation
- ✅ ChemAgent Integration
- ✅ UI Processing Methods

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- ChemAgent environment activated
- Gradio 6.0+ installed (added to requirements.txt)

### Launch the UI

```bash
# Method 1: Using the run module
module load python3
crun -p ~/envs/chemagent python -m chemagent.ui.run

# Method 2: Using the standalone script
module load python3
crun -p ~/envs/chemagent python src/chemagent/ui/run.py

# Method 3: With custom host and port
module load python3
crun -p ~/envs/chemagent python -m chemagent.ui.run --host 0.0.0.0 --port 7860

# Method 4: With public sharing (creates a public URL)
module load python3
crun -p ~/envs/chemagent python -m chemagent.ui.run --share
```

The UI will be available at: **http://localhost:7860** (or your specified port)

## 🎨 Features

### Main Interface Tabs

#### 1. 🔍 **Query Tab**
- Natural language query input
- Example queries for quick start
- Real-time result visualization
- Options for caching and verbose output
- Beautiful formatted responses in markdown

**Example Queries:**
- "What is CHEMBL25?"
- "Find similar compounds to aspirin"
- "Get properties for caffeine"
- "What targets does ibuprofen bind to?"
- "Compare molecular weight of aspirin and ibuprofen"

#### 2. 📦 **Batch Processing Tab**
- Process multiple queries at once (one per line)
- Parallel execution for faster results
- Batch results summary
- Individual query status tracking

#### 3. 📜 **History Tab**
- View recent queries
- Search through query history
- Favorite queries for quick access
- Load previous queries to re-run
- Clear history when needed

#### 4. ❓ **Help Tab**
- Complete query type examples
- Keyboard shortcuts
- Feature documentation
- API access information

## 🎯 Query Types Supported

### 1. Compound Lookup
```
"What is CHEMBL25?"
"Tell me about aspirin"
"Look up CC(=O)OC1=CC=CC=C1C(=O)O"
```

### 2. Property Queries
```
"What is the molecular weight of aspirin?"
"Get properties for CHEMBL25"
"Calculate druglikeness for caffeine"
```

### 3. Similarity Search
```
"Find similar compounds to aspirin"
"Search for analogs of CHEMBL25 with similarity > 0.8"
"Top 10 most similar compounds to caffeine"
```

### 4. Target Queries
```
"What targets does aspirin bind to?"
"Find compounds that bind to COX-2"
"Get binding affinities for metformin"
```

### 5. Complex Workflows
```
"Find similar compounds to aspirin and get their targets"
"Compare properties of aspirin and ibuprofen"
"Find COX-2 inhibitors with IC50 < 100nM"
```

## 🔧 Configuration

The UI supports several configuration options:

```python
from chemagent.ui import launch_app

launch_app(
    server_name="0.0.0.0",  # Host address
    server_port=7860,        # Port number
    share=False,             # Create public share link
    # Additional Gradio options...
)
```

## 📊 Components

### ChemAgentUI Class
Main UI controller that manages:
- Query processing
- Batch execution
- History management
- Result visualization
- Status updates

### HistoryManager
Manages query history with:
- JSON-based persistence
- Search functionality
- Favorites support
- Automatic cleanup

### ResultVisualizer
Generates HTML visualizations for:
- Compound information
- Molecular properties
- Search results
- Target data
- Error messages

## 🎨 UI Styling

The interface uses:
- **Gradio Soft Theme**: Clean, modern appearance
- **Custom CSS**: Improved typography and spacing
- **Responsive Layout**: Works on desktop and mobile
- **Markdown Rendering**: Beautiful formatted responses
- **Color-coded Status**: Success (green), Error (red), Info (blue)

## 🧪 Testing

Verify UI functionality:

```bash
# Run UI verification tests
module load python3
crun -p ~/envs/chemagent python test_ui.py

# Expected output:
# ✓ PASS: Import UI Module
# ✓ PASS: Create Gradio App
# ✓ PASS: ChemAgent Integration
# ✓ PASS: UI Processing Methods
```

## ⚡ Performance

- **Caching**: Enabled by default for faster repeated queries
- **Parallel Execution**: Multi-threaded for independent operations
- **Streaming**: Real-time progress updates (backend support)
- **History**: Last 10 queries loaded by default

## 🐛 Troubleshooting

### ModuleNotFoundError: No module named 'gradio'

```bash
# Install Gradio
module load python3
crun -p ~/envs/chemagent pip install gradio
```

### Port Already in Use

```bash
# Use a different port
python -m chemagent.ui.run --port 7861
```

### Cannot Access UI from Remote Machine

```bash
# Bind to all interfaces
python -m chemagent.ui.run --host 0.0.0.0
```

### UI Loads But Queries Fail

- Check ChemAgent installation: `python test_improvements.py`
- Verify API access (ChEMBL, UniProt, etc.)
- Check network connectivity
- Review logs for errors

## 📝 Development

To customize the UI:

1. **Add New Query Examples**: Edit `src/chemagent/ui/app.py` → `example_queries` list
2. **Modify Layout**: Update `create_app()` function
3. **Add New Tabs**: Use `with gr.Tab("Name"):` pattern
4. **Custom Visualizations**: Extend `ResultVisualizer` class
5. **Add Features**: Update `ChemAgentUI` class methods

## 🔗 Related

- **REST API**: See `src/chemagent/api/server.py` for FastAPI endpoints
- **CLI Interface**: Run `python -m chemagent --help`
- **Core Library**: Import `from chemagent import ChemAgent` in Python

## 📚 Additional Resources

- [Gradio Documentation](https://gradio.app/docs/)
- [ChemAgent API Documentation](docs/API_DOCUMENTATION.md)
- [User Guide](docs/USER_GUIDE.md)
- [Architecture Overview](docs/ARCHITECTURE.md)

## 🎉 What's Working

- ✅ Gradio 6.0 compatibility
- ✅ All 4 tabs functional
- ✅ Query processing with ChemAgent facade
- ✅ History persistence
- ✅ Batch processing
- ✅ Result visualization
- ✅ Example queries
- ✅ Help documentation
- ✅ Error handling
- ✅ Status updates

## 🚀 Future Enhancements

See [FUTURE_ENHANCEMENTS_PLAN.md](../FUTURE_ENHANCEMENTS_PLAN.md) for planned features:

1. **Real-time Streaming**: WebSocket-based live updates
2. **Structure Visualization**: RDKit molecule rendering
3. **Query Templates**: Pre-built query library
4. **Export Formats**: CSV, PDF, HTML reports
5. **Favorites & Tags**: Better query organization

---

**Ready to explore pharmaceutical research with ChemAgent's beautiful web interface!** 🧪✨
