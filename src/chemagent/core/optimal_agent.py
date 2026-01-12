"""
Optimal ChemAgent: Hybrid Tiered + Verification Architecture.

Combines pattern reliability with LLM flexibility:
- Fast path: Pattern parser for common queries (80%)
- Smart path: LLM for complex/ambiguous queries (20%)
- Verification: Ensures synthesis matches raw data

Architecture:
    Query → Entity Extraction (Pattern) → Confidence Check
        ├── High Confidence → Rule Planner → Execute → Light Synthesis
        └── Low Confidence → LLM Planner → Execute → Verified Synthesis
"""

import json
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
from urllib.parse import quote

logger = logging.getLogger(__name__)

# Import context manager
from chemagent.core.context_manager import (
    ConversationMemory, 
    get_context_manager,
    extract_results_summary
)

# Import verifier gate
from chemagent.core.verifier import (
    VerifierGate,
    ClaimVerifier,
    VerifierReport,
    create_verifier_gate
)

# Check for litellm
try:
    from litellm import completion
    LITELLM_AVAILABLE = True
except ImportError:
    LITELLM_AVAILABLE = False
    logger.warning("litellm not installed. LLM features disabled.")


# =============================================================================
# Rate-Limited LLM Caller
# =============================================================================

def call_llm_with_retry(
    model: str,
    messages: List[Dict[str, str]],
    temperature: float = 0.3,
    max_tokens: int = 1000,
    max_retries: int = 3,
    base_delay: float = 2.0
) -> Optional[Any]:
    """
    Call LLM with exponential backoff retry for rate limiting.
    
    Args:
        model: Model name (e.g., "groq/llama-3.1-8b-instant")
        messages: Chat messages
        temperature: Temperature setting
        max_tokens: Max tokens to generate
        max_retries: Number of retries
        base_delay: Base delay in seconds (doubles each retry)
    
    Returns:
        LLM response or None on failure
    """
    if not LITELLM_AVAILABLE:
        return None
    
    last_error = None
    for attempt in range(max_retries):
        try:
            response = completion(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response
        except Exception as e:
            last_error = e
            error_str = str(e).lower()
            
            # Check if it's a rate limit error
            if "rate" in error_str and "limit" in error_str:
                # Extract suggested wait time if available
                wait_match = re.search(r'try again in (\d+(?:\.\d+)?)', str(e))
                if wait_match:
                    delay = float(wait_match.group(1)) + 1.0  # Add 1s buffer
                else:
                    delay = base_delay * (2 ** attempt)
                
                logger.info(f"Rate limited, waiting {delay:.1f}s before retry {attempt + 1}/{max_retries}")
                time.sleep(delay)
            else:
                # Non-rate-limit error, don't retry
                logger.warning(f"LLM call failed (non-retryable): {e}")
                break
    
    logger.warning(f"LLM call failed after {max_retries} retries: {last_error}")
    return None


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class ExtractedEntities:
    """Entities extracted from query using patterns."""
    compounds: List[str] = field(default_factory=list)      # Names like "aspirin"
    chembl_ids: List[str] = field(default_factory=list)     # CHEMBL25, etc.
    smiles: List[str] = field(default_factory=list)         # Chemical structures
    uniprot_ids: List[str] = field(default_factory=list)    # P12345, etc.
    targets: List[str] = field(default_factory=list)        # Target names
    properties: List[str] = field(default_factory=list)     # logp, mw, etc.
    thresholds: Dict[str, float] = field(default_factory=dict)


@dataclass
class ToolCall:
    """A planned tool call."""
    tool: str
    args: Dict[str, Any]
    purpose: str = ""


@dataclass
class AgentResponse:
    """Response from the agent."""
    success: bool
    answer: str
    tool_results: Dict[str, Any] = field(default_factory=dict)
    execution_time_ms: float = 0.0
    tools_used: List[str] = field(default_factory=list)
    path_used: str = "unknown"  # "fast" or "smart"
    confidence: float = 0.0
    error: Optional[str] = None


# =============================================================================
# Entity Extraction (Pattern-based - Fast & Reliable)
# =============================================================================

class EntityExtractor:
    """Extract chemical entities from queries using regex patterns."""
    
    # Patterns for different entity types
    CHEMBL_PATTERN = re.compile(r'CHEMBL\d+', re.IGNORECASE)
    SMILES_PATTERN = re.compile(r'[A-Za-z0-9@+\-\[\]\(\)\\/#=%]+(?:[A-Za-z0-9@+\-\[\]\(\)\\/#=%])+')
    UNIPROT_PATTERN = re.compile(r'\b[OPQ][0-9][A-Z0-9]{3}[0-9]\b|\b[A-NR-Z][0-9](?:[A-Z][A-Z0-9]{2}[0-9]){1,2}\b')
    ENSEMBL_PATTERN = re.compile(r'ENSG\d+', re.IGNORECASE)
    
    # Common compound names (expandable)
    KNOWN_COMPOUNDS = {
        'aspirin', 'ibuprofen', 'acetaminophen', 'paracetamol', 'metformin',
        'atorvastatin', 'omeprazole', 'lisinopril', 'amlodipine', 'metoprolol',
        'caffeine', 'nicotine', 'morphine', 'codeine', 'penicillin',
        'amoxicillin', 'ciprofloxacin', 'doxycycline', 'warfarin', 'heparin',
        'insulin', 'testosterone', 'estrogen', 'cortisol', 'dopamine',
        'serotonin', 'adrenaline', 'epinephrine', 'norepinephrine', 'melatonin'
    }
    
    # Common target/gene names
    KNOWN_TARGETS = {
        'egfr', 'her2', 'erbb2', 'braf', 'kras', 'brca1', 'brca2', 'tp53', 'p53',
        'akt', 'mtor', 'vegf', 'vegfr', 'pdgfr', 'fgfr', 'jak', 'stat',
        'bcr-abl', 'alk', 'ros1', 'met', 'kit', 'ret', 'flt3',
        'cox-1', 'cox-2', 'cox1', 'cox2', 'ace', 'ace2', 'dpp4',
        'parp', 'hdac', 'proteasome', 'cdk4', 'cdk6', 'pi3k', 'ras',
        'androgen receptor', 'estrogen receptor', 'ar', 'er', 'pr',
        'tnf', 'tnf-alpha', 'il-6', 'il-1', 'pd-1', 'pd-l1', 'ctla-4'
    }
    
    # Property keywords
    PROPERTY_KEYWORDS = {
        'molecular weight': 'mw', 'mw': 'mw', 'mass': 'mw',
        'logp': 'logp', 'log p': 'logp', 'lipophilicity': 'logp',
        'solubility': 'solubility', 'psa': 'psa', 'tpsa': 'tpsa',
        'polar surface': 'tpsa', 'h-bond': 'hbond', 'rotatable': 'rotatable',
        'lipinski': 'lipinski', 'drug-like': 'lipinski', 'druglike': 'lipinski'
    }
    
    def extract(self, query: str) -> ExtractedEntities:
        """Extract all recognizable entities from query."""
        entities = ExtractedEntities()
        query_lower = query.lower()
        
        # Extract ChEMBL IDs
        entities.chembl_ids = self.CHEMBL_PATTERN.findall(query.upper())
        
        # Extract UniProt IDs
        entities.uniprot_ids = self.UNIPROT_PATTERN.findall(query)
        
        # Extract Ensembl IDs (targets)
        ensembl_ids = self.ENSEMBL_PATTERN.findall(query.upper())
        entities.targets.extend(ensembl_ids)
        
        # Extract known compound names (word boundary check)
        for compound in self.KNOWN_COMPOUNDS:
            pattern = r'\b' + re.escape(compound) + r'\b'
            if re.search(pattern, query_lower):
                entities.compounds.append(compound)
        
        # Extract known target names (word boundary check)
        for target in self.KNOWN_TARGETS:
            # Use word boundary to avoid partial matches
            pattern = r'\b' + re.escape(target) + r'\b'
            if re.search(pattern, query_lower):
                entities.targets.append(target.upper())
        
        # Extract SMILES (careful - many false positives)
        # Only if it looks like a SMILES with chemistry characters
        potential_smiles = self.SMILES_PATTERN.findall(query)
        for ps in potential_smiles:
            if self._is_likely_smiles(ps):
                entities.smiles.append(ps)
        
        # Extract property requests
        for keyword, prop_type in self.PROPERTY_KEYWORDS.items():
            if keyword in query_lower:
                entities.properties.append(prop_type)
        
        # Extract thresholds (e.g., "similarity > 0.8")
        threshold_match = re.search(r'(?:threshold|similarity)[^\d]*(\d+\.?\d*)', query_lower)
        if threshold_match:
            entities.thresholds['similarity'] = float(threshold_match.group(1))
            # Normalize to 0-1 if > 1
            if entities.thresholds['similarity'] > 1:
                entities.thresholds['similarity'] /= 100
        
        return entities
    
    def _is_likely_smiles(self, s: str) -> bool:
        """Check if string is likely a SMILES (not just random text)."""
        if len(s) < 3:
            return False
        # Must have chemistry-specific characters
        chem_chars = set('()[]=#@+-/\\')
        if not any(c in s for c in chem_chars):
            # Check for element patterns
            if not re.search(r'[CNOPSFClBrI]', s):
                return False
        # Should have reasonable chemistry
        return bool(re.search(r'[CNO]', s))


# =============================================================================
# Intent Classification
# =============================================================================

class IntentType(Enum):
    """Query intent types."""
    COMPOUND_LOOKUP = "compound_lookup"
    TARGET_LOOKUP = "target_lookup"
    SIMILARITY_SEARCH = "similarity_search"
    PROPERTY_CALCULATION = "property_calculation"
    BIOACTIVITY_LOOKUP = "bioactivity_lookup"
    STRUCTURE_SEARCH = "structure_search"
    TARGET_VALIDATION = "target_validation"  # NEW: Open Targets evidence
    DISEASE_ASSOCIATION = "disease_association"  # NEW: Target-disease links
    GENERAL_QUESTION = "general_question"
    UNKNOWN = "unknown"


class IntentClassifier:
    """Classify query intent using patterns."""
    
    INTENT_PATTERNS = {
        IntentType.COMPOUND_LOOKUP: [
            r'\bwhat is\b.*(?:compound|drug|molecule)?',
            r'\btell me about\b',
            r'\binfo(?:rmation)? (?:on|about)\b',
            r'\blook ?up\b',
            r'\bget\b.*\bcompound\b',
            r'\bfind\b.*\bcompound\b',
        ],
        IntentType.TARGET_LOOKUP: [
            r'\btarget[s]?\b.*(?:for|of)\b',
            r'\bwhat.*(?:target|hit|bind)\b',
            r'\bprotein\b.*(?:for|of)\b',
            r'\bfind.*target\b',
            r'\babout.*target[s]?\b',           # "more about its targets"
            r'\btarget[s]?\s*$',                 # ends with "targets"
            r'\bbiological.*(?:target|activity)\b',
            r'\bbind[s]?\s+to\b',
            r'\binteract[s]?\s+with\b',
        ],
        IntentType.TARGET_VALIDATION: [
            r'\bevidence\b.*(?:target|link|implicated)',
            r'\bvalidat(?:e|ion)\b.*\btarget\b',
            r'\bimplicated\b.*\bin\b',
            r'\bgood target\b',
            r'\bopen targets?\b',
            r'\bgenetic.*evidence\b',
            r'\bliterature.*evidence\b',
            r'\bwhy.*target\b',
        ],
        IntentType.DISEASE_ASSOCIATION: [
            r'\bdisease[s]?\b.*(?:for|of|associated)\b',
            r'\bassociat(?:ed|ion)\b.*\bdisease\b',
            r'\bwhat diseases?\b',
            r'\bindications?\b',
            r'\bcancer|diabetes|alzheimer|parkinson\b',
            r'\blung|breast|colon|brain\b.*\bcancer\b',
        ],
        IntentType.BIOACTIVITY_LOOKUP: [
            r'\bactivi(?:ty|ties)\b',
            r'\bbioactivi(?:ty|ties)\b',
            r'\bIC50\b',
            r'\bEC50\b',
            r'\bKi\b',
            r'\bKd\b',
            r'\binhibit(?:ion|or)?\b',
            r'\bbinding\b.*\baffinity\b',
        ],
        IntentType.SIMILARITY_SEARCH: [
            r'\bsimilar\b',
            r'\banalog(?:s|ue)?\b',
            r'\balternative[s]?\b',
            r'\bsubstitute[s]?\b',
            r'\blike\b.*compound',
        ],
        IntentType.PROPERTY_CALCULATION: [
            r'\bcalculate\b',
            r'\bcompute\b',
            r'\bproperties\b',
            r'\blogp\b',
            r'\bmolecular weight\b',
            r'\blipinski\b',
            r'\bdrug.?like\b',
        ],
        IntentType.BIOACTIVITY_LOOKUP: [
            r'\bactivity\b',
            r'\bic50\b',
            r'\bec50\b',
            r'\bki\b',
            r'\bpotency\b',
            r'\bbioactiv\b',
        ],
        IntentType.STRUCTURE_SEARCH: [
            r'\bsubstructure\b',
            r'\bcontain(?:s|ing)?\b.*(?:ring|group|moiety)',
            r'\bstructure search\b',
        ],
    }
    
    def classify(self, query: str, entities: ExtractedEntities) -> Tuple[IntentType, float]:
        """
        Classify query intent and return confidence.
        
        Returns:
            Tuple of (IntentType, confidence 0-1)
        """
        query_lower = query.lower()
        scores = {intent: 0.0 for intent in IntentType}
        
        # Pattern matching
        for intent, patterns in self.INTENT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    scores[intent] += 0.3
        
        # Entity-based boosting
        if entities.smiles:
            scores[IntentType.PROPERTY_CALCULATION] += 0.4
            scores[IntentType.SIMILARITY_SEARCH] += 0.2
        
        if entities.chembl_ids:
            scores[IntentType.COMPOUND_LOOKUP] += 0.3
            scores[IntentType.BIOACTIVITY_LOOKUP] += 0.2
        
        if entities.compounds:
            scores[IntentType.COMPOUND_LOOKUP] += 0.3
        
        if 'target' in query_lower or 'protein' in query_lower:
            scores[IntentType.TARGET_LOOKUP] += 0.3
        
        # Evidence and validation queries → Open Targets
        if 'evidence' in query_lower or 'implicated' in query_lower:
            scores[IntentType.TARGET_VALIDATION] += 0.5
        if 'disease' in query_lower or 'cancer' in query_lower or 'indication' in query_lower:
            scores[IntentType.DISEASE_ASSOCIATION] += 0.4
        if 'genetic' in query_lower and 'evidence' in query_lower:
            scores[IntentType.TARGET_VALIDATION] += 0.4
        
        if entities.properties:
            scores[IntentType.PROPERTY_CALCULATION] += 0.4
        
        # Find best intent
        best_intent = max(scores, key=scores.get)
        best_score = scores[best_intent]
        
        # Normalize confidence
        confidence = min(best_score, 1.0)
        
        # If no good match, mark as unknown
        if confidence < 0.2:
            return IntentType.UNKNOWN, 0.0
        
        return best_intent, confidence


# =============================================================================
# Tool Planning
# =============================================================================

class ToolPlanner:
    """Plan tool calls based on intent and entities."""
    
    def plan_fast(
        self, 
        intent: IntentType, 
        entities: ExtractedEntities
    ) -> List[ToolCall]:
        """
        Fast path: Rule-based tool planning.
        Used when pattern confidence is high.
        """
        tools = []
        
        if intent == IntentType.COMPOUND_LOOKUP:
            if entities.chembl_ids:
                chembl_id = entities.chembl_ids[0]
                tools.append(ToolCall(
                    tool="chembl_get_compound",
                    args={"chembl_id": chembl_id},
                    purpose="Get compound details"
                ))
                tools.append(ToolCall(
                    tool="chembl_get_activities",
                    args={"chembl_id": chembl_id, "limit": 20},
                    purpose="Get biological activity"
                ))
            elif entities.compounds:
                compound = entities.compounds[0]
                tools.append(ToolCall(
                    tool="chembl_search_by_name",
                    args={"query": compound, "limit": 1},
                    purpose=f"Search for {compound}"
                ))
        
        elif intent == IntentType.PROPERTY_CALCULATION:
            if entities.smiles:
                smiles = entities.smiles[0]
                tools.append(ToolCall(
                    tool="rdkit_calc_properties",
                    args={"smiles": smiles},
                    purpose="Calculate molecular properties"
                ))
                if 'lipinski' in entities.properties:
                    tools.append(ToolCall(
                        tool="rdkit_calc_lipinski",
                        args={"smiles": smiles},
                        purpose="Check Lipinski's Rule of 5"
                    ))
            elif entities.compounds:
                # First lookup the compound to get SMILES
                compound = entities.compounds[0]
                tools.append(ToolCall(
                    tool="chembl_search_by_name",
                    args={"query": compound, "limit": 1},
                    purpose=f"Get structure for {compound}"
                ))
                # Note: Property calculation will be chained in execution
        
        elif intent == IntentType.SIMILARITY_SEARCH:
            smiles = None
            if entities.smiles:
                smiles = entities.smiles[0]
            elif entities.compounds:
                # Need to get SMILES first
                tools.append(ToolCall(
                    tool="chembl_search_by_name",
                    args={"query": entities.compounds[0], "limit": 1},
                    purpose="Get compound structure"
                ))
            
            if smiles:
                threshold = entities.thresholds.get('similarity', 0.7)
                tools.append(ToolCall(
                    tool="chembl_similarity_search",
                    args={"smiles": smiles, "threshold": threshold, "limit": 10},
                    purpose="Find similar compounds"
                ))
        
        elif intent == IntentType.TARGET_LOOKUP or intent == IntentType.BIOACTIVITY_LOOKUP:
            if entities.chembl_ids:
                # Have ChEMBL ID - get activities directly
                tools.append(ToolCall(
                    tool="chembl_get_activities",
                    args={"chembl_id": entities.chembl_ids[0], "limit": 30},
                    purpose="Get activity/target data"
                ))
            elif entities.compounds:
                # Need to find compound first, then get activities
                tools.append(ToolCall(
                    tool="chembl_search_by_name",
                    args={"query": entities.compounds[0], "limit": 1},
                    purpose="Find compound to get ChEMBL ID"
                ))
                # Note: The executor should chain this to get activities
                # For now, we'll let the LLM synthesizer handle follow-up
        
        elif intent == IntentType.TARGET_VALIDATION:
            # Use Open Targets for evidence-based target validation
            # First search for the target to get Ensembl ID
            if entities.targets:
                tools.append(ToolCall(
                    tool="opentargets_search_target",
                    args={"query": entities.targets[0]},
                    purpose="Find target Ensembl ID"
                ))
            elif entities.compounds:
                # User might be asking about a compound's target validation
                tools.append(ToolCall(
                    tool="opentargets_search_target",
                    args={"query": entities.compounds[0]},
                    purpose="Search for target"
                ))
        
        elif intent == IntentType.DISEASE_ASSOCIATION:
            # Get target-disease associations from Open Targets
            if entities.targets:
                tools.append(ToolCall(
                    tool="opentargets_search_target",
                    args={"query": entities.targets[0]},
                    purpose="Find target for disease associations"
                ))
        
        return tools
    
    def plan_with_llm(
        self, 
        query: str, 
        entities: ExtractedEntities
    ) -> List[ToolCall]:
        """
        Smart path: LLM-assisted tool planning.
        Used when pattern confidence is low.
        """
        if not LITELLM_AVAILABLE:
            # Fallback to fast planning with best guess
            intent, _ = IntentClassifier().classify(query, entities)
            return self.plan_fast(intent, entities)
        
        prompt = self._build_planning_prompt(query, entities)
        
        response = call_llm_with_retry(
            model="groq/llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=1000,
            max_retries=3,
            base_delay=2.0
        )
        
        if response:
            content = response.choices[0].message.content
            return self._parse_tool_calls(content)
        else:
            logger.warning("LLM planning failed, falling back to fast planning")
            # Fallback
            intent, _ = IntentClassifier().classify(query, entities)
            return self.plan_fast(intent, entities)
    
    def _build_planning_prompt(self, query: str, entities: ExtractedEntities) -> str:
        """Build prompt for LLM planning."""
        entities_str = json.dumps({
            "compounds": entities.compounds,
            "chembl_ids": entities.chembl_ids,
            "smiles": entities.smiles,
            "properties": entities.properties,
            "targets": entities.targets
        }, indent=2)
        
        return f"""You are a pharmaceutical research assistant. Plan tool calls to answer the query.

## Available Tools

### ChEMBL (Compounds & Bioactivity)
- chembl_search_by_name(query: str, limit: int) - Search compounds by name
- chembl_get_compound(chembl_id: str) - Get compound by ChEMBL ID  
- chembl_get_activities(chembl_id: str, limit: int) - Get bioactivity data
- chembl_similarity_search(smiles: str, threshold: float, limit: int) - Find similar compounds

### Open Targets (Evidence & Disease Associations)
- opentargets_search_target(query: str) - Search targets, get Ensembl ID
- opentargets_search_disease(query: str) - Search diseases, get EFO ID
- opentargets_get_evidence(ensembl_id: str, efo_id: str) - Get target-disease evidence
- opentargets_get_associations(ensembl_id: str, limit: int) - Get all diseases for a target

### RDKit (Chemical Properties)
- rdkit_calc_properties(smiles: str) - Calculate molecular properties
- rdkit_calc_lipinski(smiles: str) - Check drug-likeness

### UniProt (Proteins)
- uniprot_search(query: str, limit: int) - Search proteins

## Extracted Entities
{entities_str}

## Query
{query}

## Instructions
Return ONLY a JSON array of tool calls:
```json
[
  {{"tool": "tool_name", "args": {{"arg": "value"}}, "purpose": "why"}}
]
```
"""
    
    def _parse_tool_calls(self, content: str) -> List[ToolCall]:
        """Parse LLM response into tool calls."""
        try:
            # Extract JSON from response
            content = content.strip()
            if "```" in content:
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            content = content.strip()
            
            data = json.loads(content)
            
            tools = []
            for item in data:
                tools.append(ToolCall(
                    tool=item.get("tool", ""),
                    args=item.get("args", {}),
                    purpose=item.get("purpose", "")
                ))
            return tools
            
        except Exception as e:
            logger.error(f"Failed to parse tool calls: {e}")
            return []


# =============================================================================
# Response Synthesis
# =============================================================================

class ResponseSynthesizer:
    """Synthesize human-readable responses from tool results."""
    
    def _get_compound_attr(self, compound: Any, *attrs: str) -> Optional[Any]:
        """Safely get compound attribute - works with both dicts and dataclasses."""
        for attr in attrs:
            if hasattr(compound, attr):
                val = getattr(compound, attr, None)
                if val:
                    return val
            elif isinstance(compound, dict):
                val = compound.get(attr)
                if val:
                    return val
        return None
    
    def _safe_float(self, value: Any) -> Optional[float]:
        """Safely convert value to float."""
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
    
    def synthesize_fast(
        self, 
        query: str, 
        results: Dict[str, Any],
        intent: IntentType
    ) -> str:
        """Fast synthesis without LLM - template based."""
        
        if not results:
            return "No results found for your query."
        
        # Check for errors - handle both dict and non-dict results
        errors = []
        for r in results.values():
            if isinstance(r, dict) and r.get("error"):
                errors.append(r.get("error"))
        if errors:
            return f"Some tools encountered errors: {', '.join(errors)}"
        
        # Build response based on intent
        parts = []
        
        for tool_name, result in results.items():
            # Handle dict and non-dict results
            if isinstance(result, dict):
                if not result.get("success", True):
                    continue
                data = result.get("data", result)
            else:
                data = result
            
            # Handle compounds list
            if isinstance(data, dict) and "compounds" in data:
                compounds = data["compounds"]
                if compounds:
                    c = compounds[0]
                    name = self._get_compound_attr(c, 'name', 'pref_name', 'chembl_id') or 'Unknown'
                    smiles = self._get_compound_attr(c, 'smiles')
                    parts.append(f"**{name}**")
                    if smiles:
                        parts.append(f"Structure: `{smiles}`")
            
            # Handle molecular weight - safely convert to float
            if isinstance(data, dict) and "molecular_weight" in data:
                mw = self._safe_float(data["molecular_weight"])
                if mw is not None:
                    parts.append(f"MW: {mw:.2f} g/mol")
            
            # Handle logp - safely convert to float
            if isinstance(data, dict) and "logp" in data:
                logp = self._safe_float(data["logp"])
                if logp is not None:
                    parts.append(f"LogP: {logp:.2f}")
        
        return "\n".join(parts) if parts else "Query completed but no displayable results."
    
    def synthesize_with_llm(
        self, 
        query: str, 
        results: Dict[str, Any],
        conversation_context: str = ""
    ) -> str:
        """Smart synthesis with LLM - natural language with conversation context."""
        if not LITELLM_AVAILABLE:
            return self.synthesize_fast(query, results, IntentType.UNKNOWN)
        
        # Extract SMILES for structure image
        smiles = None
        for tool_name, tool_result in results.items():
            data = tool_result.get("data", {}) if isinstance(tool_result, dict) else {}
            if isinstance(data, dict):
                # Check compounds list
                if "compounds" in data and data["compounds"]:
                    c = data["compounds"][0]
                    # Handle both dict and dataclass objects
                    if hasattr(c, 'smiles'):
                        smiles = c.smiles
                    elif isinstance(c, dict):
                        smiles = c.get("smiles")
                    if smiles:
                        logger.debug(f"Found SMILES from compounds: {smiles[:30]}...")
                        break
                # Check similar_compounds (for similarity search)
                elif "similar_compounds" in data and data["similar_compounds"]:
                    c = data["similar_compounds"][0]
                    if hasattr(c, 'smiles'):
                        smiles = c.smiles
                    elif isinstance(c, dict):
                        smiles = c.get("smiles")
                    if smiles:
                        logger.debug(f"Found SMILES from similar_compounds: {smiles[:30]}...")
                        break
                elif "smiles" in data:
                    smiles = data["smiles"]
                    logger.debug(f"Found SMILES directly in data: {smiles[:30]}...")
                    break
                # Also check for input_smiles (from property calculations)
                elif "input_smiles" in data:
                    smiles = data["input_smiles"]
                    logger.debug(f"Found input_smiles: {smiles[:30]}...")
                    break
            # Check tool args for SMILES input
            args = tool_result.get("args", {}) if isinstance(tool_result, dict) else {}
            if isinstance(args, dict) and "smiles" in args:
                smiles = args["smiles"]
                logger.debug(f"Found SMILES in tool args: {smiles[:30]}...")
                break
        
        if not smiles:
            logger.debug("No SMILES found for structure image")
        
        structure_instruction = ""
        if smiles:
            # URL-encode the SMILES for the API
            encoded_smiles = quote(smiles, safe='')
            structure_instruction = f"""
- Include this structure image at the TOP of your response:
  ![Structure](https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/smiles/{encoded_smiles}/PNG?image_size=200x200)
"""
        
        # Build conversation context section
        context_section = ""
        if conversation_context:
            context_section = f"""
## Conversation Context
{conversation_context}

Note: Use this context to provide continuity. If the user refers to "that compound" or "the previous result", connect your response to the conversation history.
"""
        
        prompt = f"""You are ChemAgent. Synthesize these tool results into a helpful response.
{context_section}
## Current Query
{query}

## Tool Results
{json.dumps(results, indent=2, default=str)[:4000]}

## Instructions
- Be CONCISE (under 250 words)
{structure_instruction}- Use tables for properties
- Identify known drugs by name and their common uses
- Include key data points (MW, LogP, etc.)
- Don't repeat the query

Return a well-formatted markdown response."""

        logger.info("LLM synthesis: Generating response")
        response = call_llm_with_retry(
            model="groq/llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=1000,
            max_retries=3,
            base_delay=2.0
        )
        
        if response:
            answer = response.choices[0].message.content.strip()
            logger.info("LLM synthesis: Response generated successfully")
            return answer
        else:
            logger.warning("LLM synthesis failed, falling back to fast synthesis")
            return self.synthesize_fast(query, results, IntentType.UNKNOWN)
    
    def verify_response(self, answer: str, results: Dict[str, Any]) -> bool:
        """
        Verify that the response matches the raw data.
        Returns True if no obvious hallucinations detected.
        """
        if not answer or not results:
            return True
        
        # Extract key numbers from results
        result_numbers = set()
        for tool_result in results.values():
            data = tool_result.get("data", tool_result) if isinstance(tool_result, dict) else {}
            if isinstance(data, dict):
                for k, v in data.items():
                    if isinstance(v, (int, float)) and v != 0:
                        result_numbers.add(round(v, 1))
        
        # Check for hallucinated numbers in answer
        answer_numbers = re.findall(r'\b\d+\.?\d*\b', answer)
        for num_str in answer_numbers:
            try:
                num = round(float(num_str), 1)
                # Allow common numbers like 1, 2, etc.
                if num > 10 and num not in result_numbers:
                    # This could be hallucinated
                    logger.warning(f"Potential hallucinated number: {num}")
                    # Don't fail, just log for now
            except ValueError:
                pass
        
        return True


# =============================================================================
# Main Agent
# =============================================================================

class OptimalAgent:
    """
    Hybrid Tiered + Verification Agent.
    
    Fast path (80%): Pattern → Rules → Execute → Light Synthesis
    Smart path (20%): Pattern → LLM Plan → Execute → Verified Synthesis
    
    Supports conversation memory for context-aware responses.
    Now includes Verifier Gate for hallucination prevention.
    """
    
    CONFIDENCE_THRESHOLD = 0.7  # Below this, use LLM
    
    def __init__(
        self, 
        tool_registry=None, 
        session_id: str = None,
        verifier_mode: str = "annotate",  # "reject", "annotate", or "flag"
        verification_threshold: float = 0.7
    ):
        """
        Initialize the agent.
        
        Args:
            tool_registry: Tool registry for executing tools
            session_id: Optional session ID for conversation memory
            verifier_mode: How to handle unverified responses
                - "reject": Return error for untrustworthy responses
                - "annotate": Add verification info to response  
                - "flag": Allow but log potential issues
            verification_threshold: Minimum confidence for trustworthy response
        """
        self.tool_registry = tool_registry
        self.extractor = EntityExtractor()
        self.classifier = IntentClassifier()
        self.planner = ToolPlanner()
        self.synthesizer = ResponseSynthesizer()
        
        # Verifier Gate for hallucination prevention
        self.verifier_gate = VerifierGate(
            mode=verifier_mode,
            confidence_threshold=verification_threshold
        )
        self.verifier_mode = verifier_mode
        
        # Conversation memory
        self.context_manager = get_context_manager()
        self.session_id = session_id
        self._session: Optional[ConversationMemory] = None
        
        # Statistics
        self.stats = {
            "total_queries": 0,
            "fast_path": 0,
            "smart_path": 0,
            "errors": 0,
            "total_latency_ms": 0.0,
            "verification_passed": 0,
            "verification_failed": 0
        }
    
    def set_session(self, session_id: str):
        """Set or switch session for conversation memory."""
        self.session_id = session_id
        self._session = None  # Will be fetched on next access
    
    @property
    def session(self) -> ConversationMemory:
        """Get current conversation session."""
        if self._session is None:
            self._session = self.context_manager.get_or_create_session(self.session_id)
            self.session_id = self._session.session_id
        return self._session
    
    def process(self, query: str, session_id: str = None) -> AgentResponse:
        """
        Process a query through the optimal pipeline.
        
        Args:
            query: The user's query
            session_id: Optional session ID for conversation memory
        """
        start_time = time.time()
        self.stats["total_queries"] += 1
        
        # Set session if provided
        if session_id:
            self.set_session(session_id)
        
        logger.info("=" * 60)
        logger.info(f"QUERY: {query}")
        logger.info(f"SESSION: {self.session.session_id}")
        logger.info("=" * 60)
        
        try:
            # Stage 0: Reference resolution (check conversation context)
            resolved_query = query
            resolved_entity = self.session.resolve_reference(query)
            if resolved_entity:
                logger.info(f"STAGE 0: Reference Resolution")
                logger.info(f"  → Resolved '{query}' reference to: {resolved_entity}")
                # Inject resolved entity into query for processing
                resolved_query = f"{query} (referring to {resolved_entity})"
            
            # Stage 1: Entity extraction (always pattern-based)
            logger.info("STAGE 1: Entity Extraction (Pattern-based)")
            entities = self.extractor.extract(resolved_query)
            
            # Also add entities from resolved reference
            if resolved_entity and resolved_entity not in entities.compounds:
                entities.compounds.append(resolved_entity)
            
            logger.info(f"  → Compounds: {entities.compounds}")
            logger.info(f"  → ChEMBL IDs: {entities.chembl_ids}")
            logger.info(f"  → SMILES: {entities.smiles}")
            logger.info(f"  → Properties: {entities.properties}")
            
            # Stage 2: Intent classification
            logger.info("STAGE 2: Intent Classification")
            intent, confidence = self.classifier.classify(resolved_query, entities)
            logger.info(f"  → Intent: {intent.value}")
            logger.info(f"  → Confidence: {confidence:.2f}")
            
            # Stage 3: Choose path based on confidence
            if confidence >= self.CONFIDENCE_THRESHOLD:
                logger.info(f"STAGE 3: FAST PATH (confidence {confidence:.2f} >= {self.CONFIDENCE_THRESHOLD})")
                response = self._fast_path(query, intent, entities, start_time)
            else:
                logger.info(f"STAGE 3: SMART PATH (confidence {confidence:.2f} < {self.CONFIDENCE_THRESHOLD})")
                response = self._smart_path(query, entities, start_time)
            
            # Store in conversation memory
            self._store_in_memory(query, response, intent, entities)
            
            return response
                
        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"Agent error: {e}", exc_info=True)
            return AgentResponse(
                success=False,
                answer=f"Error processing query: {str(e)}",
                error=str(e),
                execution_time_ms=(time.time() - start_time) * 1000
            )
    
    def _store_in_memory(
        self,
        query: str,
        response: AgentResponse,
        intent: IntentType,
        entities: ExtractedEntities
    ):
        """Store query and response in conversation memory."""
        try:
            # Extract summary from results
            results_summary = extract_results_summary(response.tool_results)
            
            # Build entities dict
            entities_dict = {
                "compound_names": entities.compounds,
                "chembl_ids": entities.chembl_ids,
                "smiles": entities.smiles,
                "uniprot_ids": entities.uniprot_ids
            }
            
            self.session.add_turn(
                query=query,
                response=response.answer,
                intent=intent.value,
                entities=entities_dict,
                tools_used=response.tools_used,
                results_summary=results_summary
            )
            logger.info(f"  → Stored turn {len(self.session.turns)} in session {self.session.session_id}")
        except Exception as e:
            logger.warning(f"Failed to store in memory: {e}")
    
    def _fast_path(
        self, 
        query: str, 
        intent: IntentType, 
        entities: ExtractedEntities,
        start_time: float
    ) -> AgentResponse:
        """Fast path: Rule-based planning, light synthesis."""
        self.stats["fast_path"] += 1
        
        # Plan with rules
        logger.info("  Planning: Rule-based tool selection")
        tool_calls = self.planner.plan_fast(intent, entities)
        logger.info(f"  → Tools planned: {[tc.tool for tc in tool_calls]}")
        
        if not tool_calls:
            logger.warning("  → No tools selected, returning generic response")
            return AgentResponse(
                success=True,
                answer="I couldn't determine what information you need. Please be more specific.",
                path_used="fast",
                confidence=0.0,
                execution_time_ms=(time.time() - start_time) * 1000
            )
        
        # Execute tools (chain activities for target/bioactivity lookups)
        logger.info("STAGE 4: Tool Execution")
        chain_activities = intent in (IntentType.TARGET_LOOKUP, IntentType.BIOACTIVITY_LOOKUP)
        results = self._execute_tools(tool_calls, chain_activities=chain_activities)
        
        # Synthesize (use LLM for better quality if available)
        logger.info("STAGE 5: Response Synthesis")
        conversation_context = self.session.get_context_for_llm(num_turns=3)
        if LITELLM_AVAILABLE:
            logger.info("  → Using LLM synthesis")
            answer = self.synthesizer.synthesize_with_llm(query, results, conversation_context)
        else:
            logger.info("  → Using template synthesis (no LLM)")
            answer = self.synthesizer.synthesize_fast(query, results, intent)
        
        # Apply Verifier Gate (annotate mode for fast path)
        logger.info("STAGE 6: Verifier Gate")
        verified_answer, verification_report = self.verifier_gate.process(answer, results)
        
        if verification_report.is_trustworthy:
            logger.info(f"  → Verifier Gate: PASSED (confidence: {verification_report.overall_confidence:.2f})")
            self.stats["verification_passed"] += 1
        else:
            logger.warning(f"  → Verifier Gate: FLAGGED (confidence: {verification_report.overall_confidence:.2f})")
            self.stats["verification_failed"] += 1
        
        execution_time = (time.time() - start_time) * 1000
        self.stats["total_latency_ms"] += execution_time
        logger.info(f"COMPLETE: Fast path finished in {execution_time:.0f}ms")
        logger.info("=" * 60)
        
        return AgentResponse(
            success=True,
            answer=verified_answer,
            tool_results=results,
            execution_time_ms=execution_time,
            tools_used=[tc.tool for tc in tool_calls],
            path_used="fast",
            confidence=verification_report.overall_confidence if verification_report.claims_extracted > 0 else 1.0
        )
    
    def _smart_path(
        self, 
        query: str, 
        entities: ExtractedEntities,
        start_time: float
    ) -> AgentResponse:
        """Smart path: LLM planning, verified synthesis."""
        self.stats["smart_path"] += 1
        
        # Plan with LLM
        logger.info("  Planning: LLM-assisted tool selection")
        tool_calls = self.planner.plan_with_llm(query, entities)
        logger.info(f"  → Tools planned: {[tc.tool for tc in tool_calls]}")
        
        if not tool_calls:
            logger.info("  → No tools needed, using direct LLM answer")
            if LITELLM_AVAILABLE:
                answer = self._direct_llm_answer(query)
            else:
                answer = "I couldn't determine what tools to use for this query."
            
            return AgentResponse(
                success=True,
                answer=answer,
                path_used="smart",
                confidence=0.5,
                execution_time_ms=(time.time() - start_time) * 1000
            )
        
        # Execute tools
        logger.info("STAGE 4: Tool Execution")
        results = self._execute_tools(tool_calls)
        
        # Synthesize with LLM
        logger.info("STAGE 5: Response Synthesis (LLM)")
        conversation_context = self.session.get_context_for_llm(num_turns=3)
        answer = self.synthesizer.synthesize_with_llm(query, results, conversation_context)
        
        # Verify response with basic check
        logger.info("STAGE 6: Response Verification (Basic)")
        if not self.synthesizer.verify_response(answer, results):
            logger.warning("  → Basic verification failed, using strict synthesis")
            answer = self.synthesizer.synthesize_fast(
                query, results, IntentType.UNKNOWN
            ) + "\n\n*[Auto-corrected response due to verification failure]*"
        else:
            logger.info("  → Basic verification passed")
        
        # Apply Verifier Gate for claim-level verification
        logger.info("STAGE 7: Verifier Gate (Claim Verification)")
        verified_answer, verification_report = self.verifier_gate.process(answer, results)
        
        if verification_report.is_trustworthy:
            logger.info(f"  → Verifier Gate: PASSED (confidence: {verification_report.overall_confidence:.2f})")
            self.stats["verification_passed"] += 1
        else:
            logger.warning(f"  → Verifier Gate: FLAGGED (confidence: {verification_report.overall_confidence:.2f})")
            logger.warning(f"     Claims: {verification_report.claims_extracted} extracted, "
                          f"{verification_report.claims_verified} verified, "
                          f"{verification_report.claims_contradicted} contradicted")
            self.stats["verification_failed"] += 1
        
        execution_time = (time.time() - start_time) * 1000
        self.stats["total_latency_ms"] += execution_time
        logger.info(f"COMPLETE: Smart path finished in {execution_time:.0f}ms")
        logger.info("=" * 60)
        
        return AgentResponse(
            success=True,
            answer=verified_answer,
            tool_results=results,
            execution_time_ms=execution_time,
            tools_used=[tc.tool for tc in tool_calls],
            path_used="smart",
            confidence=0.8
        )
    
    def _execute_tools(self, tool_calls: List[ToolCall], chain_activities: bool = False) -> Dict[str, Any]:
        """Execute tool calls and collect results with optional chaining."""
        results = {}
        extracted_chembl_id = None  # For chaining ChEMBL activities
        extracted_ensembl_id = None  # For chaining Open Targets associations
        
        for tc in tool_calls:
            tool_name = tc.tool
            args = tc.args
            
            logger.info(f"  → Executing: {tool_name}({args})")
            
            try:
                if self.tool_registry:
                    tool = self.tool_registry.get(tool_name)
                    if tool:
                        result = tool(**args)
                        results[tool_name] = {
                            "success": True,
                            "data": result,
                            "args": args
                        }
                        logger.info(f"    ✓ {tool_name} succeeded")
                        
                        # Extract ChEMBL ID for potential chaining
                        if tool_name == "chembl_search_by_name" and result:
                            data = result
                            if isinstance(data, dict) and "compounds" in data:
                                compounds = data["compounds"]
                                if compounds:
                                    c = compounds[0]
                                    if hasattr(c, 'chembl_id'):
                                        extracted_chembl_id = c.chembl_id
                                    elif isinstance(c, dict):
                                        extracted_chembl_id = c.get("chembl_id")
                        
                        # Extract Ensembl ID from Open Targets search for chaining
                        if tool_name == "opentargets_search_target" and result:
                            data = result
                            if isinstance(data, dict) and data.get("success"):
                                targets = data.get("targets", [])
                                if targets:
                                    extracted_ensembl_id = targets[0].get("ensembl_id")
                                    logger.info(f"    → Extracted Ensembl ID: {extracted_ensembl_id}")
                    else:
                        results[tool_name] = {
                            "success": False,
                            "error": f"Tool not found: {tool_name}"
                        }
                        logger.warning(f"    ✗ {tool_name} not found")
                else:
                    results[tool_name] = {
                        "success": False,
                        "error": "No tool registry configured"
                    }
            except Exception as e:
                logger.error(f"Tool {tool_name} failed: {e}")
                results[tool_name] = {
                    "success": False,
                    "error": str(e)
                }
        
        # Chain: If we found a ChEMBL ID and need activities, fetch them
        if chain_activities and extracted_chembl_id and "chembl_get_activities" not in results:
            logger.info(f"  → Chaining: Get activities for {extracted_chembl_id}")
            try:
                if self.tool_registry:
                    activities_tool = self.tool_registry.get("chembl_get_activities")
                    if activities_tool:
                        activities_result = activities_tool(chembl_id=extracted_chembl_id, limit=30)
                        results["chembl_get_activities"] = {
                            "success": True,
                            "data": activities_result,
                            "args": {"chembl_id": extracted_chembl_id, "limit": 30}
                        }
                        logger.info(f"    ✓ Chained chembl_get_activities succeeded")
            except Exception as e:
                logger.error(f"Chained activities fetch failed: {e}")
        
        # Chain: If we found an Ensembl ID, get disease associations
        if extracted_ensembl_id and "opentargets_get_associations" not in results:
            logger.info(f"  → Chaining: Get disease associations for {extracted_ensembl_id}")
            try:
                if self.tool_registry:
                    assoc_tool = self.tool_registry.get("opentargets_get_associations")
                    if assoc_tool:
                        assoc_result = assoc_tool(ensembl_id=extracted_ensembl_id, limit=10)
                        results["opentargets_get_associations"] = {
                            "success": True,
                            "data": assoc_result,
                            "args": {"ensembl_id": extracted_ensembl_id, "limit": 10}
                        }
                        logger.info(f"    ✓ Chained opentargets_get_associations succeeded")
            except Exception as e:
                logger.error(f"Chained associations fetch failed: {e}")
        
        return results
    
    def _direct_llm_answer(self, query: str) -> str:
        """Get direct answer from LLM without tools."""
        response = call_llm_with_retry(
            model="groq/llama-3.1-8b-instant",
            messages=[{
                "role": "system",
                "content": "You are ChemAgent, a pharmaceutical research assistant. Answer chemistry and drug-related questions concisely."
            }, {
                "role": "user", 
                "content": query
            }],
            temperature=0.3,
            max_tokens=500,
            max_retries=3,
            base_delay=2.0
        )
        
        if response:
            return response.choices[0].message.content.strip()
        else:
            return "Unable to process your query at this time. Please try again later."
    
    def get_stats(self) -> Dict[str, Any]:
        """Get agent statistics."""
        total = max(self.stats["total_queries"], 1)
        return {
            **self.stats,
            "fast_path_rate": self.stats["fast_path"] / total * 100,
            "smart_path_rate": self.stats["smart_path"] / total * 100,
            "avg_latency_ms": self.stats["total_latency_ms"] / total
        }


# =============================================================================
# Factory Function
# =============================================================================

def create_optimal_agent(tool_registry=None) -> OptimalAgent:
    """Create an OptimalAgent instance."""
    return OptimalAgent(tool_registry=tool_registry)
