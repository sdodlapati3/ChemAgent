"""
PubMed client for retrieving scientific literature.

This module provides access to PubMed/NCBI databases through the E-utilities API,
enabling retrieval of scientific papers relevant to drug discovery queries.

Features:
- Search PubMed by keyword, compound, target, or disease
- Retrieve article abstracts and metadata
- Support for advanced search queries (MeSH terms, filters)
- Automatic caching to reduce API calls
- Rate limiting for API compliance
"""

import json
import logging
import hashlib
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from pathlib import Path
from datetime import datetime
import time
import re

import requests

logger = logging.getLogger(__name__)


# =============================================================================
# Data Models
# =============================================================================

@dataclass
class Author:
    """Author information."""
    last_name: str
    first_name: Optional[str] = None
    initials: Optional[str] = None
    affiliation: Optional[str] = None
    
    @property
    def full_name(self) -> str:
        """Get formatted full name."""
        if self.first_name:
            return f"{self.first_name} {self.last_name}"
        elif self.initials:
            return f"{self.initials} {self.last_name}"
        return self.last_name


@dataclass
class Article:
    """PubMed article metadata."""
    pmid: str
    title: str
    abstract: Optional[str] = None
    authors: List[Author] = field(default_factory=list)
    journal: Optional[str] = None
    publication_date: Optional[str] = None
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None
    doi: Optional[str] = None
    pmc_id: Optional[str] = None
    mesh_terms: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    publication_types: List[str] = field(default_factory=list)
    
    @property
    def citation(self) -> str:
        """Get formatted citation string."""
        author_str = ""
        if self.authors:
            if len(self.authors) == 1:
                author_str = self.authors[0].full_name
            elif len(self.authors) == 2:
                author_str = f"{self.authors[0].full_name} and {self.authors[1].full_name}"
            else:
                author_str = f"{self.authors[0].full_name} et al."
        
        year = ""
        if self.publication_date:
            match = re.search(r'(\d{4})', self.publication_date)
            if match:
                year = f" ({match.group(1)})"
        
        return f"{author_str}{year}. {self.title}. {self.journal or 'Unknown Journal'}."
    
    @property
    def pubmed_url(self) -> str:
        """Get PubMed URL for this article."""
        return f"https://pubmed.ncbi.nlm.nih.gov/{self.pmid}/"


@dataclass
class SearchResult:
    """PubMed search results container."""
    query: str
    total_count: int
    returned_count: int
    articles: List[Article]
    search_time: float  # seconds
    web_env: Optional[str] = None  # For pagination
    query_key: Optional[str] = None


# =============================================================================
# PubMed Client
# =============================================================================

class PubMedClient:
    """
    Client for PubMed/NCBI E-utilities API.
    
    Provides access to biomedical literature through PubMed's search interface.
    Implements caching and rate limiting for efficient API usage.
    
    API Reference: https://www.ncbi.nlm.nih.gov/books/NBK25500/
    """
    
    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    
    def __init__(
        self,
        email: Optional[str] = None,
        api_key: Optional[str] = None,
        cache_dir: Optional[Path] = None,
        cache_ttl: int = 86400 * 7,  # 7 days
    ):
        """
        Initialize PubMed client.
        
        Args:
            email: Email for NCBI API (recommended)
            api_key: NCBI API key for higher rate limits (optional)
            cache_dir: Directory for caching responses
            cache_ttl: Cache time-to-live in seconds
        """
        self.email = email or "chemagent@example.com"
        self.api_key = api_key
        self.cache_dir = cache_dir or Path.home() / ".chemagent" / "pubmed_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_ttl = cache_ttl
        
        self.session = requests.Session()
        
        # Rate limiting: 3 requests/second without API key, 10 with API key
        self._last_request_time = 0
        self._min_request_interval = 0.1 if api_key else 0.34
    
    # =========================================================================
    # Cache Management
    # =========================================================================
    
    def _get_cache_key(self, endpoint: str, params: dict) -> str:
        """Generate cache key from endpoint and parameters."""
        # Remove volatile params from cache key
        cache_params = {k: v for k, v in params.items() if k not in ["api_key", "email"]}
        param_str = json.dumps(cache_params, sort_keys=True)
        key_str = f"{endpoint}:{param_str}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _get_cached(self, cache_key: str) -> Optional[str]:
        """Retrieve cached response if valid."""
        cache_file = self.cache_dir / f"{cache_key}.xml"
        if not cache_file.exists():
            return None
        
        try:
            # Check if cache is still valid
            mtime = cache_file.stat().st_mtime
            if time.time() - mtime > self.cache_ttl:
                cache_file.unlink()  # Expired
                return None
            
            return cache_file.read_text()
        except (OSError, IOError):
            return None
    
    def _set_cached(self, cache_key: str, data: str) -> None:
        """Cache response data."""
        cache_file = self.cache_dir / f"{cache_key}.xml"
        cache_file.write_text(data)
    
    # =========================================================================
    # API Request Helpers
    # =========================================================================
    
    def _rate_limit(self) -> None:
        """Apply rate limiting between requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_request_interval:
            time.sleep(self._min_request_interval - elapsed)
        self._last_request_time = time.time()
    
    def _request(
        self,
        endpoint: str,
        params: dict,
        use_cache: bool = True
    ) -> Optional[str]:
        """
        Make API request with caching and rate limiting.
        
        Args:
            endpoint: API endpoint (esearch, efetch, etc.)
            params: Query parameters
            use_cache: Whether to use cache
            
        Returns:
            XML response string or None
        """
        # Add required params
        params["email"] = self.email
        if self.api_key:
            params["api_key"] = self.api_key
        
        cache_key = self._get_cache_key(endpoint, params)
        
        if use_cache:
            cached = self._get_cached(cache_key)
            if cached is not None:
                return cached
        
        self._rate_limit()
        
        url = f"{self.BASE_URL}/{endpoint}.fcgi"
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.text
            
            if use_cache:
                self._set_cached(cache_key, data)
            
            return data
        except requests.RequestException as e:
            logger.warning(f"PubMed API request failed: {endpoint} - {e}")
            return None
    
    # =========================================================================
    # Search Methods
    # =========================================================================
    
    def search(
        self,
        query: str,
        max_results: int = 20,
        sort: str = "relevance",
        min_date: Optional[str] = None,
        max_date: Optional[str] = None,
        publication_types: Optional[List[str]] = None,
        fetch_details: bool = True
    ) -> SearchResult:
        """
        Search PubMed for articles matching a query.
        
        Args:
            query: Search query (supports PubMed query syntax)
            max_results: Maximum number of results to return
            sort: Sort order ("relevance", "date", "pub_date")
            min_date: Minimum publication date (YYYY/MM/DD)
            max_date: Maximum publication date (YYYY/MM/DD)
            publication_types: Filter by publication types
            fetch_details: Whether to fetch full article details
            
        Returns:
            SearchResult with matching articles
        """
        start_time = time.time()
        
        # Build search parameters
        params = {
            "db": "pubmed",
            "term": query,
            "retmax": min(max_results, 100),  # API limit
            "retmode": "xml",
            "usehistory": "y",
        }
        
        if sort == "date":
            params["sort"] = "pub+date"
        elif sort == "relevance":
            params["sort"] = "relevance"
        
        if min_date:
            params["mindate"] = min_date
        if max_date:
            params["maxdate"] = max_date
        if min_date or max_date:
            params["datetype"] = "pdat"
        
        # Execute search
        response = self._request("esearch", params)
        if not response:
            return SearchResult(
                query=query,
                total_count=0,
                returned_count=0,
                articles=[],
                search_time=time.time() - start_time
            )
        
        # Parse search results
        try:
            root = ET.fromstring(response)
            
            count = int(root.findtext("Count", "0"))
            web_env = root.findtext("WebEnv")
            query_key = root.findtext("QueryKey")
            
            # Get PMIDs
            pmids = [id_elem.text for id_elem in root.findall(".//Id")]
            
            articles = []
            if fetch_details and pmids:
                articles = self.fetch_articles(pmids)
            else:
                # Create stub articles with just PMIDs
                articles = [Article(pmid=pmid, title="") for pmid in pmids]
            
            return SearchResult(
                query=query,
                total_count=count,
                returned_count=len(articles),
                articles=articles,
                search_time=time.time() - start_time,
                web_env=web_env,
                query_key=query_key
            )
            
        except ET.ParseError as e:
            logger.error(f"Failed to parse search results: {e}")
            return SearchResult(
                query=query,
                total_count=0,
                returned_count=0,
                articles=[],
                search_time=time.time() - start_time
            )
    
    def fetch_articles(self, pmids: List[str]) -> List[Article]:
        """
        Fetch full article details for given PMIDs.
        
        Args:
            pmids: List of PubMed IDs
            
        Returns:
            List of Article objects
        """
        if not pmids:
            return []
        
        # Fetch in batches of 100
        all_articles = []
        for i in range(0, len(pmids), 100):
            batch = pmids[i:i + 100]
            params = {
                "db": "pubmed",
                "id": ",".join(batch),
                "retmode": "xml",
                "rettype": "abstract"
            }
            
            response = self._request("efetch", params)
            if response:
                articles = self._parse_articles(response)
                all_articles.extend(articles)
        
        return all_articles
    
    def _parse_articles(self, xml_content: str) -> List[Article]:
        """Parse article details from efetch XML response."""
        articles = []
        
        try:
            root = ET.fromstring(xml_content)
            
            for article_elem in root.findall(".//PubmedArticle"):
                article = self._parse_single_article(article_elem)
                if article:
                    articles.append(article)
                    
        except ET.ParseError as e:
            logger.error(f"Failed to parse articles: {e}")
        
        return articles
    
    def _parse_single_article(self, article_elem: ET.Element) -> Optional[Article]:
        """Parse a single PubmedArticle element."""
        try:
            medline = article_elem.find("MedlineCitation")
            if medline is None:
                return None
            
            pmid = medline.findtext("PMID", "")
            
            article_data = medline.find("Article")
            if article_data is None:
                return Article(pmid=pmid, title="")
            
            # Title
            title = article_data.findtext("ArticleTitle", "")
            
            # Abstract
            abstract_elem = article_data.find(".//Abstract")
            abstract = None
            if abstract_elem is not None:
                abstract_parts = []
                for text_elem in abstract_elem.findall("AbstractText"):
                    label = text_elem.get("Label", "")
                    text = text_elem.text or ""
                    if label:
                        abstract_parts.append(f"{label}: {text}")
                    else:
                        abstract_parts.append(text)
                abstract = " ".join(abstract_parts)
            
            # Authors
            authors = []
            author_list = article_data.find("AuthorList")
            if author_list is not None:
                for author_elem in author_list.findall("Author"):
                    last_name = author_elem.findtext("LastName", "")
                    first_name = author_elem.findtext("ForeName")
                    initials = author_elem.findtext("Initials")
                    
                    affiliation_elem = author_elem.find(".//Affiliation")
                    affiliation = affiliation_elem.text if affiliation_elem is not None else None
                    
                    if last_name:
                        authors.append(Author(
                            last_name=last_name,
                            first_name=first_name,
                            initials=initials,
                            affiliation=affiliation
                        ))
            
            # Journal info
            journal_elem = article_data.find("Journal")
            journal = None
            volume = None
            issue = None
            pub_date = None
            
            if journal_elem is not None:
                journal = journal_elem.findtext(".//Title", "")
                if not journal:
                    journal = journal_elem.findtext(".//ISOAbbreviation", "")
                
                journal_issue = journal_elem.find("JournalIssue")
                if journal_issue is not None:
                    volume = journal_issue.findtext("Volume")
                    issue = journal_issue.findtext("Issue")
                    
                    pub_date_elem = journal_issue.find("PubDate")
                    if pub_date_elem is not None:
                        year = pub_date_elem.findtext("Year", "")
                        month = pub_date_elem.findtext("Month", "")
                        day = pub_date_elem.findtext("Day", "")
                        pub_date = f"{year} {month} {day}".strip()
            
            # Pages
            pages = article_data.findtext(".//MedlinePgn")
            
            # DOI
            doi = None
            for article_id in article_elem.findall(".//ArticleId"):
                if article_id.get("IdType") == "doi":
                    doi = article_id.text
                    break
            
            # PMC ID
            pmc_id = None
            for article_id in article_elem.findall(".//ArticleId"):
                if article_id.get("IdType") == "pmc":
                    pmc_id = article_id.text
                    break
            
            # MeSH terms
            mesh_terms = []
            mesh_list = medline.find("MeshHeadingList")
            if mesh_list is not None:
                for mesh in mesh_list.findall("MeshHeading"):
                    descriptor = mesh.findtext("DescriptorName", "")
                    if descriptor:
                        mesh_terms.append(descriptor)
            
            # Keywords
            keywords = []
            keyword_list = medline.find("KeywordList")
            if keyword_list is not None:
                for kw in keyword_list.findall("Keyword"):
                    if kw.text:
                        keywords.append(kw.text)
            
            # Publication types
            pub_types = []
            pub_type_list = article_data.find("PublicationTypeList")
            if pub_type_list is not None:
                for pt in pub_type_list.findall("PublicationType"):
                    if pt.text:
                        pub_types.append(pt.text)
            
            return Article(
                pmid=pmid,
                title=title,
                abstract=abstract,
                authors=authors,
                journal=journal,
                publication_date=pub_date,
                volume=volume,
                issue=issue,
                pages=pages,
                doi=doi,
                pmc_id=pmc_id,
                mesh_terms=mesh_terms,
                keywords=keywords,
                publication_types=pub_types
            )
            
        except Exception as e:
            logger.warning(f"Failed to parse article: {e}")
            return None
    
    # =========================================================================
    # Specialized Search Methods
    # =========================================================================
    
    def search_compound(
        self,
        compound_name: str,
        max_results: int = 20
    ) -> SearchResult:
        """
        Search for articles about a specific compound.
        
        Args:
            compound_name: Chemical compound name
            max_results: Maximum results
            
        Returns:
            SearchResult with matching articles
        """
        # Build compound-specific query
        query = f'("{compound_name}"[Title/Abstract] OR "{compound_name}"[MeSH Terms])'
        return self.search(query, max_results=max_results)
    
    def search_target(
        self,
        target_name: str,
        target_type: str = "protein",
        max_results: int = 20
    ) -> SearchResult:
        """
        Search for articles about a specific drug target.
        
        Args:
            target_name: Target name (e.g., "EGFR", "ACE2")
            target_type: Type of target ("protein", "gene", "receptor")
            max_results: Maximum results
            
        Returns:
            SearchResult with matching articles
        """
        # Build target-specific query
        query = f'"{target_name}"[Title/Abstract] AND {target_type}[Title/Abstract]'
        return self.search(query, max_results=max_results)
    
    def search_drug_target_interaction(
        self,
        drug_name: str,
        target_name: str,
        max_results: int = 20
    ) -> SearchResult:
        """
        Search for articles about drug-target interactions.
        
        Args:
            drug_name: Drug or compound name
            target_name: Target name
            max_results: Maximum results
            
        Returns:
            SearchResult with matching articles
        """
        query = f'("{drug_name}"[Title/Abstract]) AND ("{target_name}"[Title/Abstract])'
        return self.search(query, max_results=max_results)
    
    def search_disease(
        self,
        disease_name: str,
        include_drugs: bool = False,
        max_results: int = 20
    ) -> SearchResult:
        """
        Search for articles about a disease.
        
        Args:
            disease_name: Disease name
            include_drugs: If True, focus on drug therapy articles
            max_results: Maximum results
            
        Returns:
            SearchResult with matching articles
        """
        if include_drugs:
            query = f'"{disease_name}"[MeSH Terms] AND (drug therapy[MeSH Subheading] OR treatment[Title/Abstract])'
        else:
            query = f'"{disease_name}"[MeSH Terms]'
        
        return self.search(query, max_results=max_results)
    
    def search_mechanism(
        self,
        compound_name: str,
        mechanism_keywords: Optional[List[str]] = None,
        max_results: int = 20
    ) -> SearchResult:
        """
        Search for articles about compound mechanism of action.
        
        Args:
            compound_name: Compound name
            mechanism_keywords: Optional specific mechanism terms
            max_results: Maximum results
            
        Returns:
            SearchResult with matching articles
        """
        if mechanism_keywords:
            mech_terms = " OR ".join([f'"{kw}"[Title/Abstract]' for kw in mechanism_keywords])
            query = f'("{compound_name}"[Title/Abstract]) AND ({mech_terms})'
        else:
            query = f'"{compound_name}"[Title/Abstract] AND (mechanism[Title/Abstract] OR pharmacology[MeSH Subheading])'
        
        return self.search(query, max_results=max_results)
    
    def get_recent_reviews(
        self,
        topic: str,
        years: int = 5,
        max_results: int = 10
    ) -> SearchResult:
        """
        Get recent review articles on a topic.
        
        Args:
            topic: Topic to search
            years: How many years back to search
            max_results: Maximum results
            
        Returns:
            SearchResult with review articles
        """
        current_year = datetime.now().year
        min_year = current_year - years
        
        query = f'{topic} AND Review[Publication Type]'
        return self.search(
            query,
            max_results=max_results,
            min_date=f"{min_year}/01/01",
            sort="date"
        )


# =============================================================================
# Convenience Functions
# =============================================================================

def search_pubmed(
    query: str,
    max_results: int = 20,
    email: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Simple function to search PubMed.
    
    Args:
        query: Search query
        max_results: Maximum number of results
        email: Email for API (optional)
        
    Returns:
        List of article dictionaries
    """
    client = PubMedClient(email=email)
    result = client.search(query, max_results=max_results)
    
    return [
        {
            "pmid": a.pmid,
            "title": a.title,
            "abstract": a.abstract,
            "authors": [auth.full_name for auth in a.authors],
            "journal": a.journal,
            "publication_date": a.publication_date,
            "doi": a.doi,
            "url": a.pubmed_url,
            "mesh_terms": a.mesh_terms,
        }
        for a in result.articles
    ]


def get_article_summary(pmid: str, email: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Get summary for a specific article.
    
    Args:
        pmid: PubMed ID
        email: Email for API
        
    Returns:
        Article summary dictionary or None
    """
    client = PubMedClient(email=email)
    articles = client.fetch_articles([pmid])
    
    if not articles:
        return None
    
    a = articles[0]
    return {
        "pmid": a.pmid,
        "title": a.title,
        "abstract": a.abstract,
        "citation": a.citation,
        "authors": [auth.full_name for auth in a.authors],
        "journal": a.journal,
        "publication_date": a.publication_date,
        "doi": a.doi,
        "pmc_id": a.pmc_id,
        "url": a.pubmed_url,
        "mesh_terms": a.mesh_terms,
        "keywords": a.keywords,
        "publication_types": a.publication_types,
    }


# =============================================================================
# CLI Entry Point
# =============================================================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python pubmed_client.py <search_query>")
        print("\nExamples:")
        print("  python pubmed_client.py 'aspirin mechanism of action'")
        print("  python pubmed_client.py 'EGFR inhibitors cancer'")
        sys.exit(1)
    
    query = " ".join(sys.argv[1:])
    
    client = PubMedClient()
    result = client.search(query, max_results=5)
    
    print(f"\n{'='*60}")
    print(f"PubMed Search: {query}")
    print(f"{'='*60}")
    print(f"Total results: {result.total_count}")
    print(f"Returned: {result.returned_count}")
    print(f"Search time: {result.search_time:.2f}s")
    
    for i, article in enumerate(result.articles, 1):
        print(f"\n--- Article {i} ---")
        print(f"PMID: {article.pmid}")
        print(f"Title: {article.title[:100]}..." if len(article.title) > 100 else f"Title: {article.title}")
        print(f"Journal: {article.journal}")
        print(f"Date: {article.publication_date}")
        if article.abstract:
            print(f"Abstract: {article.abstract[:200]}...")
        print(f"URL: {article.pubmed_url}")
