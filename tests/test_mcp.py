"""
Unit tests for MCP (Model Context Protocol) server module.

Tests the MCP server creation, tool definitions, and underlying
ChemAgent integration without requiring actual MCP client connections.
"""

import pytest
from mcp.types import (
    ListToolsRequest,
    CallToolRequest,
    ListResourcesRequest,
    ReadResourceRequest,
    ListPromptsRequest,
    GetPromptRequest,
)


class TestMCPModule:
    """Tests for MCP module imports and availability."""
    
    def test_mcp_import(self):
        """Test MCP module can be imported."""
        from chemagent.mcp import MCP_AVAILABLE
        assert isinstance(MCP_AVAILABLE, bool)
    
    def test_mcp_available(self):
        """Test MCP SDK is available."""
        from chemagent.mcp import MCP_AVAILABLE
        assert MCP_AVAILABLE is True, "MCP SDK should be installed"
    
    def test_create_mcp_server_import(self):
        """Test create_mcp_server can be imported."""
        from chemagent.mcp import create_mcp_server
        assert callable(create_mcp_server)
    
    def test_run_mcp_server_import(self):
        """Test run_mcp_server can be imported."""
        from chemagent.mcp import run_mcp_server
        assert callable(run_mcp_server)


class TestMCPServerCreation:
    """Tests for MCP server creation and configuration."""
    
    def test_create_server(self):
        """Test server can be created."""
        from chemagent.mcp import create_mcp_server
        server = create_mcp_server()
        assert server is not None
        assert server.name == "chemagent"
    
    def test_server_has_handlers(self):
        """Test server has registered handlers."""
        from chemagent.mcp import create_mcp_server
        server = create_mcp_server()
        # Server should have tool and resource handlers
        # These are registered via decorators
        assert hasattr(server, 'request_handlers')
        assert len(server.request_handlers) > 0


class TestMCPToolDefinitions:
    """Tests for MCP tool definitions."""
    
    @pytest.fixture
    def server(self):
        """Create a server instance for testing."""
        from chemagent.mcp import create_mcp_server
        return create_mcp_server()
    
    def test_list_tools_handler_registered(self, server):
        """Test list_tools handler is registered."""
        # MCP uses request type classes as keys
        assert ListToolsRequest in server.request_handlers
    
    def test_call_tool_handler_registered(self, server):
        """Verify call_tool handler is registered."""
        assert CallToolRequest in server.request_handlers


class TestChemAgentIntegration:
    """Tests for ChemAgent integration through MCP patterns."""
    
    def test_property_calculation_via_rdkit(self):
        """Test property calculation using RDKit directly."""
        from chemagent.tools.rdkit_tools import RDKitTools
        from rdkit import Chem
        rdkit = RDKitTools()
        mol = Chem.MolFromSmiles("CCO")  # ethanol
        props = rdkit.calc_molecular_properties(mol)
        assert props is not None
        assert props.molecular_weight > 0
    
    def test_lipinski_check_via_rdkit(self):
        """Test Lipinski check using RDKit directly."""
        from chemagent.tools.rdkit_tools import RDKitTools
        from rdkit import Chem
        rdkit = RDKitTools()
        mol = Chem.MolFromSmiles("CCO")  # ethanol
        result = rdkit.calc_lipinski(mol)
        assert result is not None
        assert hasattr(result, 'passes')
        assert result.passes == True  # Ethanol should pass Lipinski
    
    def test_smiles_validation(self):
        """Test SMILES are handled correctly."""
        from chemagent.tools.rdkit_tools import RDKitTools
        from rdkit import Chem
        rdkit = RDKitTools()
        # Aspirin SMILES
        mol = Chem.MolFromSmiles("CC(=O)Oc1ccccc1C(=O)O")
        props = rdkit.calc_molecular_properties(mol)
        assert props is not None
        assert props.molecular_weight > 100  # Aspirin MW is ~180


class TestMCPAdvancedTools:
    """Tests for advanced combined MCP tools (Phase F.4)."""
    
    def test_scaffold_extraction(self):
        """Test scaffold extraction for aspirin."""
        from rdkit import Chem
        from rdkit.Chem.Scaffolds import MurckoScaffold
        
        mol = Chem.MolFromSmiles("CC(=O)Oc1ccccc1C(=O)O")  # aspirin
        core = MurckoScaffold.GetScaffoldForMol(mol)
        scaffold_smiles = Chem.MolToSmiles(core)
        assert scaffold_smiles is not None
        assert len(scaffold_smiles) > 0
    
    def test_compound_comparison(self):
        """Test compound similarity comparison."""
        from rdkit import Chem, DataStructs
        from rdkit.Chem import AllChem
        
        mol1 = Chem.MolFromSmiles("CC(=O)Oc1ccccc1C(=O)O")  # aspirin
        mol2 = Chem.MolFromSmiles("CC(C)Cc1ccc(cc1)C(C)C(=O)O")  # ibuprofen
        
        fp1 = AllChem.GetMorganFingerprintAsBitVect(mol1, 2, nBits=2048)
        fp2 = AllChem.GetMorganFingerprintAsBitVect(mol2, 2, nBits=2048)
        
        similarity = DataStructs.TanimotoSimilarity(fp1, fp2)
        assert 0 <= similarity <= 1
    
    def test_batch_properties(self):
        """Test batch property calculation."""
        from rdkit import Chem
        from chemagent.tools.rdkit_tools import RDKitTools
        
        rdkit = RDKitTools()
        smiles_list = ["CCO", "CC(=O)O", "c1ccccc1"]
        
        results = []
        for smiles in smiles_list:
            mol = Chem.MolFromSmiles(smiles)
            if mol:
                props = rdkit.calc_molecular_properties(mol)
                results.append(props)
        
        assert len(results) == 3
        assert all(r.molecular_weight > 0 for r in results)


class TestMCPResources:
    """Tests for MCP resource definitions."""
    
    @pytest.fixture
    def server(self):
        """Create a server instance for testing."""
        from chemagent.mcp import create_mcp_server
        return create_mcp_server()
    
    def test_resource_handlers_registered(self, server):
        """Test resource handlers are registered."""
        assert ListResourcesRequest in server.request_handlers
        assert ReadResourceRequest in server.request_handlers


class TestMCPPrompts:
    """Tests for MCP prompt definitions."""
    
    @pytest.fixture
    def server(self):
        """Create a server instance for testing."""
        from chemagent.mcp import create_mcp_server
        return create_mcp_server()
    
    def test_prompt_handlers_registered(self, server):
        """Test prompt handlers are registered."""
        assert ListPromptsRequest in server.request_handlers
        assert GetPromptRequest in server.request_handlers


class TestMCPServerMain:
    """Tests for MCP server main entry point."""
    
    def test_main_function_exists(self):
        """Test main function is importable."""
        from chemagent.mcp.server import main
        assert callable(main)
    
    def test_run_mcp_server_exists(self):
        """Test run_mcp_server is importable."""
        from chemagent.mcp.server import run_mcp_server
        import asyncio
        assert asyncio.iscoroutinefunction(run_mcp_server)


# Integration test that would require MCP client
@pytest.mark.skip(reason="Requires MCP client connection - for manual testing")
class TestMCPClientIntegration:
    """Integration tests requiring actual MCP client."""
    
    async def test_full_tool_call(self):
        """Test full tool call through MCP protocol."""
        pass
    
    async def test_resource_read(self):
        """Test reading resources through MCP protocol."""
        pass
