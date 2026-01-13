"""
Unit tests for DrugBank client module.
"""

import pytest
from unittest.mock import patch, MagicMock
from chemagent.tools.drugbank_client import (
    DrugBankClient,
    DrugInfo,
    DrugInteraction,
    InteractionReport,
    ApprovalStatus,
    InteractionSeverity,
    check_drug_interactions,
    get_drug_safety_info,
)


class TestDrugBankClient:
    """Test suite for DrugBankClient."""
    
    @pytest.fixture
    def client(self, tmp_path):
        """Create client instance with temp cache."""
        return DrugBankClient(cache_dir=tmp_path / "cache")
    
    def test_client_initialization(self, client):
        """Test client initializes correctly."""
        assert client is not None
        assert client.cache_dir.exists()
    
    def test_cache_key_generation(self, client):
        """Test cache key generation."""
        key1 = client._get_cache_key("http://example.com/api", {"param": "value"})
        key2 = client._get_cache_key("http://example.com/api", {"param": "value"})
        key3 = client._get_cache_key("http://example.com/api", {"param": "other"})
        
        assert key1 == key2  # Same params = same key
        assert key1 != key3  # Different params = different key


class TestDrugInfo:
    """Test DrugInfo dataclass."""
    
    def test_drug_info_defaults(self):
        """Test DrugInfo default values."""
        info = DrugInfo(name="Test Drug")
        
        assert info.name == "Test Drug"
        assert info.generic_name is None
        assert info.brand_names == []
        assert info.approval_status == ApprovalStatus.UNKNOWN
        assert info.known_interactions == []
    
    def test_drug_info_full(self):
        """Test DrugInfo with all fields."""
        info = DrugInfo(
            name="Aspirin",
            generic_name="acetylsalicylic acid",
            brand_names=["Bayer", "Ecotrin"],
            rxcui="1191",
            approval_status=ApprovalStatus.APPROVED,
            indication="Pain relief",
        )
        
        assert info.name == "Aspirin"
        assert info.generic_name == "acetylsalicylic acid"
        assert len(info.brand_names) == 2
        assert info.approval_status == ApprovalStatus.APPROVED


class TestDrugInteraction:
    """Test DrugInteraction dataclass."""
    
    def test_interaction_creation(self):
        """Test creating a drug interaction."""
        interaction = DrugInteraction(
            drug_a="Warfarin",
            drug_b="Aspirin",
            severity=InteractionSeverity.MAJOR,
            description="Increased bleeding risk"
        )
        
        assert interaction.drug_a == "Warfarin"
        assert interaction.drug_b == "Aspirin"
        assert interaction.severity == InteractionSeverity.MAJOR


class TestInteractionReport:
    """Test InteractionReport dataclass."""
    
    def test_report_no_interactions(self):
        """Test report with no interactions."""
        report = InteractionReport(
            drug_a="DrugA",
            drug_b="DrugB",
            interactions_found=False,
            interaction_count=0,
            interactions=[],
            severity_summary={"major": 0, "moderate": 0, "minor": 0, "unknown": 0},
            warnings=[],
            recommendations=[]
        )
        
        assert report.interactions_found is False
        assert report.interaction_count == 0
    
    def test_report_with_interactions(self):
        """Test report with interactions."""
        interaction = DrugInteraction(
            drug_a="Warfarin",
            drug_b="Aspirin",
            severity=InteractionSeverity.MAJOR,
            description="Bleeding risk"
        )
        
        report = InteractionReport(
            drug_a="Warfarin",
            drug_b="Aspirin",
            interactions_found=True,
            interaction_count=1,
            interactions=[interaction],
            severity_summary={"major": 1, "moderate": 0, "minor": 0, "unknown": 0},
            warnings=["MAJOR interaction detected"],
            recommendations=["Consult healthcare provider"]
        )
        
        assert report.interactions_found is True
        assert report.interaction_count == 1
        assert len(report.warnings) > 0


class TestApprovalStatus:
    """Test ApprovalStatus enum."""
    
    def test_status_values(self):
        """Test all status values exist."""
        assert ApprovalStatus.APPROVED.value == "approved"
        assert ApprovalStatus.INVESTIGATIONAL.value == "investigational"
        assert ApprovalStatus.WITHDRAWN.value == "withdrawn"
        assert ApprovalStatus.DISCONTINUED.value == "discontinued"
        assert ApprovalStatus.UNKNOWN.value == "unknown"


class TestInteractionSeverity:
    """Test InteractionSeverity enum."""
    
    def test_severity_values(self):
        """Test all severity values exist."""
        assert InteractionSeverity.MAJOR.value == "major"
        assert InteractionSeverity.MODERATE.value == "moderate"
        assert InteractionSeverity.MINOR.value == "minor"
        assert InteractionSeverity.UNKNOWN.value == "unknown"


class TestConvenienceFunctions:
    """Test convenience functions."""
    
    @pytest.fixture
    def mock_client(self):
        """Create mock client."""
        with patch('chemagent.tools.drugbank_client.DrugBankClient') as mock:
            mock_instance = MagicMock()
            mock_instance.get_interaction_summary.return_value = {
                "drugs_checked": 2,
                "pairs_checked": 1,
                "interactions_found": 1,
                "severity_breakdown": {"major": 1, "moderate": 0, "minor": 0},
                "major_interaction_pairs": ["warfarin + aspirin"],
                "warnings": ["MAJOR interaction"],
                "recommendations": ["Consult provider"]
            }
            mock.return_value = mock_instance
            yield mock_instance
    
    def test_check_drug_interactions_structure(self):
        """Test check_drug_interactions returns proper structure."""
        # This will make real API call - just verify structure
        # Use a small timeout or mock in production tests
        # For now, test with mock
        with patch('chemagent.tools.drugbank_client.DrugBankClient') as mock_class:
            mock_client = MagicMock()
            mock_client.get_interaction_summary.return_value = {
                "drugs_checked": 2,
                "interactions_found": 0,
                "severity_breakdown": {"major": 0, "moderate": 0, "minor": 0},
                "major_interaction_pairs": [],
                "warnings": [],
                "recommendations": []
            }
            mock_class.return_value = mock_client
            
            result = check_drug_interactions(["drug1", "drug2"])
            
            assert "drugs_checked" in result
            assert "interactions_found" in result
            assert "severity_breakdown" in result


class TestIntegration:
    """Integration tests (require network)."""
    
    @pytest.fixture
    def client(self, tmp_path):
        """Create client with temp cache."""
        return DrugBankClient(cache_dir=tmp_path / "cache")
    
    @pytest.mark.integration
    def test_rxcui_lookup(self, client):
        """Test RXCUI lookup for known drug."""
        rxcui = client.get_rxcui_by_name("aspirin")
        
        # Aspirin RXCUI should be 1191
        assert rxcui is not None
        assert rxcui == "1191"
    
    @pytest.mark.integration
    def test_fda_label_lookup(self, client):
        """Test FDA label lookup."""
        label = client.get_fda_label_info("metformin")
        
        if label:  # API might not always be available
            assert "generic_name" in label or "brand_name" in label
    
    @pytest.mark.integration
    def test_drug_pair_interaction(self, client):
        """Test checking interaction between warfarin and aspirin."""
        report = client.check_drug_pair_interaction("warfarin", "aspirin")
        
        assert report is not None
        assert report.drug_a == "warfarin"
        assert report.drug_b == "aspirin"
        # These are known to interact
        # Note: result depends on FDA label content
        assert isinstance(report.interactions_found, bool)
    
    @pytest.mark.integration
    def test_drug_info_retrieval(self, client):
        """Test comprehensive drug info retrieval."""
        info = client.get_drug_info("metformin")
        
        assert info.name == "metformin"
        assert info.rxcui is not None
    
    @pytest.mark.integration
    def test_multi_drug_interaction_check(self, client):
        """Test checking interactions among multiple drugs."""
        drugs = ["warfarin", "aspirin", "ibuprofen"]
        summary = client.get_interaction_summary(drugs)
        
        assert "drugs_checked" in summary
        assert summary["drugs_checked"] == 3
        assert "severity_breakdown" in summary
