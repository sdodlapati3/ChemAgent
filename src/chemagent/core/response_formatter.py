"""
Response formatting for ChemAgent query results.

Converts raw execution results into human-readable answers
tailored to different intent types.
"""

from typing import Any, Dict, List, Optional

from chemagent.core.executor import ExecutionResult, ExecutionStatus
from chemagent.core.intent_parser import IntentType, ParsedIntent


class ResponseFormatter:
    """
    Formats execution results into human-readable answers.
    
    Provides intent-specific formatting for different types of chemistry queries.
    """
    
    def _safe_float(self, value: Any, default: str = "N/A", decimals: int = 2) -> str:
        """Safely convert value to formatted float string."""
        try:
            if value is None:
                return default
            float_val = float(value)
            return f"{float_val:.{decimals}f}"
        except (ValueError, TypeError):
            return str(value) if value is not None else default
    
    def format(self, intent: ParsedIntent, result: ExecutionResult) -> str:
        """
        Generate human-readable answer from execution result.
        
        Args:
            intent: Parsed intent from query
            result: Execution result
            
        Returns:
            Formatted answer string
        """
        if result.status != ExecutionStatus.COMPLETED:
            return self._format_error(result)
        
        output = result.final_output
        
        if not output:
            return "No results found."
        
        # Route to intent-specific formatter
        formatters = {
            IntentType.COMPOUND_LOOKUP: self._format_compound_lookup,
            IntentType.PROPERTY_CALCULATION: self._format_properties,
            IntentType.SIMILARITY_SEARCH: self._format_similarity_search,
            IntentType.SUBSTRUCTURE_SEARCH: self._format_substructure_search,
            IntentType.LIPINSKI_CHECK: self._format_lipinski,
            IntentType.ACTIVITY_LOOKUP: self._format_activities,
            IntentType.TARGET_LOOKUP: self._format_target,
            IntentType.STRUCTURE_CONVERSION: self._format_conversion,
            IntentType.SCAFFOLD_ANALYSIS: self._format_scaffold,
            IntentType.COMPARISON: self._format_comparison,
        }
        
        formatter = formatters.get(intent.intent_type, self._format_generic)
        return formatter(output)
    
    def _format_error(self, result: ExecutionResult) -> str:
        """Format error message."""
        error_msg = result.error or "Unknown error - query execution failed"
        
        # Provide user-friendly explanations for common errors
        if "Field not found" in error_msg:
            error_msg += "\n\n💡 **Tip:** This may be due to an unexpected data structure. Try using a ChEMBL ID instead of a compound name."
        elif "got an unexpected keyword argument" in error_msg:
            error_msg += "\n\n💡 **Tip:** This query type may have a configuration issue. Please report this."
        elif "SMILES Parse Error" in error_msg or "Invalid SMILES" in error_msg:
            error_msg += "\n\n💡 **Tip:** The compound name could not be converted to a chemical structure. Try using a ChEMBL ID (e.g., CHEMBL25) or SMILES string instead."
        elif "Empty query provided" in error_msg:
            error_msg = "Empty query - please provide a valid query string."
        elif error_msg == "Unknown error - query execution failed":
            error_msg = "Query execution failed. This may be due to an API timeout or internal error. Please try again."
        
        return f"❌ {error_msg}"
    
    def _format_generic(self, data: Any) -> str:
        """Generic formatter for unhandled intent types."""
        if isinstance(data, dict):
            if data.get("status") == "success":
                count = data.get("count", 0)
                return f"✅ Query completed successfully. Found {count} results."
            elif data.get("status") == "error":
                return f"❌ Error: {data.get('error', 'Unknown error')}"
        
        return str(data)
    
    def _format_compound_lookup(self, data: Dict[str, Any]) -> str:
        """Format compound lookup results."""
        if not isinstance(data, dict):
            return str(data)
        
        if data.get("status") != "success":
            return f"❌ Compound not found: {data.get('error', 'Unknown error')}"
        
        name = data.get("name", "Unknown compound")
        chembl_id = data.get("chembl_id", "N/A")
        smiles = data.get("smiles", "N/A")
        
        answer = f"## {name}\n\n"
        answer += f"**ChEMBL ID:** {chembl_id}\n\n"
        answer += f"**SMILES:** `{smiles}`\n\n"
        
        # Molecular properties
        if data.get("molecular_weight"):
            answer += "### Properties\n\n"
            answer += f"- **Molecular Weight:** {self._safe_float(data['molecular_weight'])} Da\n"
            
            if data.get("alogp") is not None:
                answer += f"- **ALogP:** {self._safe_float(data['alogp'])}\n"
            
            if data.get("psa") is not None:
                answer += f"- **Polar Surface Area:** {self._safe_float(data['psa'])} Ų\n"
            
            if data.get("formula"):
                answer += f"- **Formula:** {data['formula']}\n"
            
            answer += "\n"
        
        # InChI identifiers
        if data.get("inchi_key"):
            answer += "### Identifiers\n\n"
            answer += f"- **InChI Key:** `{data['inchi_key']}`\n"
            if data.get("inchi"):
                answer += f"- **InChI:** `{data['inchi'][:50]}...`\n"
            answer += "\n"
        
        # Synonyms
        if data.get("synonyms"):
            synonyms = data["synonyms"][:10]  # Limit to 10
            answer += "### Synonyms\n\n"
            answer += ", ".join(synonyms)
            if len(data["synonyms"]) > 10:
                answer += f" _(and {len(data['synonyms']) - 10} more)_"
            answer += "\n"
        
        return answer
    
    def _format_properties(self, data: Dict[str, Any]) -> str:
        """Format molecular property calculation results."""
        if not isinstance(data, dict):
            return str(data)
        
        if data.get("status") != "success":
            return f"❌ Property calculation failed: {data.get('error', 'Unknown error')}"
        
        answer = "## Molecular Properties\n\n"
        
        # Basic properties
        if data.get("molecular_weight") is not None:
            answer += f"- **Molecular Weight:** {self._safe_float(data['molecular_weight'])} Da\n"
        
        if data.get("exact_mass") is not None:
            answer += f"- **Exact Mass:** {self._safe_float(data['exact_mass'], decimals=4)} Da\n"
        
        if data.get("logp") is not None:
            answer += f"- **LogP:** {self._safe_float(data['logp'])}\n"
        
        answer += "\n"
        
        # Hydrogen bonding
        answer += "### Hydrogen Bonding\n\n"
        if data.get("h_bond_donors") is not None:
            answer += f"- **H-Bond Donors:** {data['h_bond_donors']}\n"
        
        if data.get("h_bond_acceptors") is not None:
            answer += f"- **H-Bond Acceptors:** {data['h_bond_acceptors']}\n"
        
        if data.get("polar_surface_area") is not None:
            answer += f"- **Polar Surface Area:** {self._safe_float(data['polar_surface_area'])} Ų\n"
        
        answer += "\n"
        
        # Structural features
        answer += "### Structural Features\n\n"
        
        if data.get("rotatable_bonds") is not None:
            answer += f"- **Rotatable Bonds:** {data['rotatable_bonds']}\n"
        
        if data.get("num_rings") is not None:
            answer += f"- **Number of Rings:** {data['num_rings']}\n"
        
        if data.get("num_aromatic_rings") is not None:
            answer += f"- **Aromatic Rings:** {data['num_aromatic_rings']}\n"
        
        if data.get("num_heteroatoms") is not None:
            answer += f"- **Heteroatoms:** {data['num_heteroatoms']}\n"
        
        if data.get("fraction_csp3") is not None:
            answer += f"- **Fraction Csp3:** {self._safe_float(data['fraction_csp3'], decimals=3)}\n"
        
        return answer
    
    def _format_similarity_search(self, data: Dict[str, Any]) -> str:
        """Format similarity search results."""
        if not isinstance(data, dict):
            return str(data)
        
        if data.get("status") != "success":
            return f"❌ Similarity search failed: {data.get('error', 'Unknown error')}"
        
        count = data.get("count", 0)
        threshold = data.get("threshold", "N/A")
        query_smiles = data.get("query_smiles", "N/A")
        
        answer = "## Similarity Search Results\n\n"
        answer += f"**Query SMILES:** `{query_smiles}`\n\n"
        answer += f"**Threshold:** {threshold}\n\n"
        answer += f"**Found:** {count} similar compounds\n\n"
        
        if count == 0:
            answer += "No similar compounds found. Try lowering the similarity threshold.\n"
            return answer
        
        answer += "### Top Matches\n\n"
        
        # Get compounds from either 'compounds' or 'results' key
        compounds = data.get("compounds", data.get("results", []))[:10]  # Show top 10
        
        if not compounds:
            answer += f"_No compound details available (raw count: {count})_\n"
            return answer
        
        for i, compound in enumerate(compounds, 1):
            # Handle both dict and dataclass objects
            if hasattr(compound, '__dict__'):
                # It's a dataclass, access attributes directly
                chembl_id = getattr(compound, 'chembl_id', 'N/A')
                similarity = getattr(compound, 'similarity', None)
                smiles = getattr(compound, 'smiles', None)
                name = getattr(compound, 'name', None)
                
                answer += f"{i}. **{chembl_id}**"
                if name:
                    answer += f" - {name}"
                
                # Display similarity if available
                if similarity is not None:
                    answer += f" (Similarity: {self._safe_float(similarity, decimals=3)})\n"
                else:
                    answer += f" (Match found)\n"
                    
                if smiles:
                    answer += f"   - SMILES: `{smiles}`\n"
            elif isinstance(compound, dict):
                chembl_id = compound.get("chembl_id", "N/A")
                similarity = compound.get("similarity", compound.get("tanimoto_similarity", None))
                smiles = compound.get("smiles", compound.get("canonical_smiles", ""))
                name = compound.get("name", compound.get("pref_name", ""))
                
                answer += f"{i}. **{chembl_id}**"
                if name:
                    answer += f" - {name}"
                
                if similarity is not None:
                    answer += f" (Similarity: {self._safe_float(similarity, decimals=3)})\n"
                else:
                    answer += f" (Match found)\n"
                    
                if smiles:
                    answer += f"   - SMILES: `{smiles}`\n"
        
        if count > 10:
            answer += f"\n_... and {count - 10} more compounds_\n"
        
        return answer
    
    def _format_substructure_search(self, data: Dict[str, Any]) -> str:
        """Format substructure search results."""
        if not isinstance(data, dict):
            return str(data)
        
        if data.get("status") != "success":
            return f"❌ Substructure search failed: {data.get('error', 'Unknown error')}"
        
        count = data.get("count", 0)
        substructure = data.get("substructure", "N/A")
        
        answer = "## Substructure Search Results\n\n"
        answer += f"**Substructure:** `{substructure}`\n\n"
        answer += f"**Found:** {count} matching compounds\n\n"
        
        if count == 0:
            answer += "No compounds containing this substructure found.\n"
            return answer
        
        answer += "### Matches\n\n"
        
        compounds = data.get("compounds", [])[:10]
        
        for i, compound in enumerate(compounds, 1):
            if isinstance(compound, dict):
                chembl_id = compound.get("chembl_id", "N/A")
                answer += f"{i}. {chembl_id}\n"
        
        if count > 10:
            answer += f"\n_... and {count - 10} more compounds_\n"
        
        return answer
    
    def _format_lipinski(self, data: Dict[str, Any]) -> str:
        """Format Lipinski Rule of Five results."""
        if not isinstance(data, dict):
            return str(data)
        
        if data.get("status") != "success":
            return f"❌ Lipinski check failed: {data.get('error', 'Unknown error')}"
        
        passes = data.get("passes_lipinski", False)
        violations = data.get("violations", [])
        
        answer = "## Lipinski Rule of Five\n\n"
        
        if passes:
            answer += "✅ **PASS** - Compound satisfies all Lipinski criteria\n\n"
        else:
            answer += "❌ **FAIL** - Compound violates Lipinski rules\n\n"
            if violations:
                answer += f"**Violations:** {', '.join(violations)}\n\n"
        
        answer += "### Parameters\n\n"
        
        # Molecular weight
        mw = data.get("molecular_weight")
        if mw is not None:
            try:
                mw_float = float(mw)
                status = "✓" if mw_float <= 500 else "✗"
                answer += f"- **Molecular Weight:** {self._safe_float(mw)} Da {status} (limit: ≤ 500)\n"
            except (ValueError, TypeError):
                answer += f"- **Molecular Weight:** {mw}\n"
        
        # LogP
        logp = data.get("logp")
        if logp is not None:
            try:
                logp_float = float(logp)
                status = "✓" if logp_float <= 5 else "✗"
                answer += f"- **LogP:** {self._safe_float(logp)} {status} (limit: ≤ 5)\n"
            except (ValueError, TypeError):
                answer += f"- **LogP:** {logp}\n"
        
        # H-bond donors
        hbd = data.get("h_bond_donors")
        if hbd is not None:
            status = "✓" if hbd <= 5 else "✗"
            answer += f"- **H-Bond Donors:** {hbd} {status} (limit: ≤ 5)\n"
        
        # H-bond acceptors
        hba = data.get("h_bond_acceptors")
        if hba is not None:
            status = "✓" if hba <= 10 else "✗"
            answer += f"- **H-Bond Acceptors:** {hba} {status} (limit: ≤ 10)\n"
        
        return answer
    
    def _format_activities(self, data: Dict[str, Any]) -> str:
        """Format bioactivity data."""
        if not isinstance(data, dict):
            return str(data)
        
        if data.get("status") != "success":
            return f"❌ Activity lookup failed: {data.get('error', 'Unknown error')}"
        
        chembl_id = data.get("chembl_id", "Unknown")
        count = data.get("count", 0)
        
        answer = f"## Bioactivity Data for {chembl_id}\n\n"
        answer += f"**Total Activities:** {count}\n\n"
        
        if count == 0:
            answer += "No bioactivity data found for this compound.\n"
            return answer
        
        activities = data.get("activities", [])[:10]
        
        if activities:
            answer += "### Top Activities\n\n"
            for activity in activities:
                if isinstance(activity, dict):
                    target = activity.get("target_pref_name", "Unknown target")
                    value = activity.get("standard_value", "N/A")
                    units = activity.get("standard_units", "")
                    type_ = activity.get("standard_type", "")
                    
                    answer += f"- **{target}**\n"
                    answer += f"  - {type_}: {value} {units}\n"
        
        if count > 10:
            answer += f"\n_... and {count - 10} more activities_\n"
        
        return answer
    
    def _format_target(self, data: Dict[str, Any]) -> str:
        """Format target information."""
        if not isinstance(data, dict):
            return str(data)
        
        if data.get("status") != "success":
            return f"❌ Target lookup failed: {data.get('error', 'Unknown error')}"
        
        answer = "## Target Information\n\n"
        
        # Check if we have a list of proteins
        proteins = data.get("proteins", [])
        if proteins:
            count = data.get("count", len(proteins))
            answer += f"**Found:** {count} protein(s)\n\n"
            
            for i, protein in enumerate(proteins[:5], 1):  # Show top 5
                # Handle both dict and dataclass
                if hasattr(protein, '__dict__'):
                    uniprot_id = getattr(protein, 'uniprot_id', 'N/A')
                    name = getattr(protein, 'protein_name', None)
                    organism = getattr(protein, 'organism', None)
                    gene = getattr(protein, 'gene_name', None)
                else:
                    uniprot_id = protein.get('uniprot_id', 'N/A')
                    name = protein.get('protein_name', None)
                    organism = protein.get('organism', None)
                    gene = protein.get('gene_name', None)
                
                answer += f"{i}. **{uniprot_id}**"
                if name:
                    answer += f" - {name}"
                answer += "\n"
                
                if organism:
                    answer += f"   - Organism: {organism}\n"
                if gene:
                    answer += f"   - Gene: {gene}\n"
                answer += "\n"
            
            if count > 5:
                answer += f"_... and {count - 5} more proteins_\n"
            
            return answer
        
        # Single target format (legacy)
        if data.get("pref_name"):
            answer += f"**Name:** {data['pref_name']}\n\n"
        
        if data.get("target_type"):
            answer += f"**Type:** {data['target_type']}\n\n"
        
        if data.get("organism"):
            answer += f"**Organism:** {data['organism']}\n\n"
        
        return answer
    
    def _format_conversion(self, data: Dict[str, Any]) -> str:
        """Format structure conversion results."""
        if not isinstance(data, dict):
            return str(data)
        
        if data.get("status") != "success":
            return f"❌ Conversion failed: {data.get('error', 'Unknown error')}"
        
        answer = "## Structure Conversion\n\n"
        
        if data.get("smiles"):
            answer += f"**SMILES:** `{data['smiles']}`\n\n"
        
        if data.get("inchi"):
            answer += f"**InChI:** `{data['inchi']}`\n\n"
        
        if data.get("inchikey"):
            answer += f"**InChI Key:** `{data['inchikey']}`\n\n"
        
        if data.get("mol_block"):
            answer += "**MOL Block:**\n```\n"
            answer += data['mol_block'][:500]  # Limit length
            answer += "\n```\n"
        
        return answer
    
    def _format_scaffold(self, data: Dict[str, Any]) -> str:
        """Format scaffold analysis results."""
        if not isinstance(data, dict):
            return str(data)
        
        if data.get("status") != "success":
            return f"❌ Scaffold extraction failed: {data.get('error', 'Unknown error')}"
        
        answer = "## Scaffold Analysis\n\n"
        
        if data.get("original_smiles"):
            answer += f"**Original SMILES:** `{data['original_smiles']}`\n\n"
        
        if data.get("scaffold_smiles"):
            answer += f"**Murcko Scaffold:** `{data['scaffold_smiles']}`\n\n"
        
        return answer
    
    def _format_comparison(self, data: Dict[str, Any]) -> str:
        """Format comparison results."""
        # Extract compound properties from execution outputs
        # Expected structure: {properties_0: {...}, properties_1: {...}}
        
        properties_list = []
        compound_names = []
        
        # Collect all property results
        for key, value in data.items():
            if key.startswith("properties_"):
                properties_list.append(value)
            elif key.startswith("compound_"):
                # Handle both dict and dataclass for compound results
                if isinstance(value, dict):
                    if "compounds" in value and value["compounds"]:
                        first_compound = value["compounds"][0]
                        if hasattr(first_compound, '__dict__'):
                            # Dataclass
                            name = getattr(first_compound, 'name', None) or getattr(first_compound, 'chembl_id', 'Unknown')
                        else:
                            # Dict
                            name = first_compound.get("name", first_compound.get("chembl_id", "Unknown"))
                        compound_names.append(name)
                elif hasattr(value, '__dict__'):
                    # Direct dataclass object
                    name = getattr(value, 'name', None) or getattr(value, 'chembl_id', 'Unknown')
                    compound_names.append(name)
        
        if len(properties_list) < 2:
            return "❌ Insufficient data for comparison"
        
        # Ensure we have compound names, use generic if missing
        if len(compound_names) < len(properties_list):
            for i in range(len(compound_names), len(properties_list)):
                compound_names.append(f"Compound {i+1}")
        
        # Build comparison table
        answer = "## Property Comparison\n\n"
        
        # Header row
        answer += "| Property | "
        for name in compound_names[:len(properties_list)]:
            answer += f"{name.capitalize()} | "
        answer += "\n"
        
        answer += "|" + "---|" * (len(properties_list) + 1) + "\n"
        
        # Property rows
        properties = [
            ("Molecular Weight", "molecular_weight", "Da"),
            ("Exact Mass", "exact_mass", "Da"),
            ("LogP", "logp", ""),
            ("H-Bond Donors", "num_hbd", ""),
            ("H-Bond Acceptors", "num_hba", ""),
            ("Polar Surface Area", "tpsa", "Ų"),
            ("Rotatable Bonds", "num_rotatable_bonds", ""),
            ("Aromatic Rings", "num_aromatic_rings", ""),
            ("Fraction Csp3", "fraction_csp3", ""),
        ]
        
        for prop_label, prop_key, unit in properties:
            answer += f"| **{prop_label}** | "
            for props in properties_list:
                if isinstance(props, dict) and prop_key in props:
                    value = props[prop_key]
                    formatted_value = self._safe_float(value)
                    if formatted_value != "N/A" and unit:
                        answer += f"{formatted_value} {unit} | "
                    elif formatted_value != "N/A":
                        answer += f"{formatted_value} | "
                    else:
                        answer += "N/A | "
                else:
                    answer += "N/A | "
            answer += "\n"
        
        return answer


# Singleton instance
_formatter = ResponseFormatter()


def format_response(intent: ParsedIntent, result: ExecutionResult) -> str:
    """
    Format execution result into human-readable answer.
    
    Convenience function using singleton formatter.
    
    Args:
        intent: Parsed intent
        result: Execution result
        
    Returns:
        Formatted answer string
    """
    return _formatter.format(intent, result)
