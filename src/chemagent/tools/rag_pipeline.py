"""
RAG (Retrieval-Augmented Generation) pipeline for literature-based Q&A.

This module provides a simple RAG system for augmenting queries with 
relevant scientific literature from PubMed and stored knowledge.

Features:
- Local vector store using ChromaDB (optional)
- Semantic search over indexed documents
- Integration with PubMed for on-demand retrieval
- Context augmentation for LLM queries

Note: ChromaDB is optional. The system can work with direct PubMed 
queries for simpler deployments.
"""

import json
import logging
import hashlib
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple
from pathlib import Path
import time

logger = logging.getLogger(__name__)

# Optional imports - graceful degradation if not available
try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    logger.info("ChromaDB not available - using PubMed-only mode")


# =============================================================================
# Data Models
# =============================================================================

@dataclass
class Document:
    """A document for indexing/retrieval."""
    id: str
    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None


@dataclass
class RetrievalResult:
    """Result from retrieval operation."""
    documents: List[Document]
    scores: List[float]
    query: str
    source: str  # "chromadb", "pubmed", "hybrid"


@dataclass
class RAGContext:
    """Context prepared for LLM augmentation."""
    query: str
    retrieved_documents: List[Document]
    formatted_context: str
    sources: List[str]
    retrieval_time: float


# =============================================================================
# Simple Text Embeddings (using keyword matching as fallback)
# =============================================================================

def simple_keyword_embedding(text: str, vocab_size: int = 1000) -> List[float]:
    """
    Create a simple keyword-based embedding.
    
    This is a fallback when sentence-transformers is not available.
    Uses TF-IDF-like weighting with hash-based vocabulary.
    
    Args:
        text: Text to embed
        vocab_size: Size of vocabulary vector
        
    Returns:
        Embedding vector
    """
    # Tokenize and normalize
    words = text.lower().split()
    
    # Create sparse embedding using hash
    embedding = [0.0] * vocab_size
    for word in words:
        idx = hash(word) % vocab_size
        embedding[idx] += 1.0
    
    # Normalize
    norm = sum(x * x for x in embedding) ** 0.5
    if norm > 0:
        embedding = [x / norm for x in embedding]
    
    return embedding


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    
    if norm_a == 0 or norm_b == 0:
        return 0.0
    
    return dot / (norm_a * norm_b)


# =============================================================================
# Document Store (Local In-Memory or ChromaDB)
# =============================================================================

class SimpleDocumentStore:
    """
    Simple in-memory document store with keyword-based retrieval.
    
    Used when ChromaDB is not available. Provides basic semantic
    search using keyword embeddings.
    """
    
    def __init__(self):
        """Initialize document store."""
        self.documents: Dict[str, Document] = {}
        self.embeddings: Dict[str, List[float]] = {}
    
    def add_document(self, doc: Document) -> None:
        """Add document to store."""
        self.documents[doc.id] = doc
        
        # Compute embedding if not provided
        if doc.embedding is None:
            doc.embedding = simple_keyword_embedding(doc.text)
        
        self.embeddings[doc.id] = doc.embedding
    
    def add_documents(self, docs: List[Document]) -> None:
        """Add multiple documents."""
        for doc in docs:
            self.add_document(doc)
    
    def search(
        self,
        query: str,
        top_k: int = 5
    ) -> Tuple[List[Document], List[float]]:
        """
        Search for similar documents.
        
        Args:
            query: Search query
            top_k: Number of results to return
            
        Returns:
            Tuple of (documents, scores)
        """
        if not self.documents:
            return [], []
        
        query_embedding = simple_keyword_embedding(query)
        
        # Calculate similarities
        similarities = []
        for doc_id, doc_embedding in self.embeddings.items():
            score = cosine_similarity(query_embedding, doc_embedding)
            similarities.append((doc_id, score))
        
        # Sort by score
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        # Get top k
        top_results = similarities[:top_k]
        documents = [self.documents[doc_id] for doc_id, _ in top_results]
        scores = [score for _, score in top_results]
        
        return documents, scores
    
    def count(self) -> int:
        """Get document count."""
        return len(self.documents)
    
    def clear(self) -> None:
        """Clear all documents."""
        self.documents.clear()
        self.embeddings.clear()


class ChromaDocumentStore:
    """
    ChromaDB-based document store for scalable vector search.
    
    Uses ChromaDB for efficient similarity search with proper
    vector indexing. Supports persistent storage.
    """
    
    def __init__(
        self,
        collection_name: str = "chemagent_literature",
        persist_directory: Optional[Path] = None
    ):
        """
        Initialize ChromaDB store.
        
        Args:
            collection_name: Name of the collection
            persist_directory: Directory for persistent storage
        """
        if not CHROMADB_AVAILABLE:
            raise ImportError("ChromaDB is required for this store. Install with: pip install chromadb")
        
        settings = Settings(
            anonymized_telemetry=False
        )
        
        if persist_directory:
            self.client = chromadb.PersistentClient(
                path=str(persist_directory),
                settings=settings
            )
        else:
            self.client = chromadb.Client(settings=settings)
        
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"description": "ChemAgent literature collection"}
        )
    
    def add_document(self, doc: Document) -> None:
        """Add document to store."""
        self.collection.add(
            ids=[doc.id],
            documents=[doc.text],
            metadatas=[doc.metadata] if doc.metadata else None
        )
    
    def add_documents(self, docs: List[Document]) -> None:
        """Add multiple documents."""
        self.collection.add(
            ids=[d.id for d in docs],
            documents=[d.text for d in docs],
            metadatas=[d.metadata for d in docs]
        )
    
    def search(
        self,
        query: str,
        top_k: int = 5
    ) -> Tuple[List[Document], List[float]]:
        """
        Search for similar documents.
        
        Args:
            query: Search query
            top_k: Number of results to return
            
        Returns:
            Tuple of (documents, scores)
        """
        results = self.collection.query(
            query_texts=[query],
            n_results=top_k
        )
        
        documents = []
        scores = []
        
        if results and results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                doc = Document(
                    id=doc_id,
                    text=results["documents"][0][i] if results["documents"] else "",
                    metadata=results["metadatas"][0][i] if results["metadatas"] else {}
                )
                documents.append(doc)
                
                # ChromaDB returns distances, convert to similarity
                distance = results["distances"][0][i] if results["distances"] else 0
                scores.append(1.0 / (1.0 + distance))
        
        return documents, scores
    
    def count(self) -> int:
        """Get document count."""
        return self.collection.count()
    
    def clear(self) -> None:
        """Clear all documents."""
        # ChromaDB doesn't have a clear method, delete and recreate
        self.client.delete_collection(self.collection.name)
        self.collection = self.client.create_collection(
            name=self.collection.name,
            metadata={"description": "ChemAgent literature collection"}
        )


# =============================================================================
# RAG Pipeline
# =============================================================================

class RAGPipeline:
    """
    RAG Pipeline for literature-augmented queries.
    
    Combines local vector store with on-demand PubMed retrieval
    to provide relevant context for chemistry queries.
    """
    
    def __init__(
        self,
        use_chromadb: bool = False,
        persist_directory: Optional[Path] = None,
        pubmed_email: Optional[str] = None
    ):
        """
        Initialize RAG pipeline.
        
        Args:
            use_chromadb: Whether to use ChromaDB (requires installation)
            persist_directory: Directory for persistent storage
            pubmed_email: Email for PubMed API
        """
        # Initialize document store
        if use_chromadb and CHROMADB_AVAILABLE:
            self.store = ChromaDocumentStore(
                persist_directory=persist_directory
            )
            self.store_type = "chromadb"
        else:
            self.store = SimpleDocumentStore()
            self.store_type = "simple"
        
        # Initialize PubMed client (lazy import)
        self._pubmed_client = None
        self._pubmed_email = pubmed_email
        
        logger.info(f"RAG pipeline initialized with {self.store_type} store")
    
    @property
    def pubmed_client(self):
        """Lazy-load PubMed client."""
        if self._pubmed_client is None:
            from chemagent.tools.pubmed_client import PubMedClient
            self._pubmed_client = PubMedClient(email=self._pubmed_email)
        return self._pubmed_client
    
    # =========================================================================
    # Document Management
    # =========================================================================
    
    def index_pubmed_articles(
        self,
        query: str,
        max_articles: int = 20
    ) -> int:
        """
        Index PubMed articles for a query.
        
        Args:
            query: PubMed search query
            max_articles: Maximum articles to index
            
        Returns:
            Number of articles indexed
        """
        result = self.pubmed_client.search(query, max_results=max_articles)
        
        docs = []
        for article in result.articles:
            # Combine title and abstract for indexing
            text = f"{article.title}\n\n{article.abstract or ''}"
            
            doc = Document(
                id=f"pubmed_{article.pmid}",
                text=text,
                metadata={
                    "source": "pubmed",
                    "pmid": article.pmid,
                    "title": article.title,
                    "authors": [a.full_name for a in article.authors[:3]],
                    "journal": article.journal,
                    "date": article.publication_date,
                    "url": article.pubmed_url
                }
            )
            docs.append(doc)
        
        self.store.add_documents(docs)
        logger.info(f"Indexed {len(docs)} articles from PubMed")
        
        return len(docs)
    
    def index_document(
        self,
        text: str,
        doc_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Index a custom document.
        
        Args:
            text: Document text
            doc_id: Optional document ID
            metadata: Optional metadata
            
        Returns:
            Document ID
        """
        if doc_id is None:
            doc_id = f"doc_{hashlib.md5(text.encode()).hexdigest()[:8]}"
        
        doc = Document(
            id=doc_id,
            text=text,
            metadata=metadata or {}
        )
        
        self.store.add_document(doc)
        return doc_id
    
    # =========================================================================
    # Retrieval
    # =========================================================================
    
    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        use_pubmed: bool = True
    ) -> RetrievalResult:
        """
        Retrieve relevant documents for a query.
        
        Args:
            query: Search query
            top_k: Number of documents to retrieve
            use_pubmed: Whether to also search PubMed
            
        Returns:
            RetrievalResult with matched documents
        """
        all_docs = []
        all_scores = []
        source = "local"
        
        # Search local store
        if self.store.count() > 0:
            local_docs, local_scores = self.store.search(query, top_k=top_k)
            all_docs.extend(local_docs)
            all_scores.extend(local_scores)
        
        # Search PubMed if enabled and not enough local results
        if use_pubmed and len(all_docs) < top_k:
            pubmed_count = top_k - len(all_docs)
            result = self.pubmed_client.search(query, max_results=pubmed_count)
            
            for article in result.articles:
                doc = Document(
                    id=f"pubmed_{article.pmid}",
                    text=f"{article.title}\n\n{article.abstract or ''}",
                    metadata={
                        "source": "pubmed",
                        "pmid": article.pmid,
                        "title": article.title,
                        "url": article.pubmed_url
                    }
                )
                all_docs.append(doc)
                all_scores.append(0.5)  # Default score for PubMed results
            
            source = "hybrid" if self.store.count() > 0 else "pubmed"
        
        return RetrievalResult(
            documents=all_docs[:top_k],
            scores=all_scores[:top_k],
            query=query,
            source=source
        )
    
    # =========================================================================
    # Context Augmentation
    # =========================================================================
    
    def get_context(
        self,
        query: str,
        top_k: int = 3,
        max_context_length: int = 2000
    ) -> RAGContext:
        """
        Get formatted context for augmenting an LLM query.
        
        Args:
            query: User query
            top_k: Number of documents to include
            max_context_length: Maximum context length
            
        Returns:
            RAGContext ready for LLM augmentation
        """
        start_time = time.time()
        
        result = self.retrieve(query, top_k=top_k)
        
        # Format context
        context_parts = []
        sources = []
        current_length = 0
        
        for doc, score in zip(result.documents, result.scores):
            # Truncate if needed
            available_length = max_context_length - current_length - 100
            if available_length <= 0:
                break
            
            text = doc.text[:available_length]
            
            # Format with source info
            source_info = ""
            if doc.metadata.get("source") == "pubmed":
                pmid = doc.metadata.get("pmid", "")
                source_info = f"[Source: PubMed PMID {pmid}]"
                sources.append(doc.metadata.get("url", f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"))
            else:
                source_info = f"[Document: {doc.id}]"
                sources.append(doc.id)
            
            context_parts.append(f"{source_info}\n{text}")
            current_length += len(text) + len(source_info) + 2
        
        formatted_context = "\n\n---\n\n".join(context_parts)
        
        return RAGContext(
            query=query,
            retrieved_documents=result.documents,
            formatted_context=formatted_context,
            sources=sources,
            retrieval_time=time.time() - start_time
        )
    
    def augment_prompt(
        self,
        query: str,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Create an augmented prompt with retrieved context.
        
        Args:
            query: User query
            system_prompt: Optional system prompt
            
        Returns:
            Augmented prompt string
        """
        context = self.get_context(query)
        
        if not system_prompt:
            system_prompt = "You are a helpful chemistry assistant. Use the following context to answer the question."
        
        prompt = f"""{system_prompt}

CONTEXT FROM SCIENTIFIC LITERATURE:
{context.formatted_context}

SOURCES:
{', '.join(context.sources)}

USER QUESTION:
{query}

Please provide a helpful answer based on the context above. Cite sources when possible."""
        
        return prompt


# =============================================================================
# Convenience Functions
# =============================================================================

def search_literature(
    query: str,
    top_k: int = 5
) -> List[Dict[str, Any]]:
    """
    Simple literature search function.
    
    Args:
        query: Search query
        top_k: Number of results
        
    Returns:
        List of document dictionaries
    """
    pipeline = RAGPipeline()
    result = pipeline.retrieve(query, top_k=top_k)
    
    return [
        {
            "id": doc.id,
            "text": doc.text[:500] + "..." if len(doc.text) > 500 else doc.text,
            "score": score,
            "metadata": doc.metadata
        }
        for doc, score in zip(result.documents, result.scores)
    ]


def get_augmented_context(
    query: str,
    max_length: int = 2000
) -> Dict[str, Any]:
    """
    Get augmented context for a query.
    
    Args:
        query: User query
        max_length: Maximum context length
        
    Returns:
        Context dictionary
    """
    pipeline = RAGPipeline()
    context = pipeline.get_context(query, max_context_length=max_length)
    
    return {
        "query": context.query,
        "context": context.formatted_context,
        "sources": context.sources,
        "retrieval_time": context.retrieval_time
    }


# =============================================================================
# CLI Entry Point
# =============================================================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python rag_pipeline.py <query>")
        print("\nExamples:")
        print("  python rag_pipeline.py 'aspirin mechanism of action'")
        sys.exit(1)
    
    query = " ".join(sys.argv[1:])
    
    print(f"\n{'='*60}")
    print(f"RAG Pipeline Query: {query}")
    print(f"{'='*60}")
    
    pipeline = RAGPipeline()
    context = pipeline.get_context(query)
    
    print(f"\nRetrieved {len(context.retrieved_documents)} documents in {context.retrieval_time:.2f}s")
    print(f"\nSources: {', '.join(context.sources)}")
    print(f"\n--- Context ---")
    print(context.formatted_context[:1000] + "..." if len(context.formatted_context) > 1000 else context.formatted_context)
