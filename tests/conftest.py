"""
Pytest Configuration
====================

Shared fixtures and configuration for all tests.
"""

import pytest
from pathlib import Path
from rdkit import Chem


@pytest.fixture(scope="session")
def test_data_dir():
    """Return path to test data directory."""
    return Path(__file__).parent / "data"


@pytest.fixture
def example_smiles():
    """Common test SMILES strings."""
    return {
        "aspirin": "CC(=O)Oc1ccccc1C(=O)O",
        "ibuprofen": "CC(C)Cc1ccc(cc1)C(C)C(=O)O",
        "caffeine": "CN1C=NC2=C1C(=O)N(C(=O)N2C)C",
        "ethanol": "CCO",
        "benzene": "c1ccccc1",
        "phenol": "c1ccc(cc1)O",
    }


@pytest.fixture
def example_mols(example_smiles):
    """Common test molecules as RDKit Mol objects."""
    return {name: Chem.MolFromSmiles(smiles) for name, smiles in example_smiles.items()}


# Configure pytest markers
def pytest_configure(config):
    """Configure custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "requires_api: marks tests that require external API access"
    )
