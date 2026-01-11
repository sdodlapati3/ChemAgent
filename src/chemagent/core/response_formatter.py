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
        }
        
        formatter = formatters.get(intent.intent_type, self._format_generic)
        return formatter(output)
    
    def _format_error(self, result: ExecutionResult) -> str:
        """Format error message."""
        error_msg = result.error or "Unknown error"
        return f"❌ Query failed: {error_msg}"
    
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
            answer += f"- **Molecular Weight:** {data['molecular_weight']:.2f} Da\n"
            
            if data.get("alogp") is not None:
                answer += f"- **ALogP:** {data['alogp']:.2f}\n"
            
            if data.get("psa") is not None:
                answer += f"- **Polar Surface Area:** {data['psa']:.2f} Ų\n"
            
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
            answer += f"- **Molecular Weight:** {data['molecular_weight']:.2f} Da\n"
        
        if data.get("exact_mass") is not None:
            answer += f"- **Exact Mass:** {data['exact_mass']:.4f} Da\n"
        
        if data.get("logp") is not None:
            answer += f"- **LogP:** {data['logp']:.2f}\n"
        
        answer += "\n"
        
        # Hydrogen bonding
        answer += "### Hydrogen Bonding\n\n"
        if data.get("h_bond_donors") is not None:
            answer += f"- **H-Bond Donors:** {data['h_bond_donors']}\n"
        
        if data.get("h_bond_acceptors") is not None:
            answer += f"- **H-Bond Acceptors:** {data['h_bond_acceptors']}\n"
        
        if data.get("polar_surface_area") is not None:
            answer += f"- **Polar Surface Area:** {data['polar_surface_area']:.2f} Ų\n"
        
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
            answer += f"- **Fraction Csp3:** {data['fraction_csp3']:.3f}\n"
        
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
        
        compounds = data.get("compounds", [])[:10]  # Show top 10
        
        for i, compound in enumerate(compounds, 1):
            if isinstance(compound, dict):
                chembl_id = compound.get("chembl_id", "N/A")
                similarity = compound.get("similarity", 0)
                smiles = compound.get("smiles", "")
                
                answer += f"{i}. **{chembl_id}** (Similarity: {similarity:.3f})\n"
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
            status = "✓" if mw <= 500 else "✗"
            answer += f"- **Molecular Weight:** {mw:.2f} Da {status} (limit: ≤ 500)\n"
        
        # LogP
        logp = data.get("logp")
        if logp is not None:
            status = "✓" if logp <= 5 else "✗"
            answer += f"- **LogP:** {logp:.2f} {status} (limit: ≤ 5)\n"
        
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
