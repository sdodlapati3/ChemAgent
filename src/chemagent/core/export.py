"""
Export functionality for research reference managers.

Exports ChemAgent query results to various formats:
- BibTeX: For LaTeX and reference managers (Zotero, Mendeley)
- RIS: For EndNote, RefWorks, and other managers
- JSON: For programmatic access
- Markdown: For documentation and reports

Each export includes:
- Query provenance (what was asked)
- Data sources used (ChEMBL, PubChem, etc.)
- Result summary
- Timestamps and reproducibility info

Usage:
    >>> from chemagent.core.export import ResultExporter
    >>> 
    >>> exporter = ResultExporter()
    >>> 
    >>> # Export single result
    >>> bibtex = exporter.to_bibtex(result, query="Find aspirin properties")
    >>> 
    >>> # Export to file
    >>> exporter.export_to_file(result, "results.bib", format="bibtex")
    >>> 
    >>> # Batch export
    >>> exporter.export_batch(results, "research_session.ris", format="ris")
"""

import hashlib
import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


@dataclass
class ExportMetadata:
    """Metadata for exported results."""
    
    query: str
    intent_type: str
    sources: List[str]
    timestamp: str
    execution_time_ms: float
    success: bool
    compound_names: List[str] = None
    target_names: List[str] = None
    
    def __post_init__(self):
        if self.compound_names is None:
            self.compound_names = []
        if self.target_names is None:
            self.target_names = []


class ResultExporter:
    """
    Export ChemAgent results to reference manager formats.
    
    Supports BibTeX, RIS, JSON, and Markdown output formats.
    Extracts sources and provenance from query results.
    
    Example:
        >>> exporter = ResultExporter()
        >>> 
        >>> # From QueryResult
        >>> bibtex = exporter.to_bibtex(result)
        >>> print(bibtex)
        @misc{chemagent_aspirin_2026,
          title = {ChemAgent Query: Properties of aspirin},
          author = {ChemAgent},
          year = {2026},
          ...
        }
    """
    
    # Source database URLs
    SOURCE_URLS = {
        "chembl": "https://www.ebi.ac.uk/chembl/",
        "pubchem": "https://pubchem.ncbi.nlm.nih.gov/",
        "uniprot": "https://www.uniprot.org/",
        "opentargets": "https://platform.opentargets.org/",
        "pdb": "https://www.rcsb.org/",
        "alphafold": "https://alphafold.ebi.ac.uk/",
        "rdkit": "https://www.rdkit.org/",
        "bindingdb": "https://www.bindingdb.org/",
    }
    
    def __init__(self, author: str = "ChemAgent"):
        """
        Initialize exporter.
        
        Args:
            author: Default author for citations
        """
        self.author = author
    
    def extract_metadata(
        self,
        result: Any,
        query: str = "",
    ) -> ExportMetadata:
        """
        Extract metadata from a query result.
        
        Args:
            result: QueryResult or dict with answer/provenance
            query: Original query string
            
        Returns:
            ExportMetadata with extracted information
        """
        # Handle different result types
        if hasattr(result, 'answer'):
            # QueryResult object
            answer = result.answer or ""
            provenance = getattr(result, 'provenance', []) or []
            intent_type = getattr(result, 'intent_type', 'unknown') or 'unknown'
            execution_time = getattr(result, 'execution_time_ms', 0) or 0
            success = getattr(result, 'success', False)
            query = query or getattr(result, 'original_query', '')
        elif isinstance(result, dict):
            answer = result.get('answer', '')
            provenance = result.get('provenance', [])
            intent_type = result.get('intent_type', 'unknown')
            execution_time = result.get('execution_time_ms', 0)
            success = result.get('success', False)
            query = query or result.get('query', '')
        else:
            answer = str(result)
            provenance = []
            intent_type = 'unknown'
            execution_time = 0
            success = True
        
        # Extract sources from provenance
        sources = self._extract_sources(provenance, answer)
        
        # Extract compound and target names
        compounds = self._extract_compounds(answer, query)
        targets = self._extract_targets(answer, query)
        
        return ExportMetadata(
            query=query,
            intent_type=intent_type,
            sources=sources,
            timestamp=datetime.utcnow().isoformat(),
            execution_time_ms=execution_time,
            success=success,
            compound_names=compounds,
            target_names=targets,
        )
    
    def _extract_sources(self, provenance: List[Dict], answer: str) -> List[str]:
        """Extract data sources from provenance and answer."""
        sources = set()
        
        # From provenance records
        for prov in provenance:
            if isinstance(prov, dict):
                tool = prov.get('tool', '').lower()
                source = prov.get('source', '').lower()
                
                for key in self.SOURCE_URLS:
                    if key in tool or key in source:
                        sources.add(key.title())
        
        # From answer content
        answer_lower = answer.lower()
        for key in self.SOURCE_URLS:
            if key in answer_lower:
                sources.add(key.title())
        
        return sorted(sources) or ['ChemAgent']
    
    def _extract_compounds(self, answer: str, query: str) -> List[str]:
        """Extract compound names from answer and query."""
        compounds = set()
        text = f"{query} {answer}"
        
        # Common drug names
        drug_pattern = r'\b(aspirin|ibuprofen|acetaminophen|paracetamol|metformin|' \
                       r'atorvastatin|lisinopril|omeprazole|caffeine|morphine|' \
                       r'warfarin|sildenafil|atorvastatin|simvastatin)\b'
        for match in re.finditer(drug_pattern, text, re.IGNORECASE):
            compounds.add(match.group(1).lower())
        
        # ChEMBL IDs
        for match in re.finditer(r'CHEMBL\d+', text, re.IGNORECASE):
            compounds.add(match.group(0).upper())
        
        return sorted(compounds)
    
    def _extract_targets(self, answer: str, query: str) -> List[str]:
        """Extract target names from answer and query."""
        targets = set()
        text = f"{query} {answer}"
        
        # Common target names
        target_pattern = r'\b(EGFR|BRAF|COX-2|HMG-CoA|ACE|PPAR|kinase|receptor)\b'
        for match in re.finditer(target_pattern, text, re.IGNORECASE):
            targets.add(match.group(1).upper())
        
        # UniProt IDs
        for match in re.finditer(r'[A-Z]\d[A-Z0-9]{3}\d|P\d{5}', text):
            targets.add(match.group(0))
        
        return sorted(targets)
    
    def _generate_cite_key(self, metadata: ExportMetadata) -> str:
        """Generate a unique citation key."""
        # Use first compound or first few words of query
        identifier = ""
        if metadata.compound_names:
            identifier = metadata.compound_names[0]
        elif metadata.target_names:
            identifier = metadata.target_names[0]
        else:
            words = metadata.query.split()[:3]
            identifier = "_".join(w.lower() for w in words if w.isalnum())
        
        # Clean identifier
        identifier = re.sub(r'[^a-zA-Z0-9_]', '', identifier)[:20]
        
        year = datetime.now().year
        return f"chemagent_{identifier}_{year}"
    
    def to_bibtex(
        self,
        result: Any,
        query: str = "",
        cite_key: Optional[str] = None,
    ) -> str:
        """
        Export result to BibTeX format.
        
        Args:
            result: QueryResult or dict
            query: Original query
            cite_key: Custom citation key (auto-generated if None)
            
        Returns:
            BibTeX formatted string
        """
        metadata = self.extract_metadata(result, query)
        
        if cite_key is None:
            cite_key = self._generate_cite_key(metadata)
        
        # Build BibTeX entry
        sources_str = ", ".join(metadata.sources)
        keywords = ", ".join(
            metadata.compound_names + metadata.target_names + [metadata.intent_type]
        )
        
        # Escape special characters
        def escape_bibtex(s: str) -> str:
            return s.replace('&', r'\&').replace('%', r'\%').replace('_', r'\_')
        
        bibtex = f"""@misc{{{cite_key},
  title = {{ChemAgent Query: {escape_bibtex(metadata.query[:100])}}},
  author = {{{self.author}}},
  year = {{{datetime.now().year}}},
  month = {{{datetime.now().strftime('%b').lower()}}},
  note = {{Query executed via ChemAgent. Sources: {sources_str}. Success: {metadata.success}}},
  howpublished = {{ChemAgent Cheminformatics System}},
  keywords = {{{escape_bibtex(keywords)}}},
  abstract = {{Automated chemistry query result. Intent: {metadata.intent_type}. Execution time: {metadata.execution_time_ms:.1f}ms.}},
  url = {{https://github.com/sdodlapati3/ChemAgent}},
  timestamp = {{{metadata.timestamp}}}
}}"""
        
        return bibtex
    
    def to_ris(
        self,
        result: Any,
        query: str = "",
    ) -> str:
        """
        Export result to RIS format (EndNote, RefWorks compatible).
        
        Args:
            result: QueryResult or dict
            query: Original query
            
        Returns:
            RIS formatted string
        """
        metadata = self.extract_metadata(result, query)
        
        sources_str = ", ".join(metadata.sources)
        
        ris_lines = [
            "TY  - COMP",  # Computer Program
            f"TI  - ChemAgent Query: {metadata.query[:100]}",
            f"AU  - {self.author}",
            f"PY  - {datetime.now().year}",
            f"DA  - {datetime.now().strftime('%Y/%m/%d')}",
            f"AB  - Automated chemistry query result. Intent: {metadata.intent_type}. "
            f"Sources: {sources_str}. Execution time: {metadata.execution_time_ms:.1f}ms. "
            f"Success: {metadata.success}.",
            "PB  - ChemAgent Cheminformatics System",
            "UR  - https://github.com/sdodlapati3/ChemAgent",
        ]
        
        # Add keywords
        for compound in metadata.compound_names:
            ris_lines.append(f"KW  - {compound}")
        for target in metadata.target_names:
            ris_lines.append(f"KW  - {target}")
        ris_lines.append(f"KW  - {metadata.intent_type}")
        
        # Add sources as related records
        for source in metadata.sources:
            url = self.SOURCE_URLS.get(source.lower(), "")
            if url:
                ris_lines.append(f"L2  - {url}")
        
        ris_lines.append("ER  - ")  # End of record
        
        return "\n".join(ris_lines)
    
    def to_json(
        self,
        result: Any,
        query: str = "",
        include_answer: bool = True,
    ) -> str:
        """
        Export result to JSON format.
        
        Args:
            result: QueryResult or dict
            query: Original query
            include_answer: Include full answer in export
            
        Returns:
            JSON formatted string
        """
        metadata = self.extract_metadata(result, query)
        
        export_data = {
            "chemagent_export": {
                "version": "1.0",
                "exported_at": datetime.utcnow().isoformat(),
            },
            "query": {
                "text": metadata.query,
                "intent_type": metadata.intent_type,
                "executed_at": metadata.timestamp,
                "execution_time_ms": metadata.execution_time_ms,
                "success": metadata.success,
            },
            "sources": {
                "databases": metadata.sources,
                "urls": {
                    source: self.SOURCE_URLS.get(source.lower(), "")
                    for source in metadata.sources
                },
            },
            "entities": {
                "compounds": metadata.compound_names,
                "targets": metadata.target_names,
            },
        }
        
        if include_answer:
            if hasattr(result, 'answer'):
                export_data["result"] = {
                    "answer": result.answer,
                    "raw_output": getattr(result, 'raw_output', None),
                }
            elif isinstance(result, dict):
                export_data["result"] = {
                    "answer": result.get('answer'),
                    "raw_output": result.get('raw_output'),
                }
        
        return json.dumps(export_data, indent=2)
    
    def to_markdown(
        self,
        result: Any,
        query: str = "",
        include_answer: bool = True,
    ) -> str:
        """
        Export result to Markdown format for documentation.
        
        Args:
            result: QueryResult or dict
            query: Original query
            include_answer: Include full answer
            
        Returns:
            Markdown formatted string
        """
        metadata = self.extract_metadata(result, query)
        
        md_lines = [
            "# ChemAgent Query Result",
            "",
            "## Query Information",
            "",
            f"- **Query**: {metadata.query}",
            f"- **Intent Type**: {metadata.intent_type}",
            f"- **Executed**: {metadata.timestamp}",
            f"- **Execution Time**: {metadata.execution_time_ms:.1f}ms",
            f"- **Status**: {'✅ Success' if metadata.success else '❌ Failed'}",
            "",
            "## Data Sources",
            "",
        ]
        
        for source in metadata.sources:
            url = self.SOURCE_URLS.get(source.lower(), "")
            if url:
                md_lines.append(f"- [{source}]({url})")
            else:
                md_lines.append(f"- {source}")
        
        if metadata.compound_names or metadata.target_names:
            md_lines.extend([
                "",
                "## Entities",
                "",
            ])
            
            if metadata.compound_names:
                md_lines.append(f"**Compounds**: {', '.join(metadata.compound_names)}")
            if metadata.target_names:
                md_lines.append(f"**Targets**: {', '.join(metadata.target_names)}")
        
        if include_answer:
            answer = ""
            if hasattr(result, 'answer'):
                answer = result.answer or ""
            elif isinstance(result, dict):
                answer = result.get('answer', '')
            
            if answer:
                md_lines.extend([
                    "",
                    "## Result",
                    "",
                    answer,
                ])
        
        md_lines.extend([
            "",
            "---",
            "",
            f"*Generated by [ChemAgent](https://github.com/sdodlapati3/ChemAgent) on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
        ])
        
        return "\n".join(md_lines)
    
    def export_to_file(
        self,
        result: Any,
        filepath: Union[str, Path],
        format: str = "auto",
        query: str = "",
    ) -> bool:
        """
        Export result to file.
        
        Args:
            result: QueryResult or dict
            filepath: Output file path
            format: Export format (auto, bibtex, ris, json, markdown)
            query: Original query
            
        Returns:
            True if exported successfully
        """
        filepath = Path(filepath)
        
        # Auto-detect format from extension
        if format == "auto":
            ext = filepath.suffix.lower()
            format_map = {
                ".bib": "bibtex",
                ".ris": "ris",
                ".json": "json",
                ".md": "markdown",
                ".txt": "markdown",
            }
            format = format_map.get(ext, "json")
        
        # Generate content
        if format == "bibtex":
            content = self.to_bibtex(result, query)
        elif format == "ris":
            content = self.to_ris(result, query)
        elif format == "json":
            content = self.to_json(result, query)
        elif format == "markdown":
            content = self.to_markdown(result, query)
        else:
            logger.error(f"Unknown export format: {format}")
            return False
        
        try:
            filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info(f"Exported to {filepath} ({format} format)")
            return True
        except Exception as e:
            logger.error(f"Export failed: {e}")
            return False
    
    def export_batch(
        self,
        results: List[Any],
        filepath: Union[str, Path],
        format: str = "auto",
        queries: Optional[List[str]] = None,
    ) -> bool:
        """
        Export multiple results to a single file.
        
        Args:
            results: List of QueryResult or dict
            filepath: Output file path
            format: Export format
            queries: List of query strings (matched by index)
            
        Returns:
            True if exported successfully
        """
        filepath = Path(filepath)
        queries = queries or [""] * len(results)
        
        if format == "auto":
            ext = filepath.suffix.lower()
            format_map = {".bib": "bibtex", ".ris": "ris", ".json": "json", ".md": "markdown"}
            format = format_map.get(ext, "json")
        
        # Generate content for each result
        contents = []
        for result, query in zip(results, queries):
            if format == "bibtex":
                contents.append(self.to_bibtex(result, query))
            elif format == "ris":
                contents.append(self.to_ris(result, query))
            elif format == "json":
                contents.append(self.to_json(result, query))
            elif format == "markdown":
                contents.append(self.to_markdown(result, query))
        
        # Combine
        if format == "json":
            # Wrap in array
            combined = "[\n" + ",\n".join(contents) + "\n]"
        else:
            combined = "\n\n".join(contents)
        
        try:
            filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(combined)
            logger.info(f"Exported {len(results)} results to {filepath}")
            return True
        except Exception as e:
            logger.error(f"Batch export failed: {e}")
            return False


# Convenience functions
def export_bibtex(result: Any, query: str = "") -> str:
    """Quick export to BibTeX."""
    return ResultExporter().to_bibtex(result, query)


def export_ris(result: Any, query: str = "") -> str:
    """Quick export to RIS."""
    return ResultExporter().to_ris(result, query)


def export_json(result: Any, query: str = "") -> str:
    """Quick export to JSON."""
    return ResultExporter().to_json(result, query)


def export_markdown(result: Any, query: str = "") -> str:
    """Quick export to Markdown."""
    return ResultExporter().to_markdown(result, query)
