"""
Tests for ChEMBL Client
=======================

Unit tests for ChEMBL database client.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile
import time

from chemagent.tools.chembl_client import (
    ChEMBLClient,
    CompoundResult,
    ActivityResult,
    TargetInfo,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def temp_cache_dir():
    """Create temporary cache directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def client(temp_cache_dir):
    """Create ChEMBL client with temporary cache."""
    return ChEMBLClient(cache_dir=temp_cache_dir, rate_limit=100.0)


@pytest.fixture
def mock_molecule_data():
    """Mock molecule data from ChEMBL API."""
    return {
        'molecule_chembl_id': 'CHEMBL25',
        'molecule_structures': {
            'canonical_smiles': 'CC(=O)Oc1ccccc1C(=O)O',
            'standard_inchi': 'InChI=1S/C9H8O4/c1-6(10)13-8-5-3-2-4-7(8)9(11)12/h2-5H,1H3,(H,11,12)',
            'standard_inchi_key': 'BSYNRYMUTXBXSQ-UHFFFAOYSA-N',
        },
        'molecule_properties': {
            'full_molformula': 'C9H8O4',
            'full_mwt': 180.16,
            'alogp': 1.19,
            'psa': 63.6,
        },
        'molecule_synonyms': [
            {'molecule_synonym': 'Aspirin'},
            {'molecule_synonym': 'Acetylsalicylic acid'},
        ],
    }


@pytest.fixture
def mock_activity_data():
    """Mock activity data from ChEMBL API."""
    return {
        'activity_id': 12345,
        'molecule_chembl_id': 'CHEMBL25',
        'target_chembl_id': 'CHEMBL2035',
        'target_pref_name': 'Cyclooxygenase-2',
        'assay_type': 'B',
        'standard_type': 'IC50',
        'standard_value': 100.0,
        'standard_units': 'nM',
        'pchembl_value': 7.0,
        'activity_comment': 'Active',
    }


@pytest.fixture
def mock_target_data():
    """Mock target data from ChEMBL API."""
    return {
        'target_chembl_id': 'CHEMBL2035',
        'target_type': 'SINGLE PROTEIN',
        'pref_name': 'Cyclooxygenase-2',
        'organism': 'Homo sapiens',
        'target_components': [],
    }


# =============================================================================
# Test Client Initialization
# =============================================================================

class TestClientInitialization:
    """Test client initialization."""
    
    def test_init_default(self):
        """Test default initialization."""
        client = ChEMBLClient()
        
        assert client.cache_dir.exists()
        assert client.cache_ttl == 86400
        assert client.rate_limit == 10.0
        assert client.max_retries == 3
    
    def test_init_custom(self, temp_cache_dir):
        """Test custom initialization."""
        client = ChEMBLClient(
            cache_dir=temp_cache_dir,
            cache_ttl=3600,
            rate_limit=5.0,
            max_retries=5,
        )
        
        assert str(client.cache_dir) == temp_cache_dir
        assert client.cache_ttl == 3600
        assert client.rate_limit == 5.0
        assert client.max_retries == 5


# =============================================================================
# Test Rate Limiting
# =============================================================================

class TestRateLimiting:
    """Test rate limiting functionality."""
    
    def test_rate_limit_enforcement(self, client):
        """Test that rate limiting delays requests."""
        client.rate_limit = 2.0  # 2 requests per second
        client.min_interval = 0.5  # 500ms between requests
        
        start = time.time()
        
        # Make 3 quick calls
        for _ in range(3):
            client._rate_limit_wait()
        
        elapsed = time.time() - start
        
        # Should take at least 1 second (2 * 0.5s intervals)
        assert elapsed >= 1.0


# =============================================================================
# Test Caching
# =============================================================================

class TestCaching:
    """Test caching functionality."""
    
    def test_cache_hit(self, client):
        """Test that cache returns cached results."""
        # Manually add to cache
        test_data = [CompoundResult(
            chembl_id='CHEMBL25',
            smiles='CCO',
            standard_inchi=None,
            standard_inchi_key=None,
            molecular_formula='C2H6O',
            molecular_weight=46.07,
            alogp=None,
            psa=None,
        )]
        
        cache_key = "test_key"
        client.cache.set(cache_key, test_data, expire=60)
        
        # Retrieve from cache
        assert cache_key in client.cache
        cached = client.cache[cache_key]
        assert cached == test_data
    
    def test_cache_expiry(self, client):
        """Test that cache expires after TTL."""
        cache_key = "expire_test"
        test_data = "test_value"
        
        # Set with 1 second TTL
        client.cache.set(cache_key, test_data, expire=1)
        assert cache_key in client.cache
        
        # Wait for expiry
        time.sleep(1.1)
        assert cache_key not in client.cache


# =============================================================================
# Test Search by Name
# =============================================================================

class TestSearchByName:
    """Test search_by_name functionality."""
    
    def test_search_by_name_success(self, client, mock_molecule_data):
        """Test successful search by name."""
        # Mock the ChEMBL API
        with patch.object(client.molecule, 'filter') as mock_filter:
            mock_result = MagicMock()
            mock_result.__getitem__.return_value = [mock_molecule_data]
            mock_filter.return_value.only.return_value = mock_result
            
            results = client.search_by_name("aspirin", limit=1)
            
            assert len(results) == 1
            assert results[0].chembl_id == 'CHEMBL25'
            assert results[0].smiles == 'CC(=O)Oc1ccccc1C(=O)O'
            assert results[0].molecular_weight == 180.16
            assert results[0].provenance is not None
            assert results[0].provenance.source == "chembl"
            assert results[0].provenance.method == "search_by_name"
    
    def test_search_by_name_caching(self, client, mock_molecule_data):
        """Test that search results are cached."""
        with patch.object(client.molecule, 'filter') as mock_filter:
            mock_result = MagicMock()
            mock_result.__getitem__.return_value = [mock_molecule_data]
            mock_filter.return_value.only.return_value = mock_result
            
            # First call - should hit API
            results1 = client.search_by_name("aspirin", limit=1)
            assert mock_filter.call_count == 1
            
            # Second call - should hit cache
            results2 = client.search_by_name("aspirin", limit=1)
            assert mock_filter.call_count == 1  # No additional API call
            
            # Results should be identical
            assert results1[0].chembl_id == results2[0].chembl_id
    
    def test_search_by_name_empty_results(self, client):
        """Test search with no results."""
        with patch.object(client.molecule, 'filter') as mock_filter:
            mock_result = MagicMock()
            mock_result.__getitem__.return_value = []
            mock_filter.return_value.only.return_value = mock_result
            
            results = client.search_by_name("nonexistent_compound")
            
            assert len(results) == 0


# =============================================================================
# Test Get Compound
# =============================================================================

class TestGetCompound:
    """Test get_compound functionality."""
    
    def test_get_compound_success(self, client, mock_molecule_data):
        """Test successful compound retrieval."""
        with patch.object(client.molecule, 'filter') as mock_filter:
            mock_filter.return_value = [mock_molecule_data]
            
            compound = client.get_compound("CHEMBL25")
            
            assert compound is not None
            assert compound.chembl_id == 'CHEMBL25'
            assert compound.molecular_formula == 'C9H8O4'
            assert compound.provenance.method == "get_compound"
    
    def test_get_compound_not_found(self, client):
        """Test compound not found."""
        with patch.object(client.molecule, 'filter') as mock_filter:
            mock_filter.return_value = []
            
            compound = client.get_compound("CHEMBL999999")
            
            assert compound is None
    
    def test_get_compound_caching(self, client, mock_molecule_data):
        """Test compound results are cached."""
        with patch.object(client.molecule, 'filter') as mock_filter:
            mock_filter.return_value = [mock_molecule_data]
            
            # First call
            compound1 = client.get_compound("CHEMBL25")
            assert mock_filter.call_count == 1
            
            # Second call - should use cache
            compound2 = client.get_compound("CHEMBL25")
            assert mock_filter.call_count == 1
            
            assert compound1.chembl_id == compound2.chembl_id


# =============================================================================
# Test Similarity Search
# =============================================================================

class TestSimilaritySearch:
    """Test similarity_search functionality."""
    
    def test_similarity_search_success(self, client, mock_molecule_data):
        """Test successful similarity search."""
        with patch.object(client.molecule, 'filter') as mock_filter:
            mock_result = MagicMock()
            mock_result.__getitem__.return_value = [mock_molecule_data]
            mock_filter.return_value.only.return_value = mock_result
            
            results = client.similarity_search("CCO", threshold=0.7, limit=10)
            
            assert len(results) == 1
            assert results[0].chembl_id == 'CHEMBL25'
            assert results[0].provenance.method == "similarity_search"
            assert results[0].provenance.parameters['threshold'] == 0.7
    
    def test_similarity_search_error_handling(self, client):
        """Test similarity search error handling."""
        with patch.object(client.molecule, 'filter') as mock_filter:
            mock_filter.side_effect = Exception("API Error")
            
            results = client.similarity_search("CCO")
            
            # Should return empty list on error
            assert len(results) == 0


# =============================================================================
# Test Get Activities
# =============================================================================

class TestGetActivities:
    """Test get_activities functionality."""
    
    def test_get_activities_success(self, client, mock_activity_data):
        """Test successful activity retrieval."""
        with patch.object(client.activity, 'filter') as mock_filter:
            mock_result = MagicMock()
            mock_result.__getitem__.return_value = [mock_activity_data]
            mock_filter.return_value.filter.return_value.only.return_value = mock_result
            
            activities = client.get_activities("CHEMBL25", target_type="SINGLE PROTEIN")
            
            assert len(activities) == 1
            assert activities[0].chembl_id == 'CHEMBL25'
            assert activities[0].target_name == 'Cyclooxygenase-2'
            assert activities[0].standard_type == 'IC50'
            assert activities[0].standard_value == 100.0
            assert activities[0].provenance.method == "get_activities"
    
    def test_get_activities_without_filter(self, client, mock_activity_data):
        """Test activity retrieval without target type filter."""
        with patch.object(client.activity, 'filter') as mock_filter:
            mock_result = MagicMock()
            mock_result.__getitem__.return_value = [mock_activity_data]
            mock_filter.return_value.only.return_value = mock_result
            
            activities = client.get_activities("CHEMBL25")
            
            assert len(activities) == 1


# =============================================================================
# Test Get Target Info
# =============================================================================

class TestGetTargetInfo:
    """Test get_target_info functionality."""
    
    def test_get_target_info_success(self, client, mock_target_data):
        """Test successful target retrieval."""
        with patch.object(client.target, 'filter') as mock_filter:
            mock_filter.return_value = [mock_target_data]
            
            target = client.get_target_info("CHEMBL2035")
            
            assert target is not None
            assert target.target_chembl_id == 'CHEMBL2035'
            assert target.pref_name == 'Cyclooxygenase-2'
            assert target.organism == 'Homo sapiens'
            assert target.provenance.method == "get_target_info"
    
    def test_get_target_info_not_found(self, client):
        """Test target not found."""
        with patch.object(client.target, 'filter') as mock_filter:
            mock_filter.return_value = []
            
            target = client.get_target_info("CHEMBL999999")
            
            assert target is None


# =============================================================================
# Test Retry Logic
# =============================================================================

class TestRetryLogic:
    """Test retry logic."""
    
    def test_retry_on_failure(self, client):
        """Test that requests are retried on failure."""
        attempt_count = 0
        
        def failing_func():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise Exception("Temporary failure")
            return "success"
        
        result = client._retry_request(failing_func)
        
        assert result == "success"
        assert attempt_count == 3
    
    def test_max_retries_exceeded(self, client):
        """Test that exception is raised after max retries."""
        def always_failing():
            raise Exception("Permanent failure")
        
        with pytest.raises(Exception, match="Permanent failure"):
            client._retry_request(always_failing)


# =============================================================================
# Test Provenance
# =============================================================================

class TestProvenance:
    """Test provenance tracking."""
    
    def test_provenance_creation(self, client):
        """Test provenance record creation."""
        provenance = client._create_provenance(
            "test_method",
            param1="value1",
            param2=42,
        )
        
        assert provenance.source == "chembl"
        assert provenance.source_version == "30"
        assert provenance.method == "test_method"
        assert provenance.parameters == {"param1": "value1", "param2": 42}
        assert provenance.timestamp is not None
    
    def test_all_results_have_provenance(self, client, mock_molecule_data):
        """Test that all results include provenance."""
        with patch.object(client.molecule, 'filter') as mock_filter:
            mock_result = MagicMock()
            mock_result.__getitem__.return_value = [mock_molecule_data]
            mock_filter.return_value.only.return_value = mock_result
            
            results = client.search_by_name("test")
            
            assert all(r.provenance is not None for r in results)
            assert all(r.provenance.source == "chembl" for r in results)


# =============================================================================
# Test Cache Management
# =============================================================================

class TestCacheManagement:
    """Test cache management."""
    
    def test_clear_cache(self, client):
        """Test cache clearing."""
        # Add something to cache
        client.cache.set("test_key", "test_value")
        assert "test_key" in client.cache
        
        # Clear cache
        client.clear_cache()
        assert "test_key" not in client.cache


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
