"""
Intent parser for natural language chemistry queries.

Converts user queries into structured intents with extracted entities.
Supports 50+ chemistry-specific query patterns.
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class IntentType(Enum):
    """Types of chemistry queries."""
    
    # Search intents
    SIMILARITY_SEARCH = "similarity_search"
    SUBSTRUCTURE_SEARCH = "substructure_search"
    COMPOUND_LOOKUP = "compound_lookup"
    TARGET_LOOKUP = "target_lookup"
    
    # Property intents
    PROPERTY_CALCULATION = "property_calculation"
    PROPERTY_FILTER = "property_filter"
    LIPINSKI_CHECK = "lipinski_check"
    
    # Activity intents
    ACTIVITY_LOOKUP = "activity_lookup"
    TARGET_PREDICTION = "target_prediction"
    
    # Conversion intents
    STRUCTURE_CONVERSION = "structure_conversion"
    STANDARDIZATION = "standardization"
    
    # Analysis intents
    SCAFFOLD_ANALYSIS = "scaffold_analysis"
    BATCH_ANALYSIS = "batch_analysis"
    
    # Unknown/fallback
    UNKNOWN = "unknown"


@dataclass
class ParsedIntent:
    """Parsed query with intent and extracted entities."""
    
    intent_type: IntentType
    entities: Dict[str, Any] = field(default_factory=dict)
    constraints: Dict[str, Any] = field(default_factory=dict)
    original_query: str = ""
    confidence: float = 1.0
    
    def __repr__(self) -> str:
        """String representation."""
        ent_str = ", ".join(f"{k}={v}" for k, v in self.entities.items())
        return f"ParsedIntent({self.intent_type.value}, {ent_str})"


class IntentParser:
    """
    Natural language intent parser for chemistry queries.
    
    Recognizes 50+ query patterns and extracts relevant entities like
    SMILES, compound names, targets, ChEMBL IDs, and constraints.
    
    Example:
        >>> parser = IntentParser()
        >>> intent = parser.parse("Find compounds similar to aspirin")
        >>> intent.intent_type
        <IntentType.SIMILARITY_SEARCH: 'similarity_search'>
        >>> intent.entities["compound"]
        'aspirin'
    """
    
    def __init__(self):
        """Initialize parser with pattern matchers."""
        self.patterns = self._build_patterns()
    
    def parse(self, query: str) -> ParsedIntent:
        """
        Parse query into structured intent.
        
        Args:
            query: Natural language query
            
        Returns:
            ParsedIntent with type and extracted entities
            
        Example:
            >>> parser = IntentParser()
            >>> intent = parser.parse("What's the LogP of CC(=O)O")
            >>> intent.intent_type
            <IntentType.PROPERTY_CALCULATION: 'property_calculation'>
        """
        query_lower = query.lower().strip()
        
        # Try each pattern
        for pattern, config in self.patterns:
            if match := re.search(pattern, query_lower, re.IGNORECASE):
                intent_type = config["intent"]
                entities = self._extract_entities(
                    query, query_lower, match, config.get("entity_extractors", [])
                )
                constraints = self._extract_constraints(query_lower)
                
                return ParsedIntent(
                    intent_type=intent_type,
                    entities=entities,
                    constraints=constraints,
                    original_query=query,
                    confidence=1.0
                )
        
        # No pattern matched - try fallback classification
        return self._fallback_parse(query)
    
    def _build_patterns(self) -> List[Tuple[str, Dict[str, Any]]]:
        """
        Build list of (pattern, config) tuples.
        
        Each config has:
        - intent: IntentType
        - entity_extractors: List of extractor names
        
        Returns 50+ patterns covering common chemistry queries.
        """
        return [
            # ============================================================
            # SIMILARITY SEARCH (10 patterns)
            # ============================================================
            (
                r"find.*(similar|analogs?|related).*(compounds?|molecules?|structures?).*(to|of|like)\s+(?P<compound>\w+)",
                {"intent": IntentType.SIMILARITY_SEARCH, "entity_extractors": ["compound", "threshold", "limit"]}
            ),
            (
                r"(similar|analogs?).*(to|of)\s+(?P<smiles>[A-Z][A-Za-z0-9@+\-\[\]()=#]+)",
                {"intent": IntentType.SIMILARITY_SEARCH, "entity_extractors": ["smiles", "threshold"]}
            ),
            (
                r"similar.*(to|of).*(CHEMBL\d+)",
                {"intent": IntentType.SIMILARITY_SEARCH, "entity_extractors": ["chembl_id", "threshold"]}
            ),
            (
                r"compounds?.*(similar|like).*(aspirin|ibuprofen|acetaminophen|caffeine|morphine|cocaine)",
                {"intent": IntentType.SIMILARITY_SEARCH, "entity_extractors": ["compound", "threshold"]}
            ),
            (
                r"(search|find|get|show).*(tanimoto|similarity).*(>|above|greater).*(?P<threshold>0?\.\d+|\d+)",
                {"intent": IntentType.SIMILARITY_SEARCH, "entity_extractors": ["threshold", "smiles", "compound"]}
            ),
            (
                r"structural?.*(similar|analog)",
                {"intent": IntentType.SIMILARITY_SEARCH, "entity_extractors": ["smiles", "compound", "threshold"]}
            ),
            (
                r"molecules?.*(resemble|resembling)",
                {"intent": IntentType.SIMILARITY_SEARCH, "entity_extractors": ["smiles", "compound"]}
            ),
            (
                r"chemically.*(close|near|related)",
                {"intent": IntentType.SIMILARITY_SEARCH, "entity_extractors": ["smiles", "compound", "threshold"]}
            ),
            (
                r"fingerprint.*(match|search)",
                {"intent": IntentType.SIMILARITY_SEARCH, "entity_extractors": ["smiles", "threshold"]}
            ),
            (
                r"(find|search).*(neighbors?|nearest)",
                {"intent": IntentType.SIMILARITY_SEARCH, "entity_extractors": ["smiles", "compound", "limit"]}
            ),
            
            # ============================================================
            # SUBSTRUCTURE SEARCH (8 patterns)
            # ============================================================
            (
                r"(find|search|contains?).*(substructure|fragment|motif)",
                {"intent": IntentType.SUBSTRUCTURE_SEARCH, "entity_extractors": ["smarts", "smiles"]}
            ),
            (
                r"compounds?.*(contain|containing|with).*(benzene|carbonyl|hydroxyl|amine|amide|ester)",
                {"intent": IntentType.SUBSTRUCTURE_SEARCH, "entity_extractors": ["functional_group"]}
            ),
            (
                r"match.*(smarts|pattern)",
                {"intent": IntentType.SUBSTRUCTURE_SEARCH, "entity_extractors": ["smarts"]}
            ),
            (
                r"molecules?.*(having|with).*(ring|phenyl|aromatic)",
                {"intent": IntentType.SUBSTRUCTURE_SEARCH, "entity_extractors": ["functional_group"]}
            ),
            (
                r"structures?.*(having|containing).*(scaffold|core)",
                {"intent": IntentType.SUBSTRUCTURE_SEARCH, "entity_extractors": ["smiles", "smarts"]}
            ),
            (
                r"(find|search).*(fragment|piece)",
                {"intent": IntentType.SUBSTRUCTURE_SEARCH, "entity_extractors": ["smarts", "smiles"]}
            ),
            (
                r"has.*(moiety|group|unit)",
                {"intent": IntentType.SUBSTRUCTURE_SEARCH, "entity_extractors": ["smarts", "functional_group"]}
            ),
            (
                r"murcko.*(scaffold|core)",
                {"intent": IntentType.SCAFFOLD_ANALYSIS, "entity_extractors": ["smiles", "compound"]}
            ),
            
            # ============================================================
            # COMPOUND LOOKUP (8 patterns)
            # ============================================================
            (
                r"(what is|what's|tell me about|info on|information about|show me|get|find)\s+(compound\s+)?(CHEMBL\d+)",
                {"intent": IntentType.COMPOUND_LOOKUP, "entity_extractors": ["chembl_id"]}
            ),
            (
                r"(structure|smiles|formula).*(of|for)\s+(?P<compound>\w+)",
                {"intent": IntentType.COMPOUND_LOOKUP, "entity_extractors": ["compound"]}
            ),
            (
                r"(lookup|search|find).*(compound|molecule|drug).*(name[d]?|called)\s+(?P<compound>\w+)",
                {"intent": IntentType.COMPOUND_LOOKUP, "entity_extractors": ["compound"]}
            ),
            (
                r"(aspirin|ibuprofen|acetaminophen|caffeine|morphine|paracetamol|warfarin).*(structure|formula|smiles)",
                {"intent": IntentType.COMPOUND_LOOKUP, "entity_extractors": ["compound"]}
            ),
            (
                r"compound.*(CHEMBL\d+)",
                {"intent": IntentType.COMPOUND_LOOKUP, "entity_extractors": ["chembl_id"]}
            ),
            (
                r"(get|retrieve|fetch).*(data|info).*(for|on|about)\s+(?P<compound>\w+)",
                {"intent": IntentType.COMPOUND_LOOKUP, "entity_extractors": ["compound", "chembl_id"]}
            ),
            (
                r"details.*(of|for|on|about)\s+(CHEMBL\d+|\w+)",
                {"intent": IntentType.COMPOUND_LOOKUP, "entity_extractors": ["compound", "chembl_id"]}
            ),
            (
                r"(molecule|drug).*(name[d]?|called)\s+(?P<compound>\w+)",
                {"intent": IntentType.COMPOUND_LOOKUP, "entity_extractors": ["compound"]}
            ),
            
            # ============================================================
            # TARGET LOOKUP (5 patterns)
            # ============================================================
            (
                r"(target|protein|enzyme|receptor).*(info|information|details).*(for|on|about)\s+(?P<target>\w+)",
                {"intent": IntentType.TARGET_LOOKUP, "entity_extractors": ["target", "uniprot_id"]}
            ),
            (
                r"(what is|what's|tell me about)\s+(?P<target>COX-?\d+|EGFR|VEGFR|BRAF|P53|BCL2)",
                {"intent": IntentType.TARGET_LOOKUP, "entity_extractors": ["target"]}
            ),
            (
                r"(protein|target).*(P\d{5}|[A-Z]\d[A-Z0-9]{3}\d)",
                {"intent": IntentType.TARGET_LOOKUP, "entity_extractors": ["uniprot_id"]}
            ),
            (
                r"uniprot.*(P\d{5})",
                {"intent": IntentType.TARGET_LOOKUP, "entity_extractors": ["uniprot_id"]}
            ),
            (
                r"(enzyme|receptor|kinase).*(named?|called)",
                {"intent": IntentType.TARGET_LOOKUP, "entity_extractors": ["target"]}
            ),
            
            # ============================================================
            # PROPERTY CALCULATION (9 patterns)
            # ============================================================
            (
                r"(calc|calculate|compute|get|what.?s|what is).*(property|properties|descriptor)",
                {"intent": IntentType.PROPERTY_CALCULATION, "entity_extractors": ["smiles", "compound"]}
            ),
            (
                r"(logp|clogp|partition coefficient)",
                {"intent": IntentType.PROPERTY_CALCULATION, "entity_extractors": ["smiles", "compound", "property_name"]}
            ),
            (
                r"molecular.*(weight|mass|formula)",
                {"intent": IntentType.PROPERTY_CALCULATION, "entity_extractors": ["smiles", "compound", "property_name"]}
            ),
            (
                r"(tpsa|polar surface area)",
                {"intent": IntentType.PROPERTY_CALCULATION, "entity_extractors": ["smiles", "compound", "property_name"]}
            ),
            (
                r"(hb?[ad]|hydrogen bond|h-bond).*(donor|acceptor)",
                {"intent": IntentType.PROPERTY_CALCULATION, "entity_extractors": ["smiles", "compound", "property_name"]}
            ),
            (
                r"rotatable.*(bond)",
                {"intent": IntentType.PROPERTY_CALCULATION, "entity_extractors": ["smiles", "compound", "property_name"]}
            ),
            (
                r"(ring|aromatic)",
                {"intent": IntentType.PROPERTY_CALCULATION, "entity_extractors": ["smiles", "compound", "property_name"]}
            ),
            (
                r"(descriptor|features?|characteristics)",
                {"intent": IntentType.PROPERTY_CALCULATION, "entity_extractors": ["smiles", "compound"]}
            ),
            (
                r"(properties|props).*(of|for)\s+([A-Z][A-Za-z0-9@+\-\[\]()=#]+|\w+)",
                {"intent": IntentType.PROPERTY_CALCULATION, "entity_extractors": ["smiles", "compound"]}
            ),
            
            # ============================================================
            # PROPERTY FILTER (7 patterns)
            # ============================================================
            (
                r"filter.*(mw|molecular weight|mass).*(<|>|less|greater|below|above)\s*(?P<mw_value>\d+)",
                {"intent": IntentType.PROPERTY_FILTER, "entity_extractors": ["mw_constraint"]}
            ),
            (
                r"compounds?.*(mw|molecular weight).*(<|>|less|greater|below|above)\s*(?P<mw_value>\d+)",
                {"intent": IntentType.PROPERTY_FILTER, "entity_extractors": ["mw_constraint"]}
            ),
            (
                r"(logp|clogp).*(<|>|less|greater|below|above)\s*(?P<logp_value>-?\d+\.?\d*)",
                {"intent": IntentType.PROPERTY_FILTER, "entity_extractors": ["logp_constraint"]}
            ),
            (
                r"filter.*(property|properties|descriptor)",
                {"intent": IntentType.PROPERTY_FILTER, "entity_extractors": ["constraints"]}
            ),
            (
                r"molecules?.*(with|having).*(mw|weight|logp|tpsa)",
                {"intent": IntentType.PROPERTY_FILTER, "entity_extractors": ["constraints"]}
            ),
            (
                r"(select|keep|retain).*(where|with)",
                {"intent": IntentType.PROPERTY_FILTER, "entity_extractors": ["constraints"]}
            ),
            (
                r"satisf(y|ies|ying).*(constraint|criteria|rule)",
                {"intent": IntentType.PROPERTY_FILTER, "entity_extractors": ["constraints"]}
            ),
            
            # ============================================================
            # LIPINSKI CHECK (4 patterns)
            # ============================================================
            (
                r"(lipinski|rule.?of.?five|ro5)",
                {"intent": IntentType.LIPINSKI_CHECK, "entity_extractors": ["smiles", "compound"]}
            ),
            (
                r"(drug.?like|druglike|druggable)",
                {"intent": IntentType.LIPINSKI_CHECK, "entity_extractors": ["smiles", "compound"]}
            ),
            (
                r"(pass|passes|violate).*(lipinski|ro5|rule)",
                {"intent": IntentType.LIPINSKI_CHECK, "entity_extractors": ["smiles", "compound"]}
            ),
            (
                r"(adme|absorption|oral|bioavail)",
                {"intent": IntentType.LIPINSKI_CHECK, "entity_extractors": ["smiles", "compound"]}
            ),
            
            # ============================================================
            # ACTIVITY LOOKUP (6 patterns)
            # ============================================================
            (
                r"(ic50|ki|ec50|kd).*(for|of|on|against)\s+(?P<target>\w+)",
                {"intent": IntentType.ACTIVITY_LOOKUP, "entity_extractors": ["compound", "target", "activity_type"]}
            ),
            (
                r"(bioactivity|activity|potency).*(data|value|measurement)",
                {"intent": IntentType.ACTIVITY_LOOKUP, "entity_extractors": ["compound", "target", "chembl_id"]}
            ),
            (
                r"(inhibit|inhibition|bind|binding).*(to|of|on|against)\s+(?P<target>\w+)",
                {"intent": IntentType.ACTIVITY_LOOKUP, "entity_extractors": ["compound", "target"]}
            ),
            (
                r"activity.*(against|on|for)\s+(?P<target>\w+)",
                {"intent": IntentType.ACTIVITY_LOOKUP, "entity_extractors": ["compound", "target"]}
            ),
            (
                r"(assay|screening).*(data|result)",
                {"intent": IntentType.ACTIVITY_LOOKUP, "entity_extractors": ["compound", "target", "chembl_id"]}
            ),
            (
                r"(target|protein).*(binding|affinity)",
                {"intent": IntentType.ACTIVITY_LOOKUP, "entity_extractors": ["compound", "target"]}
            ),
            
            # ============================================================
            # STRUCTURE CONVERSION (5 patterns)
            # ============================================================
            (
                r"convert.*(smiles|inchi|inchikey|mol|sdf)",
                {"intent": IntentType.STRUCTURE_CONVERSION, "entity_extractors": ["smiles", "format"]}
            ),
            (
                r"(smiles|inchi).*(to|into|as).*(inchi|smiles|inchikey)",
                {"intent": IntentType.STRUCTURE_CONVERSION, "entity_extractors": ["smiles", "format"]}
            ),
            (
                r"(canonical|canonicalize|normalize)",
                {"intent": IntentType.STANDARDIZATION, "entity_extractors": ["smiles"]}
            ),
            (
                r"(standardize|standard form)",
                {"intent": IntentType.STANDARDIZATION, "entity_extractors": ["smiles", "compound"]}
            ),
            (
                r"(format|represent).*(as|to|in).*(smiles|inchi)",
                {"intent": IntentType.STRUCTURE_CONVERSION, "entity_extractors": ["smiles", "format"]}
            ),
        ]
    
    def _extract_entities(
        self,
        query: str,
        query_lower: str,
        match: re.Match,
        extractors: List[str]
    ) -> Dict[str, Any]:
        """
        Extract entities from query based on extractor list.
        
        Args:
            query: Original query (case-preserved)
            query_lower: Lowercase query
            match: Regex match object
            extractors: List of entity extractors to apply
            
        Returns:
            Dictionary of extracted entities
        """
        entities = {}
        
        # Add named groups from match
        entities.update(match.groupdict())
        
        # Apply entity extractors
        for extractor in extractors:
            if extractor == "smiles":
                if smiles := self._extract_smiles(query):
                    entities["smiles"] = smiles
            
            elif extractor == "compound":
                if compound := self._extract_compound(query, query_lower):
                    entities["compound"] = compound
            
            elif extractor == "chembl_id":
                if chembl_id := self._extract_chembl_id(query):
                    entities["chembl_id"] = chembl_id
            
            elif extractor == "target":
                if target := self._extract_target(query):
                    entities["target"] = target
            
            elif extractor == "uniprot_id":
                if uniprot_id := self._extract_uniprot_id(query):
                    entities["uniprot_id"] = uniprot_id
            
            elif extractor == "threshold":
                if threshold := self._extract_threshold(query_lower):
                    entities["threshold"] = threshold
            
            elif extractor == "limit":
                if limit := self._extract_limit(query_lower):
                    entities["limit"] = limit
            
            elif extractor == "smarts":
                if smarts := self._extract_smarts(query):
                    entities["smarts"] = smarts
            
            elif extractor == "functional_group":
                if group := self._extract_functional_group(query_lower):
                    entities["functional_group"] = group
            
            elif extractor == "property_name":
                if prop := self._extract_property_name(query_lower):
                    entities["property_name"] = prop
            
            elif extractor == "activity_type":
                if activity_type := self._extract_activity_type(query_lower):
                    entities["activity_type"] = activity_type
            
            elif extractor == "format":
                if fmt := self._extract_format(query_lower):
                    entities["format"] = fmt
        
        return entities
    
    def _extract_smiles(self, query: str) -> Optional[str]:
        """Extract SMILES from query."""
        # Match SMILES-like strings - must have lowercase AND special SMILES chars
        # Improved pattern: require at least 4 chars with mix of case and SMILES symbols
        pattern = r"\b([A-Z][A-Za-z0-9@+\-\[\]()=#]{4,})\b"
        candidates = re.findall(pattern, query)
        
        for candidate in candidates:
            # Must have at least one lowercase letter AND one SMILES special char
            has_lowercase = any(c.islower() for c in candidate)
            has_special = any(c in "[]()=#@+" for c in candidate)
            has_numbers = any(c.isdigit() for c in candidate)
            
            # Valid SMILES typically has lowercase (aromatic) or special chars
            # Also check it's not a common word
            common_words = ["Find", "Show", "Get", "Tell", "What", "Similarity", "Filter", "Search"]
            if candidate in common_words:
                continue
            
            if (has_lowercase or has_special) and has_numbers:
                return candidate
        
        return None
    
    def _extract_compound(self, query: str, query_lower: str) -> Optional[str]:
        """Extract compound name from query."""
        # Common drug names
        common_drugs = [
            "aspirin", "ibuprofen", "acetaminophen", "paracetamol",
            "caffeine", "morphine", "cocaine", "warfarin", "insulin",
            "penicillin", "metformin", "lipitor", "viagra", "prozac"
        ]
        
        for drug in common_drugs:
            if drug in query_lower:
                return drug
        
        # Extract from patterns like "compound X" or "drug X"
        pattern = r"(?:compound|drug|molecule)\s+([A-Z][a-z]+)"
        if match := re.search(pattern, query):
            return match.group(1)
        
        return None
    
    def _extract_chembl_id(self, query: str) -> Optional[str]:
        """Extract ChEMBL ID from query."""
        pattern = r"(CHEMBL\d+)"
        if match := re.search(pattern, query, re.IGNORECASE):
            return match.group(1).upper()
        return None
    
    def _extract_target(self, query: str) -> Optional[str]:
        """Extract target name from query."""
        # Common targets
        common_targets = [
            "COX-1", "COX-2", "COX1", "COX2",
            "EGFR", "VEGFR", "BRAF", "P53", "BCL2",
            "kinase", "protease", "phosphatase"
        ]
        
        for target in common_targets:
            if re.search(rf"\b{re.escape(target)}\b", query, re.IGNORECASE):
                return target
        
        # Extract from patterns
        pattern = r"(?:target|protein|enzyme|receptor)\s+([A-Z][A-Z0-9-]+)"
        if match := re.search(pattern, query, re.IGNORECASE):
            return match.group(1)
        
        return None
    
    def _extract_uniprot_id(self, query: str) -> Optional[str]:
        """Extract UniProt ID from query."""
        # UniProt ID format: [A-Z][0-9][A-Z0-9]{3}[0-9] or P\d{5}
        pattern = r"\b([A-Z]\d[A-Z0-9]{3}\d|P\d{5})\b"
        if match := re.search(pattern, query):
            return match.group(1)
        return None
    
    def _extract_threshold(self, query_lower: str) -> Optional[float]:
        """Extract similarity threshold from query."""
        # Pattern: "similarity 0.7" or "threshold > 0.8" or "70%"
        patterns = [
            r"(?:similarity|threshold).*?(0?\.\d+|\d+%)",
            r"(?:>|above|greater).*?(0?\.\d+)",
            r"(?:<|below|less).*?(0?\.\d+)",
        ]
        
        for pattern in patterns:
            if match := re.search(pattern, query_lower):
                value = match.group(1).rstrip('%')
                threshold = float(value)
                # Convert percentage to decimal
                if '%' in match.group(1):
                    threshold /= 100.0
                # Ensure 0-1 range
                if 0 <= threshold <= 1:
                    return threshold
        
        return None
    
    def _extract_limit(self, query_lower: str) -> Optional[int]:
        """Extract result limit from query."""
        patterns = [
            r"(?:top|first)\s+(\d+)",
            r"limit\s+(\d+)",
            r"(\d+)\s+(?:results?|compounds?|molecules?)",
        ]
        
        for pattern in patterns:
            if match := re.search(pattern, query_lower):
                return int(match.group(1))
        
        return None
    
    def _extract_smarts(self, query: str) -> Optional[str]:
        """Extract SMARTS pattern from query."""
        # SMARTS patterns typically have brackets and special chars
        pattern = r"\[([^\]]+)\]"
        if match := re.search(pattern, query):
            return f"[{match.group(1)}]"
        return None
    
    def _extract_functional_group(self, query_lower: str) -> Optional[str]:
        """Extract functional group name from query."""
        groups = {
            "benzene": "c1ccccc1",
            "phenyl": "c1ccccc1",
            "carbonyl": "C=O",
            "hydroxyl": "O",
            "amine": "N",
            "amide": "C(=O)N",
            "ester": "C(=O)O",
            "carboxylic acid": "C(=O)O",
            "ketone": "C(=O)C",
            "aldehyde": "C=O",
            "aromatic": "a",
        }
        
        for name, smarts in groups.items():
            if name in query_lower:
                return smarts
        
        return None
    
    def _extract_property_name(self, query_lower: str) -> Optional[str]:
        """Extract property name from query."""
        properties = {
            "logp": ["logp", "clogp", "partition coefficient"],
            "mw": ["molecular weight", "mw", "mass"],
            "tpsa": ["tpsa", "polar surface area"],
            "hbd": ["hbd", "h-bond donor", "hydrogen bond donor"],
            "hba": ["hba", "h-bond acceptor", "hydrogen bond acceptor"],
            "rotatable_bonds": ["rotatable bond"],
            "aromatic_rings": ["aromatic ring"],
        }
        
        for prop_name, keywords in properties.items():
            if any(kw in query_lower for kw in keywords):
                return prop_name
        
        return None
    
    def _extract_activity_type(self, query_lower: str) -> Optional[str]:
        """Extract activity type from query."""
        types = ["ic50", "ki", "ec50", "kd", "ki"]
        
        for activity_type in types:
            if activity_type in query_lower:
                return activity_type.upper()
        
        return None
    
    def _extract_format(self, query_lower: str) -> Optional[str]:
        """Extract target format from query."""
        formats = ["smiles", "inchi", "inchikey", "mol", "sdf"]
        
        # For conversions like "smiles to inchi", prefer the target (after "to")
        if " to " in query_lower or " into " in query_lower:
            parts = re.split(r"\s+(?:to|into)\s+", query_lower)
            if len(parts) == 2:
                # Check second part for format
                for fmt in formats:
                    if fmt in parts[1]:
                        return fmt
        
        # Otherwise, find any format mentioned
        for fmt in formats:
            if fmt in query_lower:
                return fmt
        
        return None
    
    def _extract_constraints(self, query_lower: str) -> Dict[str, Any]:
        """
        Extract property constraints from query.
        
        Examples:
        - "MW < 500" → {"mw_max": 500}
        - "LogP > 3" → {"logp_min": 3}
        - "TPSA < 140" → {"tpsa_max": 140}
        """
        constraints = {}
        
        # MW constraints
        if match := re.search(r"(?:mw|molecular weight|mass)\s*([<>]|less|greater|below|above)\s*(\d+)", query_lower):
            operator, value = match.group(1), int(match.group(2))
            if operator in ['<', 'less', 'below']:
                constraints["mw_max"] = value
            else:
                constraints["mw_min"] = value
        
        # LogP constraints
        if match := re.search(r"(?:logp|clogp)\s*([<>]|less|greater|below|above)\s*(-?\d+\.?\d*)", query_lower):
            operator, value = match.group(1), float(match.group(2))
            if operator in ['<', 'less', 'below']:
                constraints["logp_max"] = value
            else:
                constraints["logp_min"] = value
        
        # TPSA constraints
        if match := re.search(r"tpsa\s*([<>]|less|greater|below|above)\s*(\d+)", query_lower):
            operator, value = match.group(1), int(match.group(2))
            if operator in ['<', 'less', 'below']:
                constraints["tpsa_max"] = value
            else:
                constraints["tpsa_min"] = value
        
        # HBD/HBA constraints
        if match := re.search(r"(?:hbd|h-bond donor)\s*([<>]|less|greater)\s*(\d+)", query_lower):
            operator, value = match.group(1), int(match.group(2))
            constraints["hbd_max" if operator == '<' else "hbd_min"] = value
        
        if match := re.search(r"(?:hba|h-bond acceptor)\s*([<>]|less|greater)\s*(\d+)", query_lower):
            operator, value = match.group(1), int(match.group(2))
            constraints["hba_max" if operator == '<' else "hba_min"] = value
        
        return constraints
    
    def _fallback_parse(self, query: str) -> ParsedIntent:
        """
        Fallback parsing when no pattern matches.
        
        Try to classify based on keywords and extracted entities.
        """
        query_lower = query.lower()
        
        # Extract any available entities
        entities = {}
        if smiles := self._extract_smiles(query):
            entities["smiles"] = smiles
        if compound := self._extract_compound(query, query_lower):
            entities["compound"] = compound
        if chembl_id := self._extract_chembl_id(query):
            entities["chembl_id"] = chembl_id
        
        # Simple keyword classification
        if any(kw in query_lower for kw in ["similar", "analog", "like"]):
            intent = IntentType.SIMILARITY_SEARCH
        elif any(kw in query_lower for kw in ["property", "logp", "weight", "tpsa"]):
            intent = IntentType.PROPERTY_CALCULATION
        elif any(kw in query_lower for kw in ["lipinski", "drug-like", "ro5"]):
            intent = IntentType.LIPINSKI_CHECK
        elif any(kw in query_lower for kw in ["activity", "ic50", "binding"]):
            intent = IntentType.ACTIVITY_LOOKUP
        elif any(kw in query_lower for kw in ["target", "protein", "enzyme"]):
            intent = IntentType.TARGET_LOOKUP
        elif entities.get("compound") or entities.get("chembl_id"):
            intent = IntentType.COMPOUND_LOOKUP
        else:
            intent = IntentType.UNKNOWN
        
        return ParsedIntent(
            intent_type=intent,
            entities=entities,
            original_query=query,
            confidence=0.5  # Lower confidence for fallback
        )
