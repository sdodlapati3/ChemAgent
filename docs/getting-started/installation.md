# Installation Guide

This guide will help you install and set up ChemAgent on your system.

---

## System Requirements

- **Python**: 3.10 or higher
- **Operating System**: Linux, macOS, or Windows
- **Memory**: 4GB RAM minimum (8GB recommended)
- **Disk Space**: 2GB for dependencies and caching

---

## Installation Methods

### Method 1: Using Conda (Recommended)

```bash
# Create a new conda environment
conda create -n chemagent python=3.10
conda activate chemagent

# Install ChemAgent
cd ChemAgent
pip install -e ".[dev]"
```

### Method 2: Using pip and venv

```bash
# Create virtual environment
python3.10 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install ChemAgent
cd ChemAgent
pip install -e ".[dev]"
```

### Method 3: Docker (Production)

```bash
# Build Docker image
docker-compose build

# Run ChemAgent
docker-compose up
```

---

## Verifying Installation

### Test Basic Functionality

```bash
# Test CLI
python -m chemagent "What is aspirin?"

# Should output compound information
```

### Run Tests

```bash
# Run unit tests
pytest tests/unit/ -v

# Run integration tests (requires internet)
pytest tests/integration/test_full_pipeline.py -v
```

### Check Version

```python
import chemagent
print(chemagent.__version__)  # Should print: 1.0.0
```

---

## Dependencies

### Core Dependencies

- **FastAPI**: Web API framework
- **RDKit**: Chemistry toolkit
- **requests**: HTTP client
- **diskcache**: Result caching

### Optional Dependencies

- **uvicorn**: ASGI server (for API)
- **gradio**: Web UI
- **pytest**: Testing framework (dev)
- **black**: Code formatter (dev)

---

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# API Keys (optional, for cloud LLMs)
OPENAI_API_KEY=your_openai_key
GEMINI_API_KEY=your_gemini_key

# Cache Settings
CHEMAGENT_CACHE_DIR=~/.cache/chemagent
CHEMAGENT_CACHE_TTL=3600

# Performance
CHEMAGENT_MAX_WORKERS=4
CHEMAGENT_QUERY_TIMEOUT=30
```

### Cache Directory

ChemAgent uses disk caching for performance:

```bash
# Default cache location
~/.cache/chemagent/

# Clear cache if needed
rm -rf ~/.cache/chemagent/*
```

---

## Common Issues

### Issue: RDKit Import Error

**Problem**: `ImportError: No module named 'rdkit'`

**Solution**:
```bash
# Install RDKit via conda (recommended)
conda install -c conda-forge rdkit

# Or via pip (may have issues on some systems)
pip install rdkit-pypi
```

### Issue: ChEMBL API Timeout

**Problem**: Queries timeout when accessing ChEMBL

**Solution**:
```python
# Increase timeout in your code
agent = ChemAgent(chembl_timeout=60)
```

### Issue: Permission Denied on Cache Directory

**Problem**: Cannot write to cache directory

**Solution**:
```bash
# Create cache directory with proper permissions
mkdir -p ~/.cache/chemagent
chmod 755 ~/.cache/chemagent
```

---

## Platform-Specific Notes

### macOS

- Use Homebrew to install Python 3.10
- RDKit works best via conda on macOS

### Linux

- Most distributions work out of the box
- Ensure development headers are installed:
  ```bash
  # Ubuntu/Debian
  sudo apt-get install python3-dev build-essential
  ```

### Windows

- Use Anaconda or Miniconda (recommended)
- Some dependencies may require Visual Studio Build Tools
- Use Windows Subsystem for Linux (WSL) for best experience

---

## Next Steps

After successful installation:

1. **[Quick Start Tutorial](quickstart.md)** - Run your first queries
2. **[Examples](examples.md)** - Learn common patterns
3. **[User Guide](../user-guide/USER_GUIDE.md)** - Explore all features

---

## Getting Help

- **Installation issues**: Check [GitHub Issues](https://github.com/yourusername/ChemAgent/issues)
- **Dependency problems**: See [requirements.txt](../../requirements.txt)
- **General questions**: Open a GitHub Discussion

---

**Last Updated**: January 11, 2026
