"""
BindingDB Client
================

Wrapper for BindingDB API with caching and provenance tracking.

BindingDB provides binding affinity data for protein-ligand interactions.

Example:
    >>> from chemagent.tools.bindingdb_client import BindingDBClient
    >>> client = BindingDBClient()
    >>> results = client.search_by_target("COX-2")
"""

import time
import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import xml.etree.ElementTree as ET

import requests
from diskcache import Cache

from .rdkit_tools import Provenance


logger = logging.getLogger(__name__)


# =============================================================================
# Result Classes
# =============================================================================

@dataclass
class AffinityResult:
    """Binding affinity result."""
    bindingdb_id: str
    target_name: str
    target_source_organism: Optional[str]
    ligand_smiles: Optional[str]
    ligand_inchi: Optional[str]
    ic50_nm: Optional[float]  # IC50 in nM
    ki_nm: Optional[float]    # Ki in nM
    kd_nm: Optional[float]    # Kd in nM
    ec50_nm: Optional[float]  # EC50 in nM
    ph: Optional[float]
    temp_c: Optional[float]
    provenance: Optional[Provenance] = None


# =============================================================================
# BindingDB Client
# =============================================================================

class BindingDBClient:
    """
    BindingDB API client with caching and retry logic.
    
    Features:
    - Search by target name or UniProt ID
    - Get affinity data for compounds
    - Disk caching (24h TTL)
    - Rate limiting
    - Provenance tracking
    
    Example:
        >>> client = BindingDBClient()
        >>> 
        >>> # Search by target
        >>> results = client.search_by_target("COX-2", limit=10)
        >>> 
        >>> # Get affinity data for compound
        >>> affinities = client.get_affinity_data("aspirin")
    """
    
    BASE_URL = "https://bindingdb.org/axis2/services/BDBService"
    
    def __init__(
        self,
        cache_dir: str = ".cache/bindingdb",
        cache_ttl: int = 86400,  # 24 hours
        rate_limit: float = 1.0,  # 1 request per second (conservative)
        max_retries: int = 3,
        timeout: int = 30,
    ):
        """
        Initialize BindingDB client.
        
        Args:
            cache_dir: Directory for disk cache
            cache_ttl: Cache time-to-live in seconds
            rate_limit: Max requests per second
            max_retries: Max retry attempts
            timeout: Request timeout in seconds
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache = Cache(str(self.cache_dir))
        self.cache_ttl = cache_ttl
        
        # Rate limiting
        self.rate_limit = rate_limit
        self.min_interval = 1.0 / rate_limit
        self.last_request_time = 0.0
        
        # Retry settings
        self.max_retries = max_retries
        self.retry_delay = 1.0
        self.timeout = timeout
        
        logger.info(f"BindingDB client initialized with cache at {cache_dir}")
    
    def _rate_limit_wait(self):
        """Enforce rate limiting."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_request_time = time.time()
    
    def _retry_request(self, func, *args, **kwargs) -> Any:
        """Execute function with exponential backoff retry."""
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                self._rate_limit_wait()
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2 ** attempt)
                    logger.warning(
                        f"Request failed (attempt {attempt + 1}/{self.max_retries}): {e}. "
                        f"Retrying in {delay}s..."
                    )
                    time.sleep(delay)
                else:
                    logger.error(f"All {self.max_retries} attempts failed: {e}")
        
        if last_exception is not None:
            raise last_exception
        raise RuntimeError("Request failed after all retries")
    
    def _create_provenance(self, method: str, **params) -> Provenance:
        """Create provenance record."""
        return Provenance(
            source="bindingdb",
            source_version="2024.01",
            timestamp=datetime.now().isoformat(),
            method=method,
            parameters=params,
        )
    
    def _parse_xml_response(self, xml_text: str) -> List[Dict[str, Any]]:
        """Parse XML response from BindingDB."""
        try:
            root = ET.fromstring(xml_text)
            results = []
            
            for affinity in root.findall('.//affinities'):
                result = {}
                for child in affinity:
                    tag = child.tag.replace('{http://ws.bindingdb.org/xsd}', '')
                    result[tag] = child.text
                results.append(result)
            
            return results
        except ET.ParseError as e:
            logger.error(f"Failed to parse XML: {e}")
            return []
    
    def search_by_target(
        self,
        target_name: str,
        limit: int = 100,
    ) -> List[AffinityResult]:
        """
        Search binding data by target name.
        
        Args:
            target_name: Target protein name (e.g., "COX-2", "EGFR")
            limit: Maximum results to return
            
        Returns:
            List of binding affinity results
            
        Example:
            >>> client = BindingDBClient()
            >>> results = client.search_by_target("COX-2", limit=20)
            >>> for r in results:
            ...     if r.ic50_nm:
            ...         print(f"{r.ligand_smiles}: IC50 = {r.ic50_nm:.2f} nM")
        """
        cache_key = f"target:{target_name}:{limit}"
        
        # Check cache
        if cache_key in self.cache:
            logger.debug(f"Cache hit for search_by_target({target_name})")
            return self.cache[cache_key]
        
        logger.info(f"Searching BindingDB for target: {target_name}")
        
        # Make request
        def _search():
            # BindingDB REST API endpoint
            url = f"{self.BASE_URL}/getTargetByName"
            params = {
                'target': target_name,
                'response': 'application/xml',
            }
            
            response = requests.get(
                url,
                params=params,
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.text
        
        try:
            xml_response = self._retry_request(_search)
            raw_results = self._parse_xml_response(xml_response)
        except Exception as e:
            logger.error(f"BindingDB search failed: {e}")
            return []
        
        # Convert to AffinityResult
        affinities = []
        provenance = self._create_provenance("search_by_target", target_name=target_name, limit=limit)
        
        for data in raw_results[:limit]:
            affinity = AffinityResult(
                bindingdb_id=data.get('BindingDB_ID', ''),
                target_name=data.get('Target_Name', target_name),
                target_source_organism=data.get('Target_Source_Organism'),
                ligand_smiles=data.get('Ligand_SMILES'),
                ligand_inchi=data.get('Ligand_InChI'),
                ic50_nm=self._parse_float(data.get('IC50_(nM)')),
                ki_nm=self._parse_float(data.get('Ki_(nM)')),
                kd_nm=self._parse_float(data.get('Kd_(nM)')),
                ec50_nm=self._parse_float(data.get('EC50_(nM)')),
                ph=self._parse_float(data.get('pH')),
                temp_c=self._parse_float(data.get('Temp_(C)')),
                provenance=provenance,
            )
            affinities.append(affinity)
        
        # Cache results
        self.cache.set(cache_key, affinities, expire=self.cache_ttl)
        
        logger.info(f"Found {len(affinities)} binding affinities for {target_name}")
        return affinities
    
    def get_affinity_data(
        self,
        compound_name: str,
        limit: int = 50,
    ) -> List[AffinityResult]:
        """
        Get binding affinities for a compound.
        
        Args:
            compound_name: Compound name or identifier
            limit: Maximum results to return
            
        Returns:
            List of binding affinity results
            
        Example:
            >>> client = BindingDBClient()
            >>> results = client.get_affinity_data("imatinib")
            >>> print(f"Found {len(results)} targets")
        """
        cache_key = f"compound:{compound_name}:{limit}"
        
        # Check cache
        if cache_key in self.cache:
            logger.debug(f"Cache hit for get_affinity_data({compound_name})")
            return self.cache[cache_key]
        
        logger.info(f"Fetching affinity data for: {compound_name}")
        
        # Make request
        def _fetch():
            url = f"{self.BASE_URL}/getLigandByName"
            params = {
                'ligand': compound_name,
                'response': 'application/xml',
            }
            
            response = requests.get(
                url,
                params=params,
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.text
        
        try:
            xml_response = self._retry_request(_fetch)
            raw_results = self._parse_xml_response(xml_response)
        except Exception as e:
            logger.error(f"BindingDB fetch failed: {e}")
            return []
        
        # Convert to AffinityResult
        affinities = []
        provenance = self._create_provenance("get_affinity_data", compound_name=compound_name, limit=limit)
        
        for data in raw_results[:limit]:
            affinity = AffinityResult(
                bindingdb_id=data.get('BindingDB_ID', ''),
                target_name=data.get('Target_Name', ''),
                target_source_organism=data.get('Target_Source_Organism'),
                ligand_smiles=data.get('Ligand_SMILES'),
                ligand_inchi=data.get('Ligand_InChI'),
                ic50_nm=self._parse_float(data.get('IC50_(nM)')),
                ki_nm=self._parse_float(data.get('Ki_(nM)')),
                kd_nm=self._parse_float(data.get('Kd_(nM)')),
                ec50_nm=self._parse_float(data.get('EC50_(nM)')),
                ph=self._parse_float(data.get('pH')),
                temp_c=self._parse_float(data.get('Temp_(C)')),
                provenance=provenance,
            )
            affinities.append(affinity)
        
        # Cache results
        self.cache.set(cache_key, affinities, expire=self.cache_ttl)
        
        logger.info(f"Found {len(affinities)} affinity records for {compound_name}")
        return affinities
    
    @staticmethod
    def _parse_float(value: Optional[str]) -> Optional[float]:
        """Parse float from string, handling None and errors."""
        if value is None or value == '':
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def clear_cache(self):
        """Clear all cached data."""
        self.cache.clear()
        logger.info("Cache cleared")


if __name__ == "__main__":
    # Demo usage
    logging.basicConfig(level=logging.INFO)
    
    client = BindingDBClient()
    
    print("\n=== Search by target ===")
    results = client.search_by_target("COX-2", limit=5)
    for r in results[:3]:
        if r.ic50_nm:
            print(f"IC50: {r.ic50_nm:.2f} nM")
