#!/usr/bin/env python
"""
ChemAgent CLI - Command Line Interface

Interactive pharmaceutical research assistant powered by natural language.

Usage:
    python -m chemagent.cli                    # Interactive mode
    python -m chemagent.cli "query"           # Single query
    python -m chemagent.cli --help            # Show help

Examples:
    python -m chemagent.cli "What is CHEMBL25?"
    python -m chemagent.cli "Calculate properties of aspirin"
    python -m chemagent.cli "Find compounds similar to CC(=O)O"
"""

import argparse
import sys
from typing import Optional

from chemagent.caching import ResultCache, add_caching_to_registry
from chemagent.core import (
    ExecutionStatus,
    IntentParser,
    QueryExecutor,
    QueryPlanner,
    ToolRegistry,
)


class ChemAgentCLI:
    """Command-line interface for ChemAgent."""
    
    def __init__(
        self,
        use_real_tools: bool = True,
        verbose: bool = False,
        use_cache: bool = True,
        cache_ttl: int = 3600
    ):
        """
        Initialize CLI.
        
        Args:
            use_real_tools: Use real API calls vs placeholders
            verbose: Show detailed execution information
            use_cache: Enable result caching
            cache_ttl: Cache TTL in seconds
        """
        self.parser = IntentParser()
        self.planner = QueryPlanner()
        
        # Create executor with optional caching
        registry = ToolRegistry(use_real_tools=use_real_tools)
        self.executor = QueryExecutor(tool_registry=registry)
        
        self.cache = None
        if use_cache:
            self.cache = ResultCache(ttl=cache_ttl)
            add_caching_to_registry(registry, self.cache)
        
        self.verbose = verbose
        self.use_cache = use_cache
    
    def process_query(self, query: str) -> None:
        """
        Process a single query and display results.
        
        Args:
            query: Natural language query
        """
        print(f"\n🔍 Query: {query}")
        print("─" * 70)
        
        # Parse
        if self.verbose:
            print("\n1️⃣  Parsing query...")
        intent = self.parser.parse(query)
        
        if self.verbose:
            print(f"   Intent: {intent.intent_type.value}")
            if intent.entities:
                print(f"   Entities: {intent.entities}")
            if intent.constraints:
                print(f"   Constraints: {intent.constraints}")
        
        # Plan
        if self.verbose:
            print("\n2️⃣  Planning execution...")
        plan = self.planner.plan(intent)
        
        if self.verbose:
            print(f"   Steps: {len(plan.steps)}")
            for step in plan.steps:
                deps = f" [depends on {step.depends_on}]" if step.depends_on else ""
                print(f"   - {step.tool_name}{deps}")
        
        # Execute
        if self.verbose:
            print("\n3️⃣  Executing...")
        result = self.executor.execute(plan)
        
        # Display results
        print(f"\n📊 Results:")
        print(f"   Status: {result.status.value}")
        print(f"   Duration: {result.total_duration_ms}ms")
        
        # Show cache stats if enabled
        if self.use_cache and self.verbose:
            stats = self.cache.stats()
            print(f"   Cache: {stats['hits']} hits, {stats['misses']} misses ({stats['hit_rate']:.1%} hit rate)")
        
        if result.status == ExecutionStatus.COMPLETED:
            self._display_output(result.final_output, intent.intent_type.value)
        elif result.status == ExecutionStatus.FAILED:
            print(f"   ✗ Error: {result.error}")
            if self.verbose:
                print(f"\n   Steps completed: {result.steps_completed}")
                print(f"   Steps failed: {result.steps_failed}")
    
    def _display_output(self, output: dict, intent_type: str) -> None:
        """
        Display formatted output based on intent type.
        
        Args:
            output: Result dictionary
            intent_type: Type of intent
        """
        if not output:
            print("   (No results)")
            return
        
        # Check for error status
        if output.get("status") == "error":
            print(f"   ✗ Error: {output.get('error')}")
            return
        
        # Display based on intent type
        if intent_type == "compound_lookup":
            self._display_compound(output)
        elif intent_type == "property_calculation":
            self._display_properties(output)
        elif intent_type == "lipinski_check":
            self._display_lipinski(output)
        elif intent_type in ["similarity_search", "substructure_search"]:
            self._display_search_results(output)
        elif intent_type == "activity_lookup":
            self._display_activities(output)
        else:
            # Generic display
            self._display_generic(output)
    
    def _display_compound(self, data: dict) -> None:
        """Display compound information."""
        print(f"\n   ChEMBL ID: {data.get('chembl_id', 'N/A')}")
        print(f"   Name: {data.get('name', 'N/A')}")
        print(f"   SMILES: {data.get('smiles', 'N/A')}")
        print(f"   Formula: {data.get('formula', 'N/A')}")
        print(f"   MW: {data.get('molecular_weight', 'N/A')}")
        print(f"   ALogP: {data.get('alogp', 'N/A')}")
    
    def _display_properties(self, data: dict) -> None:
        """Display molecular properties."""
        print(f"\n   SMILES: {data.get('smiles', 'N/A')}")
        
        props = data.get('properties', data)
        print(f"\n   Molecular Properties:")
        print(f"   - Molecular Weight: {props.get('molecular_weight', 'N/A')}")
        print(f"   - LogP: {props.get('logp', 'N/A')}")
        print(f"   - H-Bond Donors: {props.get('h_bond_donors', 'N/A')}")
        print(f"   - H-Bond Acceptors: {props.get('h_bond_acceptors', 'N/A')}")
        print(f"   - PSA: {props.get('polar_surface_area', 'N/A')}")
        print(f"   - Rotatable Bonds: {props.get('rotatable_bonds', 'N/A')}")
        print(f"   - Rings: {props.get('num_rings', 'N/A')}")
    
    def _display_lipinski(self, data: dict) -> None:
        """Display Lipinski results."""
        passes = data.get('passes_lipinski', 'N/A')
        violations = data.get('violations', [])
        
        status = "✓ PASS" if passes else "✗ FAIL"
        print(f"\n   Lipinski Rule of Five: {status}")
        
        print(f"\n   Parameters:")
        print(f"   - MW: {data.get('molecular_weight', 'N/A')} (≤ 500)")
        print(f"   - LogP: {data.get('logp', 'N/A')} (≤ 5)")
        print(f"   - H-Donors: {data.get('h_bond_donors', 'N/A')} (≤ 5)")
        print(f"   - H-Acceptors: {data.get('h_bond_acceptors', 'N/A')} (≤ 10)")
        
        if violations:
            print(f"\n   Violations: {', '.join(violations)}")
    
    def _display_search_results(self, data: dict) -> None:
        """Display search results."""
        count = data.get('count', 0)
        compounds = data.get('compounds', [])
        
        print(f"\n   Found {count} compounds")
        
        if compounds:
            print(f"\n   Top Results:")
            for i, compound in enumerate(compounds[:5], 1):
                chembl_id = compound.get('molecule_chembl_id', compound.get('chembl_id', 'N/A'))
                similarity = compound.get('similarity', 'N/A')
                print(f"   {i}. {chembl_id} (similarity: {similarity})")
    
    def _display_activities(self, data: dict) -> None:
        """Display bioactivity data."""
        count = data.get('count', 0)
        activities = data.get('activities', [])
        
        print(f"\n   Found {count} bioactivities")
        
        if activities:
            print(f"\n   Activities:")
            for i, activity in enumerate(activities[:5], 1):
                target = activity.get('target_name', activity.get('target_pref_name', 'N/A'))
                value = activity.get('standard_value', 'N/A')
                units = activity.get('standard_units', '')
                print(f"   {i}. {target}: {value} {units}")
    
    def _display_generic(self, data: dict) -> None:
        """Generic display for unknown result types."""
        for key, value in data.items():
            if key not in ['status', 'provenance']:
                if isinstance(value, (list, dict)):
                    print(f"   {key}: {type(value).__name__} ({len(value)} items)")
                else:
                    print(f"   {key}: {value}")
    
    def interactive_mode(self) -> None:
        """Run interactive query loop."""
        print("\n" + "=" * 70)
        print("  ChemAgent - Pharmaceutical Research Assistant")
        print("=" * 70)
        print("\n  Type your questions in natural language.")
        print("  Commands: 'help', 'examples', 'quit', 'verbose', 'cache', 'clear'")
        
        if self.use_cache:
            print("  💾 Result caching: ENABLED")
        print()
        
        while True:
            try:
                query = input("🧪 > ").strip()
                
                if not query:
                    continue
                
                # Handle commands
                if query.lower() in ['quit', 'exit', 'q']:
                    print("\n👋 Goodbye!\n")
                    break
                
                elif query.lower() == 'help':
                    self._show_help()
                    continue
                
                elif query.lower() == 'examples':
                    self._show_examples()
                    continue
                
                elif query.lower() == 'verbose':
                    self.verbose = not self.verbose
                    status = "ON" if self.verbose else "OFF"
                    print(f"\n   Verbose mode: {status}")
                    continue
                
                elif query.lower() == 'cache':
                    if self.cache:
                        stats = self.cache.stats()
                        print(f"\n   Cache Statistics:")
                        print(f"   - Hits: {stats['hits']}")
                        print(f"   - Misses: {stats['misses']}")
                        print(f"   - Hit Rate: {stats['hit_rate']:.1%}")
                        print(f"   - Cached Items: {stats['cache_size']}")
                    else:
                        print("\n   Caching is disabled")
                    continue
                
                elif query.lower() == 'clear':
                    if self.cache:
                        self.cache.clear()
                        print("\n   ✓ Cache cleared")
                    else:
                        print("\n   Caching is disabled")
                    continue
                
                # Process query
                self.process_query(query)
                
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!\n")
                break
            except Exception as e:
                print(f"\n✗ Error: {e}")
                if self.verbose:
                    import traceback
                    traceback.print_exc()
    
    def _show_help(self) -> None:
        """Show help message."""
        print("""
📚 ChemAgent Help

Natural Language Queries:
  - "What is CHEMBL25?"
  - "Calculate properties of aspirin"
  - "Find compounds similar to CC(=O)O"
  - "Check Lipinski for ibuprofen"
  - "What is the activity of aspirin against COX-2?"

Supported Intent Types:
  - Compound lookup (ChEMBL ID or name)
  - Property calculation (SMILES or compound name)
  - Similarity search (find similar compounds)
  - Substructure search (compounds containing pattern)
  - Lipinski Rule of Five check
  - Bioactivity lookup
  - Target information

Commands:
  help      - Show this help
  examples  - Show example queries
  verbose   - Toggle verbose output
  cache     - Show cache statistics
  clear     - Clear result cache
  quit      - Exit ChemAgent
        """)
    
    def _show_examples(self) -> None:
        """Show example queries."""
        print("""
💡 Example Queries

Compound Information:
  > What is CHEMBL25?
  > Tell me about aspirin
  > Find information on ibuprofen

Property Calculations:
  > Calculate properties of CC(=O)Oc1ccccc1C(=O)O
  > What are the properties of aspirin?
  > Compute molecular descriptors for CHEMBL25

Drug-Likeness:
  > Check Lipinski for aspirin
  > Is CC(=O)O drug-like?
  > Evaluate CHEMBL25 for oral bioavailability

Similarity Searching:
  > Find compounds similar to aspirin
  > Similar molecules to CC(=O)O
  > Search for aspirin analogs

Bioactivity:
  > What is the activity of aspirin?
  > Activities of CHEMBL25
  > Aspirin vs COX-2
        """)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="ChemAgent - Pharmaceutical Research Assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                              # Interactive mode
  %(prog)s "What is CHEMBL25?"         # Single query
  %(prog)s --verbose "Calculate..."     # Verbose output
  %(prog)s --no-api                     # Use placeholder tools
        """
    )
    
    parser.add_argument(
        "query",
        nargs="?",
        help="Query to process (omit for interactive mode)"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show detailed execution information"
    )
    
    parser.add_argument(
        "--no-api",
        action="store_true",
        help="Use placeholder tools (no real API calls)"
    )
    
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable result caching"
    )
    
    parser.add_argument(
        "--cache-ttl",
        type=int,
        default=3600,
        help="Cache TTL in seconds (default: 3600 = 1 hour)"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="ChemAgent 1.0.0"
    )
    
    args = parser.parse_args()
    
    # Create CLI
    cli = ChemAgentCLI(
        use_real_tools=not args.no_api,
        verbose=args.verbose,
        use_cache=not args.no_cache,
        cache_ttl=args.cache_ttl
    )
    
    # Run
    if args.query:
        # Single query mode
        cli.process_query(args.query)
    else:
        # Interactive mode
        cli.interactive_mode()


if __name__ == "__main__":
    main()
