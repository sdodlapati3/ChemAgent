"""
Assertion-Based Evaluation for ChemAgent.

Provides constraint-based assertions for evaluating agent responses:
- Provenance assertions (every claim must have source)
- Entity assertions (response must mention specific entities)
- Numeric assertions (values within expected ranges)
- Source assertions (data from specific databases)

Philosophy: We don't check exact answers, we check constraints.
"""

import re
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict, is_dataclass
from typing import Any, Dict, List, Optional, Union
from enum import Enum

logger = logging.getLogger(__name__)


def safe_json_dumps(obj: Any, **kwargs) -> str:
    """JSON dumps that handles dataclasses and other non-serializable types."""
    def default_encoder(o):
        if is_dataclass(o) and not isinstance(o, type):
            return asdict(o)
        elif hasattr(o, '__dict__'):
            return o.__dict__
        elif hasattr(o, 'to_dict'):
            return o.to_dict()
        else:
            return str(o)
    
    return json.dumps(obj, default=default_encoder, **kwargs)


class AssertionResult(Enum):
    """Result of an assertion check."""
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"  # Not applicable to this response


@dataclass
class AssertionOutcome:
    """Outcome of running a single assertion."""
    assertion_name: str
    result: AssertionResult
    message: str
    details: Dict[str, Any] = field(default_factory=dict)


class Assertion(ABC):
    """Base class for response assertions."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name of this assertion."""
        pass
    
    @abstractmethod
    def check(
        self, 
        response: str, 
        tool_results: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> AssertionOutcome:
        """
        Check if the response satisfies this assertion.
        
        Args:
            response: The agent's text response
            tool_results: Raw results from tools used
            metadata: Additional context (query, entities, etc.)
        
        Returns:
            AssertionOutcome with pass/fail and details
        """
        pass


# =============================================================================
# Provenance Assertions
# =============================================================================

class HasProvenance(Assertion):
    """Assert that numeric claims have provenance."""
    
    @property
    def name(self) -> str:
        return "has_provenance"
    
    def check(
        self, 
        response: str, 
        tool_results: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> AssertionOutcome:
        """Check that response contains provenance information."""
        
        # Look for provenance indicators
        provenance_patterns = [
            r'(?:source|from|according to|via)\s*[:\s]*\w+',
            r'platform\.opentargets\.org',
            r'ebi\.ac\.uk/chembl',
            r'uniprot\.org',
            r'pubchem\.ncbi',
            r'CHEMBL\d+',
            r'ENSG\d+',
            r'EFO_\d+',
        ]
        
        found_provenance = []
        for pattern in provenance_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            found_provenance.extend(matches)
        
        # Also check tool results for provenance
        tool_provenance = []
        for tool_name, result in tool_results.items():
            if isinstance(result, dict):
                data = result.get("data", result)
                if isinstance(data, dict):
                    if "provenance" in data:
                        tool_provenance.append(data["provenance"])
                    if "source" in data:
                        tool_provenance.append(data["source"])
        
        has_provenance = len(found_provenance) > 0 or len(tool_provenance) > 0
        
        return AssertionOutcome(
            assertion_name=self.name,
            result=AssertionResult.PASSED if has_provenance else AssertionResult.FAILED,
            message=f"Found {len(found_provenance)} provenance indicators" if has_provenance 
                    else "No provenance information found in response",
            details={
                "text_provenance": found_provenance[:5],  # Limit to first 5
                "tool_provenance": tool_provenance[:5]
            }
        )


class SourceIs(Assertion):
    """Assert that data comes from a specific source."""
    
    def __init__(self, expected_source: str):
        """
        Args:
            expected_source: Expected data source (e.g., "Open Targets", "ChEMBL")
        """
        self.expected_source = expected_source.lower()
    
    @property
    def name(self) -> str:
        return f"source_is_{self.expected_source.replace(' ', '_')}"
    
    def check(
        self, 
        response: str, 
        tool_results: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> AssertionOutcome:
        """Check that data comes from expected source."""
        
        # Check response text
        source_in_response = self.expected_source in response.lower()
        
        # Check tool results
        source_in_tools = False
        for tool_name, result in tool_results.items():
            if self.expected_source.replace(" ", "") in tool_name.lower():
                source_in_tools = True
                break
            if isinstance(result, dict):
                data = result.get("data", result)
                if isinstance(data, dict):
                    prov = data.get("provenance", {})
                    if isinstance(prov, dict):
                        if self.expected_source in str(prov.get("source", "")).lower():
                            source_in_tools = True
                            break
        
        passed = source_in_response or source_in_tools
        
        return AssertionOutcome(
            assertion_name=self.name,
            result=AssertionResult.PASSED if passed else AssertionResult.FAILED,
            message=f"Found {self.expected_source} source" if passed 
                    else f"Expected source '{self.expected_source}' not found",
            details={
                "in_response": source_in_response,
                "in_tools": source_in_tools
            }
        )


# =============================================================================
# Entity Assertions
# =============================================================================

class ContainsEntity(Assertion):
    """Assert that response mentions a specific entity."""
    
    def __init__(self, entity: str, case_sensitive: bool = False):
        """
        Args:
            entity: Entity to look for (e.g., "EGFR", "lung cancer")
            case_sensitive: Whether to match case
        """
        self.entity = entity
        self.case_sensitive = case_sensitive
    
    @property
    def name(self) -> str:
        return f"contains_{self.entity.replace(' ', '_')}"
    
    def check(
        self, 
        response: str, 
        tool_results: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> AssertionOutcome:
        """Check that response mentions the entity."""
        
        if self.case_sensitive:
            found = self.entity in response
        else:
            found = self.entity.lower() in response.lower()
        
        # Also check tool results (with safe JSON serialization)
        tools_str = safe_json_dumps(tool_results).lower() if not self.case_sensitive \
                    else safe_json_dumps(tool_results)
        in_tools = self.entity.lower() in tools_str if not self.case_sensitive \
                   else self.entity in tools_str
        
        passed = found or in_tools
        
        return AssertionOutcome(
            assertion_name=self.name,
            result=AssertionResult.PASSED if passed else AssertionResult.FAILED,
            message=f"Entity '{self.entity}' found" if passed 
                    else f"Entity '{self.entity}' not found in response",
            details={
                "in_response": found,
                "in_tools": in_tools
            }
        )


class ContainsAnyEntity(Assertion):
    """Assert that response mentions at least one of several entities."""
    
    def __init__(self, entities: List[str]):
        """
        Args:
            entities: List of entities, at least one must be present
        """
        self.entities = entities
    
    @property
    def name(self) -> str:
        return "contains_any_entity"
    
    def check(
        self, 
        response: str, 
        tool_results: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> AssertionOutcome:
        """Check that response mentions at least one entity."""
        
        response_lower = response.lower()
        found = []
        
        for entity in self.entities:
            if entity.lower() in response_lower:
                found.append(entity)
        
        passed = len(found) > 0
        
        return AssertionOutcome(
            assertion_name=self.name,
            result=AssertionResult.PASSED if passed else AssertionResult.FAILED,
            message=f"Found entities: {found}" if passed 
                    else f"None of {self.entities[:3]}... found",
            details={"found": found, "expected_any": self.entities}
        )


# =============================================================================
# Numeric Assertions
# =============================================================================

class HasNumericValue(Assertion):
    """Assert that response contains numeric values."""
    
    def __init__(
        self, 
        min_count: int = 1,
        value_range: Optional[tuple] = None
    ):
        """
        Args:
            min_count: Minimum number of numeric values expected
            value_range: Optional (min, max) range for values
        """
        self.min_count = min_count
        self.value_range = value_range
    
    @property
    def name(self) -> str:
        return "has_numeric_value"
    
    def check(
        self, 
        response: str, 
        tool_results: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> AssertionOutcome:
        """Check that response contains numeric values."""
        
        # Find all numbers in response
        number_pattern = r'\b\d+\.?\d*\b'
        numbers = re.findall(number_pattern, response)
        numbers = [float(n) for n in numbers if n]
        
        has_enough = len(numbers) >= self.min_count
        
        # Check value range if specified
        in_range = True
        out_of_range = []
        if self.value_range and numbers:
            min_val, max_val = self.value_range
            for n in numbers:
                if n < min_val or n > max_val:
                    in_range = False
                    out_of_range.append(n)
        
        passed = has_enough and in_range
        
        return AssertionOutcome(
            assertion_name=self.name,
            result=AssertionResult.PASSED if passed else AssertionResult.FAILED,
            message=f"Found {len(numbers)} numeric values" if passed 
                    else f"Expected at least {self.min_count} values, found {len(numbers)}",
            details={
                "count": len(numbers),
                "sample_values": numbers[:10],
                "out_of_range": out_of_range[:5] if out_of_range else None
            }
        )


class HasAssociationScore(Assertion):
    """Assert that response contains association/confidence scores."""
    
    @property
    def name(self) -> str:
        return "has_association_score"
    
    def check(
        self, 
        response: str, 
        tool_results: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> AssertionOutcome:
        """Check for association scores in response."""
        
        # Look for score patterns
        score_patterns = [
            r'(?:score|association|confidence)[:\s]+(\d+\.?\d*)',
            r'(\d+\.?\d*)\s*(?:score|association|confidence)',
            r'0\.\d{2,4}',  # Decimal scores like 0.85
        ]
        
        scores = []
        for pattern in score_patterns:
            matches = re.findall(pattern, response.lower())
            for m in matches:
                try:
                    val = float(m) if isinstance(m, str) else float(m[0]) if m else 0
                    if 0 <= val <= 1:
                        scores.append(val)
                except (ValueError, IndexError):
                    pass
        
        # Also check tool results
        for tool_name, result in tool_results.items():
            if isinstance(result, dict):
                data = result.get("data", result)
                if isinstance(data, dict):
                    score = data.get("association_score") or data.get("score")
                    if score and isinstance(score, (int, float)):
                        scores.append(score)
        
        passed = len(scores) > 0
        
        return AssertionOutcome(
            assertion_name=self.name,
            result=AssertionResult.PASSED if passed else AssertionResult.FAILED,
            message=f"Found {len(scores)} association scores" if passed 
                    else "No association scores found",
            details={"scores": scores[:10]}
        )


# =============================================================================
# Response Quality Assertions
# =============================================================================

class ResponseLength(Assertion):
    """Assert response length is within bounds."""
    
    def __init__(self, min_words: int = 10, max_words: int = 500):
        """
        Args:
            min_words: Minimum word count
            max_words: Maximum word count
        """
        self.min_words = min_words
        self.max_words = max_words
    
    @property
    def name(self) -> str:
        return "response_length"
    
    def check(
        self, 
        response: str, 
        tool_results: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> AssertionOutcome:
        """Check response length."""
        
        word_count = len(response.split())
        in_range = self.min_words <= word_count <= self.max_words
        
        return AssertionOutcome(
            assertion_name=self.name,
            result=AssertionResult.PASSED if in_range else AssertionResult.FAILED,
            message=f"Response has {word_count} words" if in_range 
                    else f"Response has {word_count} words (expected {self.min_words}-{self.max_words})",
            details={"word_count": word_count}
        )


class HasStructuredData(Assertion):
    """Assert response contains structured data (tables, lists)."""
    
    @property
    def name(self) -> str:
        return "has_structured_data"
    
    def check(
        self, 
        response: str, 
        tool_results: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> AssertionOutcome:
        """Check for structured data in response."""
        
        # Look for markdown tables
        has_table = bool(re.search(r'\|.*\|.*\|', response))
        
        # Look for markdown lists
        has_list = bool(re.search(r'^[\-\*]\s', response, re.MULTILINE))
        
        # Look for numbered lists
        has_numbered = bool(re.search(r'^\d+\.\s', response, re.MULTILINE))
        
        passed = has_table or has_list or has_numbered
        
        return AssertionOutcome(
            assertion_name=self.name,
            result=AssertionResult.PASSED if passed else AssertionResult.FAILED,
            message="Found structured data" if passed 
                    else "No tables or lists found in response",
            details={
                "has_table": has_table,
                "has_bullet_list": has_list,
                "has_numbered_list": has_numbered
            }
        )


class NoHallucination(Assertion):
    """Assert that numeric values in response come from tool results."""
    
    @property
    def name(self) -> str:
        return "no_hallucination"
    
    def check(
        self, 
        response: str, 
        tool_results: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> AssertionOutcome:
        """Check for potential hallucinated numbers."""
        
        # Extract numbers from response
        response_numbers = set()
        for match in re.findall(r'\b(\d+\.?\d*)\b', response):
            try:
                val = float(match)
                # Skip common numbers
                if val > 10 and val not in {100, 1000, 10000}:
                    response_numbers.add(round(val, 2))
            except ValueError:
                pass
        
        # Extract numbers from tool results
        tool_numbers = set()
        def extract_numbers(obj, depth=0):
            if depth > 10:
                return
            if isinstance(obj, (int, float)) and obj > 10:
                tool_numbers.add(round(obj, 2))
            elif isinstance(obj, dict):
                for v in obj.values():
                    extract_numbers(v, depth + 1)
            elif isinstance(obj, list):
                for item in obj:
                    extract_numbers(item, depth + 1)
        
        extract_numbers(tool_results)
        
        # Find numbers in response not in tools
        potentially_hallucinated = response_numbers - tool_numbers
        
        # Allow some tolerance for percentage conversions, rounding
        suspicious = []
        for num in potentially_hallucinated:
            # Check if it could be a reasonable transformation
            is_percentage = any(abs(num - t * 100) < 1 for t in tool_numbers if t <= 1)
            is_rounded = any(abs(num - t) < 1 for t in tool_numbers)
            if not is_percentage and not is_rounded:
                suspicious.append(num)
        
        passed = len(suspicious) <= 2  # Allow some tolerance
        
        return AssertionOutcome(
            assertion_name=self.name,
            result=AssertionResult.PASSED if passed else AssertionResult.FAILED,
            message="No obvious hallucinations" if passed 
                    else f"Found {len(suspicious)} potentially hallucinated values",
            details={
                "suspicious_values": list(suspicious)[:10],
                "response_numbers": list(response_numbers)[:10],
                "tool_numbers_sample": list(tool_numbers)[:10]
            }
        )


# =============================================================================
# Assertion Builder
# =============================================================================

def create_standard_assertions() -> List[Assertion]:
    """Create a standard set of assertions for general queries."""
    return [
        HasProvenance(),
        HasNumericValue(min_count=1),
        ResponseLength(min_words=20, max_words=500),
        NoHallucination(),
    ]


def create_evidence_assertions(
    target: Optional[str] = None,
    disease: Optional[str] = None
) -> List[Assertion]:
    """Create assertions for evidence/target validation queries."""
    assertions = [
        HasProvenance(),
        SourceIs("Open Targets"),
        HasAssociationScore(),
        HasStructuredData(),
        NoHallucination(),
    ]
    
    if target:
        assertions.append(ContainsEntity(target))
    if disease:
        assertions.append(ContainsEntity(disease))
    
    return assertions


def create_compound_assertions(
    compound_name: Optional[str] = None
) -> List[Assertion]:
    """Create assertions for compound lookup queries."""
    assertions = [
        HasProvenance(),
        HasNumericValue(min_count=2),  # MW, LogP, etc.
        ResponseLength(min_words=30, max_words=500),
        NoHallucination(),
    ]
    
    if compound_name:
        assertions.append(ContainsEntity(compound_name))
    
    return assertions
