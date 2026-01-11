"""
Custom exception hierarchy for ChemAgent.

Provides specific error types with helpful suggestions for common failures.
"""

from typing import Optional


class ChemAgentError(Exception):
    """
    Base exception for all ChemAgent errors.
    
    All custom exceptions inherit from this class.
    """
    
    def __init__(self, message: str, suggestion: Optional[str] = None):
        """
        Initialize exception.
        
        Args:
            message: Error message
            suggestion: Optional suggestion for fixing the error
        """
        super().__init__(message)
        self.suggestion = suggestion
    
    def __str__(self) -> str:
        """String representation with suggestion."""
        msg = super().__str__()
        if self.suggestion:
            msg += f"\n💡 Suggestion: {self.suggestion}"
        return msg


# =============================================================================
# Chemistry Errors
# =============================================================================

class InvalidSMILESError(ChemAgentError):
    """Invalid SMILES string provided."""
    
    def __init__(self, smiles: str, details: Optional[str] = None):
        """
        Initialize with SMILES string.
        
        Args:
            smiles: The invalid SMILES string
            details: Optional details about the error
        """
        self.smiles = smiles
        message = f"Invalid SMILES: {smiles}"
        if details:
            message += f" ({details})"
        
        suggestion = "Check for typos, ensure proper syntax, or use a molecule drawing tool"
        super().__init__(message, suggestion)


class InvalidInChIError(ChemAgentError):
    """Invalid InChI string provided."""
    
    def __init__(self, inchi: str):
        """Initialize with InChI string."""
        self.inchi = inchi
        message = f"Invalid InChI: {inchi}"
        suggestion = "Verify InChI format or convert from SMILES first"
        super().__init__(message, suggestion)


class MoleculeParsingError(ChemAgentError):
    """Failed to parse molecular structure."""
    
    def __init__(self, structure: str, format_type: str = "unknown"):
        """
        Initialize with structure and format.
        
        Args:
            structure: The structure string that failed to parse
            format_type: The format type (SMILES, InChI, MOL, etc.)
        """
        self.structure = structure
        self.format_type = format_type
        message = f"Failed to parse {format_type}: {structure[:50]}"
        suggestion = f"Verify the {format_type} format is correct"
        super().__init__(message, suggestion)


# =============================================================================
# Database Errors
# =============================================================================

class CompoundNotFoundError(ChemAgentError):
    """Compound lookup failed."""
    
    def __init__(self, identifier: str, database: str = "ChEMBL"):
        """
        Initialize with compound identifier.
        
        Args:
            identifier: The compound identifier
            database: The database name
        """
        self.identifier = identifier
        self.database = database
        message = f"Compound not found in {database}: {identifier}"
        suggestion = "Try alternative names, synonyms, or use ChEMBL ID format (e.g., CHEMBL25)"
        super().__init__(message, suggestion)


class TargetNotFoundError(ChemAgentError):
    """Target lookup failed."""
    
    def __init__(self, identifier: str, database: str = "ChEMBL"):
        """Initialize with target identifier."""
        self.identifier = identifier
        self.database = database
        message = f"Target not found in {database}: {identifier}"
        suggestion = "Try alternative target names or UniProt accession"
        super().__init__(message, suggestion)


class ProteinNotFoundError(ChemAgentError):
    """Protein lookup failed."""
    
    def __init__(self, identifier: str):
        """Initialize with protein identifier."""
        self.identifier = identifier
        message = f"Protein not found: {identifier}"
        suggestion = "Verify UniProt ID or try searching by protein name"
        super().__init__(message, suggestion)


class DatabaseConnectionError(ChemAgentError):
    """Failed to connect to external database."""
    
    def __init__(self, database: str, reason: Optional[str] = None):
        """
        Initialize with database name.
        
        Args:
            database: Database name
            reason: Optional reason for failure
        """
        self.database = database
        message = f"Failed to connect to {database}"
        if reason:
            message += f": {reason}"
        suggestion = "Check internet connection and database service status"
        super().__init__(message, suggestion)


class RateLimitError(ChemAgentError):
    """API rate limit exceeded."""
    
    def __init__(self, database: str, retry_after: Optional[int] = None):
        """
        Initialize with database and retry time.
        
        Args:
            database: Database name
            retry_after: Seconds until retry is allowed
        """
        self.database = database
        self.retry_after = retry_after
        
        message = f"Rate limit exceeded for {database}"
        if retry_after:
            suggestion = f"Wait {retry_after} seconds before retrying"
        else:
            suggestion = "Wait a few seconds before retrying or enable caching"
        
        super().__init__(message, suggestion)


# =============================================================================
# Query Processing Errors
# =============================================================================

class QueryParsingError(ChemAgentError):
    """Failed to parse natural language query."""
    
    def __init__(self, query: str, reason: Optional[str] = None):
        """
        Initialize with query string.
        
        Args:
            query: The query that failed to parse
            reason: Optional reason for failure
        """
        self.query = query
        message = f"Failed to parse query: {query}"
        if reason:
            message += f" ({reason})"
        suggestion = "Try rephrasing or being more specific (e.g., 'What is CHEMBL25?' or 'Calculate properties of CCO')"
        super().__init__(message, suggestion)


class UnknownIntentError(ChemAgentError):
    """Could not determine intent from query."""
    
    def __init__(self, query: str):
        """Initialize with query string."""
        self.query = query
        message = f"Could not understand query: {query}"
        suggestion = "Try a more specific query like 'Find compounds similar to aspirin' or 'Calculate properties of CC(=O)O'"
        super().__init__(message, suggestion)


class PlanGenerationError(ChemAgentError):
    """Failed to generate execution plan."""
    
    def __init__(self, intent_type: str, reason: Optional[str] = None):
        """
        Initialize with intent type.
        
        Args:
            intent_type: The intent type
            reason: Optional reason for failure
        """
        self.intent_type = intent_type
        message = f"Failed to create plan for {intent_type}"
        if reason:
            message += f": {reason}"
        suggestion = "Ensure all required parameters are present in the query"
        super().__init__(message, suggestion)


# =============================================================================
# Execution Errors
# =============================================================================

class ToolExecutionError(ChemAgentError):
    """Tool execution failed."""
    
    def __init__(self, tool_name: str, reason: str):
        """
        Initialize with tool name and reason.
        
        Args:
            tool_name: Name of the tool
            reason: Reason for failure
        """
        self.tool_name = tool_name
        message = f"Tool '{tool_name}' failed: {reason}"
        suggestion = "Check tool inputs and try again"
        super().__init__(message, suggestion)


class ToolNotFoundError(ChemAgentError):
    """Requested tool not found in registry."""
    
    def __init__(self, tool_name: str, available_tools: Optional[list] = None):
        """
        Initialize with tool name.
        
        Args:
            tool_name: Name of the missing tool
            available_tools: Optional list of available tools
        """
        self.tool_name = tool_name
        self.available_tools = available_tools
        
        message = f"Tool not found: {tool_name}"
        if available_tools:
            suggestion = f"Available tools: {', '.join(available_tools[:5])}"
        else:
            suggestion = "Ensure tool is registered in ToolRegistry"
        
        super().__init__(message, suggestion)


class ExecutionTimeoutError(ChemAgentError):
    """Query execution timed out."""
    
    def __init__(self, timeout_seconds: int):
        """
        Initialize with timeout duration.
        
        Args:
            timeout_seconds: Timeout duration
        """
        self.timeout_seconds = timeout_seconds
        message = f"Query execution timed out after {timeout_seconds} seconds"
        suggestion = "Try a simpler query or increase timeout limit"
        super().__init__(message, suggestion)


class DependencyError(ChemAgentError):
    """Step dependency not satisfied."""
    
    def __init__(self, step_id: int, missing_dependency: int):
        """
        Initialize with step IDs.
        
        Args:
            step_id: Current step ID
            missing_dependency: Missing dependency step ID
        """
        self.step_id = step_id
        self.missing_dependency = missing_dependency
        message = f"Step {step_id} depends on step {missing_dependency} which failed"
        suggestion = "Check execution logs for the failed dependency"
        super().__init__(message, suggestion)


# =============================================================================
# Configuration Errors
# =============================================================================

class ConfigurationError(ChemAgentError):
    """Invalid configuration."""
    
    def __init__(self, parameter: str, reason: str):
        """
        Initialize with parameter and reason.
        
        Args:
            parameter: Configuration parameter name
            reason: Why it's invalid
        """
        self.parameter = parameter
        message = f"Invalid configuration for '{parameter}': {reason}"
        suggestion = "Check configuration file or environment variables"
        super().__init__(message, suggestion)


class MissingDependencyError(ChemAgentError):
    """Required dependency not installed."""
    
    def __init__(self, package: str, feature: str):
        """
        Initialize with package name and feature.
        
        Args:
            package: Missing package name
            feature: Feature that requires it
        """
        self.package = package
        self.feature = feature
        message = f"Missing dependency '{package}' required for {feature}"
        suggestion = f"Install with: pip install {package}"
        super().__init__(message, suggestion)


# =============================================================================
# Cache Errors
# =============================================================================

class CacheError(ChemAgentError):
    """Cache operation failed."""
    
    def __init__(self, operation: str, reason: str):
        """
        Initialize with operation and reason.
        
        Args:
            operation: Cache operation (get, set, clear, etc.)
            reason: Reason for failure
        """
        self.operation = operation
        message = f"Cache {operation} failed: {reason}"
        suggestion = "Check cache directory permissions or disk space"
        super().__init__(message, suggestion)


# =============================================================================
# Validation Errors
# =============================================================================

class ValidationError(ChemAgentError):
    """Input validation failed."""
    
    def __init__(self, field: str, value: any, reason: str):
        """
        Initialize with field, value, and reason.
        
        Args:
            field: Field name
            value: Invalid value
            reason: Why it's invalid
        """
        self.field = field
        self.value = value
        message = f"Invalid {field}: {value} ({reason})"
        suggestion = f"Provide valid {field} value"
        super().__init__(message, suggestion)


# =============================================================================
# Export
# =============================================================================

__all__ = [
    # Base
    "ChemAgentError",
    
    # Chemistry
    "InvalidSMILESError",
    "InvalidInChIError",
    "MoleculeParsingError",
    
    # Database
    "CompoundNotFoundError",
    "TargetNotFoundError",
    "ProteinNotFoundError",
    "DatabaseConnectionError",
    "RateLimitError",
    
    # Query Processing
    "QueryParsingError",
    "UnknownIntentError",
    "PlanGenerationError",
    
    # Execution
    "ToolExecutionError",
    "ToolNotFoundError",
    "ExecutionTimeoutError",
    "DependencyError",
    
    # Configuration
    "ConfigurationError",
    "MissingDependencyError",
    
    # Cache
    "CacheError",
    
    # Validation
    "ValidationError",
]
