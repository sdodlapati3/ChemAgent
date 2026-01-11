"""
UniProt Client
==============

Wrapper for UniProt API with caching and provenance tracking.

UniProt provides protein sequence and functional information.

Example:
    >>> from chemagent.tools.uniprot_client import UniProtClient
    >>> client = UniProtClient()
    >>> protein = client.get_protein_info("P35354")
"""

import time
import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import requests
from diskcache import Cache

from .rdkit_tools import Provenance


logger = logging.getLogger(__name__)


# =============================================================================
# Result Classes
# =============================================================================

@dataclass
class ProteinInfo:
    """Protein information."""
    uniprot_id: str
    entry_name: str
    protein_name: str
    gene_names: List[str] = field(default_factory=list)
    organism: str = ""
    organism_id: int = 0
    sequence: str = ""
    sequence_length: int = 0
    function_description: Optional[str] = None
    subcellular_location: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    pdb_ids: List[str] = field(default_factory=list)
    provenance: Optional[Provenance] = None


# =============================================================================
# UniProt Client
# =============================================================================

class UniProtClient:
    """
    UniProt API client with caching and retry logic.
    
    Features:
    - Get protein information by UniProt ID
    - Search proteins by name or gene
    - Disk caching (24h TTL)
    - Rate limiting
    - Provenance tracking
    
    Example:
        >>> client = UniProtClient()
        >>> 
        >>> # Get protein info
        >>> protein = client.get_protein_info("P35354")
        >>> print(f"{protein.protein_name} ({protein.organism})")
        >>> 
        >>> # Search proteins
        >>> results = client.search_proteins("cyclooxygenase-2")
    """
    
    BASE_URL = "https://rest.uniprot.org"
    
    def __init__(
        self,
        cache_dir: str = ".cache/uniprot",
        cache_ttl: int = 86400,  # 24 hours
        rate_limit: float = 1.0,  # 1 request per second (conservative)
        max_retries: int = 3,
        timeout: int = 30,
    ):
        """
        Initialize UniProt client.
        
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
        
        logger.info(f"UniProt client initialized with cache at {cache_dir}")
    
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
        raise RuntimeError(f"Failed to execute request after {self.max_retries} attempts")
    
    def _create_provenance(self, method: str, **params) -> Provenance:
        """Create provenance record."""
        return Provenance(
            source="uniprot",
            source_version="2024.01",
            timestamp=datetime.now().isoformat(),
            method=method,
            parameters=params,
        )
    
    def get_protein_info(self, uniprot_id: str) -> Optional[ProteinInfo]:
        """
        Get protein information by UniProt ID.
        
        Args:
            uniprot_id: UniProt accession ID (e.g., "P35354")
            
        Returns:
            Protein information or None if not found
            
        Example:
            >>> client = UniProtClient()
            >>> protein = client.get_protein_info("P35354")
            >>> print(f"Protein: {protein.protein_name}")
            >>> print(f"Organism: {protein.organism}")
            >>> print(f"Sequence length: {protein.sequence_length}")
        """
        cache_key = f"protein:{uniprot_id}"
        
        # Check cache
        if cache_key in self.cache:
            logger.debug(f"Cache hit for get_protein_info({uniprot_id})")
            return self.cache[cache_key]
        
        logger.info(f"Fetching protein: {uniprot_id}")
        
        # Make request
        def _fetch():
            url = f"{self.BASE_URL}/uniprotkb/{uniprot_id}.json"
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        
        try:
            data = self._retry_request(_fetch)
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                logger.warning(f"Protein {uniprot_id} not found")
                return None
            raise
        except Exception as e:
            logger.error(f"UniProt fetch failed: {e}")
            return None
        
        # Parse response
        provenance = self._create_provenance("get_protein_info", uniprot_id=uniprot_id)
        
        # Extract gene names
        gene_names = []
        if 'genes' in data:
            for gene in data['genes']:
                if 'geneName' in gene:
                    gene_names.append(gene['geneName']['value'])
        
        # Extract function description
        function_desc = None
        if 'comments' in data:
            for comment in data['comments']:
                if comment.get('commentType') == 'FUNCTION':
                    function_desc = comment.get('texts', [{}])[0].get('value')
                    break
        
        # Extract subcellular location
        subcellular_loc = []
        if 'comments' in data:
            for comment in data['comments']:
                if comment.get('commentType') == 'SUBCELLULAR LOCATION':
                    for loc in comment.get('subcellularLocations', []):
                        if 'location' in loc:
                            subcellular_loc.append(loc['location']['value'])
        
        # Extract keywords
        keywords = []
        if 'keywords' in data:
            keywords = [kw['name'] for kw in data['keywords']]
        
        # Extract PDB IDs
        pdb_ids = []
        if 'uniProtKBCrossReferences' in data:
            for ref in data['uniProtKBCrossReferences']:
                if ref.get('database') == 'PDB':
                    pdb_ids.append(ref['id'])
        
        # Extract sequence
        sequence = ""
        sequence_length = 0
        if 'sequence' in data:
            sequence = data['sequence'].get('value', '')
            sequence_length = data['sequence'].get('length', 0)
        
        protein = ProteinInfo(
            uniprot_id=data['primaryAccession'],
            entry_name=data.get('uniProtkbId', ''),
            protein_name=data.get('proteinDescription', {}).get('recommendedName', {}).get('fullName', {}).get('value', ''),
            gene_names=gene_names,
            organism=data.get('organism', {}).get('scientificName', ''),
            organism_id=data.get('organism', {}).get('taxonId', 0),
            sequence=sequence,
            sequence_length=sequence_length,
            function_description=function_desc,
            subcellular_location=subcellular_loc,
            keywords=keywords,
            pdb_ids=pdb_ids,
            provenance=provenance,
        )
        
        # Cache result
        self.cache.set(cache_key, protein, expire=self.cache_ttl)
        
        return protein
    
    def search_proteins(
        self,
        query: str,
        limit: int = 20,
        reviewed_only: bool = True,
    ) -> List[ProteinInfo]:
        """
        Search proteins by name, gene, or keyword.
        
        Args:
            query: Search query (protein name, gene name, etc.)
            limit: Maximum results to return
            reviewed_only: Only return reviewed (Swiss-Prot) entries
            
        Returns:
            List of protein information
            
        Example:
            >>> client = UniProtClient()
            >>> results = client.search_proteins("cyclooxygenase")
            >>> for p in results:
            ...     print(f"{p.uniprot_id}: {p.protein_name} ({p.organism})")
        """
        cache_key = f"search:{query}:{limit}:{reviewed_only}"
        
        # Check cache
        if cache_key in self.cache:
            logger.debug(f"Cache hit for search_proteins({query})")
            return self.cache[cache_key]
        
        logger.info(f"Searching UniProt for: {query}")
        
        # Validate query
        if not query or not query.strip():
            logger.warning("Empty query provided to search_proteins")
            return []
        
        # Make request
        def _search():
            url = f"{self.BASE_URL}/uniprotkb/search"
            
            # Build query
            search_query = query.strip()
            if reviewed_only:
                search_query += " AND (reviewed:true)"
            
            params = {
                'query': search_query,
                'format': 'json',
                'size': limit,
            }
            
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        
        try:
            data = self._retry_request(_search)
        except Exception as e:
            logger.error(f"UniProt search failed: {e}")
            return []
        
        # Parse results
        proteins = []
        provenance = self._create_provenance(
            "search_proteins",
            query=query,
            limit=limit,
            reviewed_only=reviewed_only,
        )
        
        for entry in data.get('results', []):
            # Extract gene names
            gene_names = []
            if 'genes' in entry:
                for gene in entry['genes']:
                    if 'geneName' in gene:
                        gene_names.append(gene['geneName']['value'])
            
            # Extract keywords
            keywords = []
            if 'keywords' in entry:
                keywords = [kw['name'] for kw in entry['keywords']]
            
            # Extract sequence info
            sequence = ""
            sequence_length = 0
            if 'sequence' in entry:
                sequence = entry['sequence'].get('value', '')
                sequence_length = entry['sequence'].get('length', 0)
            
            protein = ProteinInfo(
                uniprot_id=entry['primaryAccession'],
                entry_name=entry.get('uniProtkbId', ''),
                protein_name=entry.get('proteinDescription', {}).get('recommendedName', {}).get('fullName', {}).get('value', ''),
                gene_names=gene_names,
                organism=entry.get('organism', {}).get('scientificName', ''),
                organism_id=entry.get('organism', {}).get('taxonId', 0),
                sequence=sequence,
                sequence_length=sequence_length,
                keywords=keywords,
                provenance=provenance,
            )
            proteins.append(protein)
        
        # Cache results
        self.cache.set(cache_key, proteins, expire=self.cache_ttl)
        
        logger.info(f"Found {len(proteins)} proteins for '{query}'")
        return proteins
    
    def clear_cache(self):
        """Clear all cached data."""
        self.cache.clear()
        logger.info("Cache cleared")


if __name__ == "__main__":
    # Demo usage
    logging.basicConfig(level=logging.INFO)
    
    client = UniProtClient()
    
    # Get protein info
    print("\n=== Get protein info ===")
    protein = client.get_protein_info("P35354")  # COX-2
    if protein:
        print(f"Protein: {protein.protein_name}")
        print(f"Organism: {protein.organism}")
        print(f"Sequence length: {protein.sequence_length}")
        print(f"PDB entries: {len(protein.pdb_ids)}")
    
    # Search proteins
    print("\n=== Search proteins ===")
    results = client.search_proteins("cyclooxygenase", limit=5)
    for p in results:
        print(f"{p.uniprot_id}: {p.protein_name} ({p.organism})")
