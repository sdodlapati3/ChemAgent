# Contributing to ChemAgent

Thank you for your interest in contributing to ChemAgent! This document provides guidelines and instructions for contributing.

---

## 🚀 Quick Start for Contributors

### 1. Development Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/ChemAgent.git
cd ChemAgent

# Create development environment
conda create -n chemagent-dev python=3.10
conda activate chemagent-dev

# Install in development mode with all dependencies
pip install -e ".[dev]"

# Verify installation
python -m chemagent "What is aspirin?"
pytest tests/unit/ -v
```

### 2. Create a Branch

```bash
# Update main branch
git checkout master
git pull origin master

# Create feature branch
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

---

## 📋 Code Standards

### Style Guidelines

We follow standard Python conventions:

- **PEP 8** for code style
- **Google-style** docstrings
- **Type hints** on all public functions
- **Black** for code formatting
- **isort** for import sorting

### Code Formatting

```bash
# Format code
black src/ tests/

# Sort imports
isort src/ tests/

# Check style
flake8 src/ tests/

# Type checking
mypy src/
```

### Docstring Example

```python
def query(self, user_query: str, timeout: int = 30) -> QueryResult:
    """
    Execute a natural language query.
    
    Args:
        user_query: Natural language question about compounds/targets
        timeout: Maximum execution time in seconds (default: 30)
        
    Returns:
        QueryResult containing answer, provenance, and metadata
        
    Raises:
        ValueError: If query is empty or invalid
        TimeoutError: If execution exceeds timeout
        
    Examples:
        >>> agent = ChemAgent()
        >>> result = agent.query("What is CHEMBL25?")
        >>> print(result.answer)
        
    Note:
        Queries are cached by default. Use use_cache=False to disable.
    """
```

---

## 🧪 Testing Requirements

### Running Tests

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/unit/test_intent_parser.py -v

# Run with coverage
pytest --cov=chemagent tests/

# Run integration tests (slower)
pytest tests/integration/ -v
```

### Writing Tests

- **Unit tests**: Test individual functions/classes in isolation
- **Integration tests**: Test component interactions
- **Use fixtures**: For common test setups
- **Mock external APIs**: Don't hit real ChEMBL/UniProt in unit tests

Example test:

```python
import pytest
from chemagent import ChemAgent

def test_compound_lookup():
    """Test basic compound lookup query."""
    agent = ChemAgent()
    result = agent.query("What is CHEMBL25?")
    
    assert result.success is True
    assert "aspirin" in result.answer.lower()
    assert result.execution_time_ms > 0
```

### Test Coverage Requirements

- **Minimum**: 80% coverage for new code
- **Target**: 90% coverage overall
- **Critical paths**: 100% coverage (query pipeline, executor)

---

## 🏗️ Architecture Guidelines

### Code Organization

```
src/chemagent/
├── __init__.py           # Public API exports
├── core/                 # Business logic (no external API calls)
│   ├── intent_parser.py  # Query understanding
│   ├── query_planner.py  # Execution planning
│   └── executor.py       # Plan execution
├── tools/                # External API integrations
│   ├── chembl_client.py
│   ├── rdkit_tools.py
│   └── uniprot_client.py
├── api/                  # FastAPI server
└── cli/                  # Command-line interface
```

### Design Principles

1. **Separation of Concerns**: Core logic separate from I/O
2. **Dependency Injection**: Pass dependencies explicitly
3. **Interface-based Design**: Use protocols/ABCs for extensibility
4. **Immutable Data**: Use dataclasses with frozen=True where possible
5. **Fail Fast**: Validate inputs early, raise clear exceptions

### Adding New Features

When adding a new intent type or tool:

1. **Intent Parser**: Add pattern matching in `intent_parser.py`
2. **Query Planner**: Add plan generation in `query_planner.py`
3. **Tool Implementation**: Create/update tool in `tools/`
4. **Response Formatter**: Add formatting in `response_formatter.py`
5. **Tests**: Add unit and integration tests
6. **Documentation**: Update relevant docs

---

## 📝 Documentation Standards

### Code Documentation

- **All public functions**: Must have docstrings
- **Complex logic**: Add inline comments explaining "why"
- **Type hints**: Required on all function signatures
- **Examples**: Include usage examples in docstrings

### User Documentation

When adding features that affect users:

1. Update relevant user guide (docs/user-guide/)
2. Add examples to docs/getting-started/examples.md
3. Update README.md if it's a major feature
4. Add to CHANGELOG.md

---

## 🔄 Pull Request Process

### Before Submitting

- [ ] Tests pass: `pytest tests/`
- [ ] Code formatted: `black src/ tests/`
- [ ] Type checking passes: `mypy src/`
- [ ] Documentation updated
- [ ] CHANGELOG.md updated (if applicable)
- [ ] Commit messages are clear and descriptive

### PR Description Template

```markdown
## Description
Brief description of what this PR does

## Motivation
Why is this change needed?

## Changes
- List of specific changes made
- Another change

## Testing
How was this tested?

## Checklist
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] Code formatted with black
- [ ] Type hints added
```

### Review Process

1. Automated tests run on GitHub Actions
2. Code review by maintainer
3. Address feedback
4. Approval and merge

---

## 🐛 Bug Reports

### Reporting Bugs

Use GitHub Issues with the "bug" label. Include:

1. **Description**: Clear description of the bug
2. **Steps to Reproduce**: Exact steps to trigger the bug
3. **Expected Behavior**: What should happen
4. **Actual Behavior**: What actually happens
5. **Environment**: Python version, OS, ChemAgent version
6. **Error Messages**: Full error output if applicable

Example:

```markdown
**Description**
Query fails with "KeyError" when looking up certain ChEMBL IDs

**Steps to Reproduce**
1. Run: `python -m chemagent "What is CHEMBL999999?"`
2. Error occurs

**Expected**
Should return "Compound not found" message

**Actual**
KeyError: 'chembl_id'

**Environment**
- Python 3.10.4
- ChemAgent 1.0.0
- Ubuntu 22.04
```

---

## 💡 Feature Requests

### Proposing Features

Use GitHub Issues with the "enhancement" label. Include:

1. **Use Case**: What problem does this solve?
2. **Proposed Solution**: How should it work?
3. **Alternatives**: Other approaches considered?
4. **Examples**: Usage examples

---

## 🎯 Development Priorities

### Current Focus Areas

1. **LLM Integration** (Priority 1)
   - Natural language understanding
   - Multi-turn conversations
   - Context retention

2. **Performance** (Priority 2)
   - Advanced caching strategies
   - Query optimization
   - Parallel execution improvements

3. **Extensibility** (Priority 3)
   - Plugin system for new tools
   - Custom intent types
   - Configurable pipelines

See [FUTURE_ENHANCEMENTS_PLAN.md](FUTURE_ENHANCEMENTS_PLAN.md) for detailed roadmap.

---

## 📖 Resources

- **Architecture**: [docs/developer/ARCHITECTURE.md](docs/developer/ARCHITECTURE.md)
- **User Guide**: [docs/user-guide/USER_GUIDE.md](docs/user-guide/USER_GUIDE.md)
- **API Docs**: [docs/user-guide/API_DOCUMENTATION.md](docs/user-guide/API_DOCUMENTATION.md)
- **Testing Guide**: [docs/developer/testing.md](docs/developer/testing.md)

---

## 🤝 Code of Conduct

Be respectful, inclusive, and constructive. We're all here to build something useful together.

---

## ❓ Questions?

- Open a GitHub Discussion
- Tag maintainers in issues
- Check existing documentation first

---

**Thank you for contributing to ChemAgent!** 🎉
