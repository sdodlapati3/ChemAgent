"""
Query planner for converting intents to execution plans.

Takes parsed intents and generates multi-step execution plans with
dependency tracking and parallel execution support.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from chemagent.core.intent_parser import IntentType, ParsedIntent


@dataclass
class PlanStep:
    """
    Single execution step in a query plan.
    
    Attributes:
        step_id: Unique identifier for this step
        tool_name: Name of tool to invoke
        args: Arguments to pass to tool
        depends_on: List of step IDs this depends on
        can_run_parallel: Whether this can run in parallel with other steps
        output_name: Variable name to store output
        estimated_time_ms: Estimated execution time
    """
    
    step_id: int
    tool_name: str
    args: Dict[str, Any]
    depends_on: List[int] = field(default_factory=list)
    can_run_parallel: bool = False
    output_name: str = ""
    estimated_time_ms: int = 100
    
    def __repr__(self) -> str:
        """String representation."""
        deps = f", depends_on={self.depends_on}" if self.depends_on else ""
        return f"Step{self.step_id}({self.tool_name}{deps})"


@dataclass
class QueryPlan:
    """
    Execution plan for a query.
    
    Contains ordered steps with dependency information and
    resource estimates.
    
    Attributes:
        steps: List of execution steps
        intent_type: Original intent type
        estimated_time_ms: Total estimated execution time
        estimated_cost: Estimated API cost (in credits)
        can_cache: Whether results can be cached
    """
    
    steps: List[PlanStep]
    intent_type: IntentType
    estimated_time_ms: int = 0
    estimated_cost: float = 0.0
    can_cache: bool = True
    
    def __repr__(self) -> str:
        """String representation."""
        return f"QueryPlan({self.intent_type.value}, {len(self.steps)} steps, ~{self.estimated_time_ms}ms)"
    
    def get_parallel_groups(self) -> List[List[PlanStep]]:
        """
        Group steps that can run in parallel.
        
        Returns:
            List of step groups that can execute in parallel
        """
        groups = []
        executed = set()
        
        while len(executed) < len(self.steps):
            # Find steps whose dependencies are satisfied
            ready = []
            for step in self.steps:
                if step.step_id not in executed:
                    if all(dep in executed for dep in step.depends_on):
                        ready.append(step)
            
            if not ready:
                # Circular dependency or error
                break
            
            groups.append(ready)
            executed.update(s.step_id for s in ready)
        
        return groups


class QueryPlanner:
    """
    Generates execution plans from parsed intents.
    
    Converts high-level user intents into concrete execution plans
    with proper dependency ordering and optimization.
    
    Now with LLM-based fallback for UNKNOWN intents.
    
    Example:
        >>> parser = IntentParser()
        >>> planner = QueryPlanner()
        >>> intent = parser.parse("Find compounds similar to aspirin")
        >>> plan = planner.plan(intent)
        >>> len(plan.steps)
        3
    """
    
    def __init__(self, llm_router=None):
        """Initialize planner.
        
        Args:
            llm_router: Optional LLMRouter for handling unknown intents
        """
        self.step_counter = 0
        self.llm_router = llm_router
    
    def plan(self, intent: ParsedIntent) -> QueryPlan:
        """
        Generate execution plan from parsed intent.
        
        Args:
            intent: Parsed user intent with entities
            
        Returns:
            Executable query plan
            
        Example:
            >>> intent = ParsedIntent(
            ...     intent_type=IntentType.SIMILARITY_SEARCH,
            ...     entities={"compound": "aspirin", "threshold": 0.8}
            ... )
            >>> plan = planner.plan(intent)
            >>> plan.intent_type
            <IntentType.SIMILARITY_SEARCH: 'similarity_search'>
        """
        self.step_counter = 0  # Reset for each plan
        
        # Route to appropriate planner based on intent type
        if intent.intent_type == IntentType.SIMILARITY_SEARCH:
            return self._plan_similarity_search(intent)
        
        elif intent.intent_type == IntentType.SUBSTRUCTURE_SEARCH:
            return self._plan_substructure_search(intent)
        
        elif intent.intent_type == IntentType.COMPOUND_LOOKUP:
            return self._plan_compound_lookup(intent)
        
        elif intent.intent_type == IntentType.TARGET_LOOKUP:
            return self._plan_target_lookup(intent)
        
        elif intent.intent_type == IntentType.PROPERTY_CALCULATION:
            return self._plan_property_calculation(intent)
        
        elif intent.intent_type == IntentType.PROPERTY_FILTER:
            return self._plan_property_filter(intent)
        
        elif intent.intent_type == IntentType.LIPINSKI_CHECK:
            return self._plan_lipinski_check(intent)
        
        elif intent.intent_type == IntentType.ACTIVITY_LOOKUP:
            return self._plan_activity_lookup(intent)
        
        elif intent.intent_type == IntentType.STRUCTURE_CONVERSION:
            return self._plan_structure_conversion(intent)
        
        elif intent.intent_type == IntentType.STANDARDIZATION:
            return self._plan_standardization(intent)
        
        elif intent.intent_type == IntentType.SCAFFOLD_ANALYSIS:
            return self._plan_scaffold_analysis(intent)
        
        elif intent.intent_type == IntentType.COMPARISON:
            return self._plan_comparison(intent)
        
        elif intent.intent_type == IntentType.DISEASE_TARGET_LOOKUP:
            return self._plan_disease_target_lookup(intent)
        
        elif intent.intent_type == IntentType.TARGET_DISEASE_LOOKUP:
            return self._plan_target_disease_lookup(intent)
        
        elif intent.intent_type == IntentType.TARGET_DRUG_LOOKUP:
            return self._plan_target_drug_lookup(intent)
        
        elif intent.intent_type == IntentType.STRUCTURE_LOOKUP:
            return self._plan_structure_lookup(intent)
        
        elif intent.intent_type == IntentType.ALPHAFOLD_LOOKUP:
            return self._plan_alphafold_lookup(intent)
        
        else:
            # Unknown intent - try LLM-based planning if available
            return self._plan_unknown(intent)
    
    def _plan_unknown(self, intent: ParsedIntent) -> QueryPlan:
        """
        Handle unknown intents with best-effort planning.
        
        If entities were extracted (e.g., compound name), try to make
        a reasonable plan. Otherwise return empty.
        """
        entities = intent.entities
        steps = []
        
        # If we have a compound, at least do a lookup
        if "compound" in entities or "chembl_id" in entities:
            steps.append(PlanStep(
                step_id=self._next_step_id(),
                tool_name="chembl_search_by_name" if "compound" in entities else "chembl_get_compound",
                args={"query": entities.get("compound") or entities.get("chembl_id")},
                depends_on=[],
                can_run_parallel=False,
                output_name="compound_info",
                estimated_time_ms=500
            ))
        
        # If we have a target/protein, look it up
        if "target" in entities or "uniprot_id" in entities:
            steps.append(PlanStep(
                step_id=self._next_step_id(),
                tool_name="uniprot_get_protein",
                args={"query": entities.get("target") or entities.get("uniprot_id")},
                depends_on=[],
                can_run_parallel=True,
                output_name="target_info",
                estimated_time_ms=500
            ))
        
        # If we have SMILES, calculate properties
        if "smiles" in entities:
            steps.append(PlanStep(
                step_id=self._next_step_id(),
                tool_name="calculate_properties",
                args={"smiles": entities["smiles"]},
                depends_on=[],
                can_run_parallel=True,
                output_name="properties",
                estimated_time_ms=50
            ))
        
        return QueryPlan(
            steps=steps,
            intent_type=intent.intent_type,
            estimated_time_ms=sum(s.estimated_time_ms for s in steps),
            can_cache=len(steps) > 0
        )
    
    def _next_step_id(self) -> int:
        """Get next step ID."""
        step_id = self.step_counter
        self.step_counter += 1
        return step_id
    
    def _plan_similarity_search(self, intent: ParsedIntent) -> QueryPlan:
        """
        Plan similarity search.
        
        Steps:
        1. Resolve compound name → SMILES (if needed)
        2. Standardize SMILES
        3. ChEMBL similarity search
        4. Filter by constraints (optional)
        5. Calculate properties (optional)
        """
        steps = []
        entities = intent.entities
        
        # Step 1: Get SMILES
        smiles_ref = None
        
        if "smiles" in entities:
            # Already have SMILES
            smiles_ref = entities["smiles"]
        
        elif "compound" in entities or "chembl_id" in entities:
            # Need to look up compound first
            lookup_step = PlanStep(
                step_id=self._next_step_id(),
                tool_name="chembl_search_by_name" if "compound" in entities else "chembl_get_compound",
                args={
                    "query": entities.get("compound") or entities.get("chembl_id")
                },
                depends_on=[],
                can_run_parallel=False,
                output_name="compound_data",
                estimated_time_ms=500
            )
            steps.append(lookup_step)
            # search_by_name returns {compounds: [...]}, get_compound returns {smiles: ...}
            smiles_ref = "$compound_data.compounds[0].smiles" if "compound" in entities else "$compound_data.smiles"
        
        # Step 2: Standardize SMILES
        if smiles_ref:
            standardize_step = PlanStep(
                step_id=self._next_step_id(),
                tool_name="rdkit_standardize_smiles",
                args={"smiles": smiles_ref},
                depends_on=[steps[-1].step_id] if steps else [],
                can_run_parallel=False,
                output_name="standardized",
                estimated_time_ms=50
            )
            steps.append(standardize_step)
            smiles_ref = "$standardized.canonical_smiles"
        
        # Step 3: Similarity search
        similarity_step = PlanStep(
            step_id=self._next_step_id(),
            tool_name="chembl_similarity_search",
            args={
                "smiles": smiles_ref,
                "threshold": entities.get("threshold", 0.7),
                "limit": entities.get("limit", 100)
            },
            depends_on=[steps[-1].step_id] if steps else [],
            can_run_parallel=False,
            output_name="similar_compounds",
            estimated_time_ms=2000
        )
        steps.append(similarity_step)
        
        # Step 4: Filter by constraints (if provided)
        if intent.constraints:
            filter_step = PlanStep(
                step_id=self._next_step_id(),
                tool_name="filter_by_properties",
                args={
                    "compounds": "$similar_compounds",
                    "constraints": intent.constraints
                },
                depends_on=[similarity_step.step_id],
                can_run_parallel=False,
                output_name="filtered_compounds",
                estimated_time_ms=200
            )
            steps.append(filter_step)
        
        # Calculate total time and cost
        total_time = sum(s.estimated_time_ms for s in steps)
        total_cost = len(steps) * 0.01  # Estimate 0.01 credits per step
        
        return QueryPlan(
            steps=steps,
            intent_type=intent.intent_type,
            estimated_time_ms=total_time,
            estimated_cost=total_cost,
            can_cache=True
        )
    
    def _plan_substructure_search(self, intent: ParsedIntent) -> QueryPlan:
        """
        Plan substructure search.
        
        Steps:
        1. Convert functional group to SMARTS (if needed)
        2. Search compounds with substructure
        """
        steps = []
        entities = intent.entities
        
        smarts = entities.get("smarts") or entities.get("functional_group")
        
        if smarts:
            search_step = PlanStep(
                step_id=self._next_step_id(),
                tool_name="chembl_substructure_search",
                args={"smiles": smarts, "limit": entities.get("limit", 100)},
                depends_on=[],
                can_run_parallel=False,
                output_name="matches",
                estimated_time_ms=1500
            )
            steps.append(search_step)
        
        return QueryPlan(
            steps=steps,
            intent_type=intent.intent_type,
            estimated_time_ms=sum(s.estimated_time_ms for s in steps),
            estimated_cost=0.02,
            can_cache=True
        )
    
    def _plan_compound_lookup(self, intent: ParsedIntent) -> QueryPlan:
        """
        Plan compound lookup.
        
        Steps:
        1. Search by name or get by ChEMBL ID
        2. Optionally get additional properties
        """
        steps = []
        entities = intent.entities
        
        if "chembl_id" in entities:
            lookup_step = PlanStep(
                step_id=self._next_step_id(),
                tool_name="chembl_get_compound",
                args={"chembl_id": entities["chembl_id"]},
                depends_on=[],
                can_run_parallel=False,
                output_name="compound",
                estimated_time_ms=300
            )
        else:
            lookup_step = PlanStep(
                step_id=self._next_step_id(),
                tool_name="chembl_search_by_name",
                args={"query": entities.get("compound", "")},
                depends_on=[],
                can_run_parallel=False,
                output_name="compound",
                estimated_time_ms=500
            )
        
        steps.append(lookup_step)
        
        return QueryPlan(
            steps=steps,
            intent_type=intent.intent_type,
            estimated_time_ms=sum(s.estimated_time_ms for s in steps),
            estimated_cost=0.01,
            can_cache=True
        )
    
    def _plan_target_lookup(self, intent: ParsedIntent) -> QueryPlan:
        """
        Plan target/protein lookup.
        
        Steps:
        1. Search UniProt by name or get by ID
        """
        steps = []
        entities = intent.entities
        
        if "uniprot_id" in entities:
            lookup_step = PlanStep(
                step_id=self._next_step_id(),
                tool_name="uniprot_get_protein",
                args={"uniprot_id": entities["uniprot_id"]},
                depends_on=[],
                can_run_parallel=False,
                output_name="protein",
                estimated_time_ms=400
            )
        elif "target" in entities and entities["target"]:
            lookup_step = PlanStep(
                step_id=self._next_step_id(),
                tool_name="uniprot_search",
                args={"query": entities["target"]},
                depends_on=[],
                can_run_parallel=False,
                output_name="protein",
                estimated_time_ms=500
            )
        else:
            # No valid target specified - create a dummy step that will fail gracefully
            # This shouldn't happen if intent parser works correctly, but handle it anyway
            lookup_step = PlanStep(
                step_id=self._next_step_id(),
                tool_name="uniprot_search",
                args={"query": "protein"},  # Generic fallback
                depends_on=[],
                can_run_parallel=False,
                output_name="protein",
                estimated_time_ms=500
            )
        
        steps.append(lookup_step)
        
        return QueryPlan(
            steps=steps,
            intent_type=intent.intent_type,
            estimated_time_ms=sum(s.estimated_time_ms for s in steps),
            estimated_cost=0.01,
            can_cache=True
        )
    
    def _plan_property_calculation(self, intent: ParsedIntent) -> QueryPlan:
        """
        Plan property calculation.
        
        Steps:
        1. Get/resolve SMILES (if needed)
        2. Standardize SMILES
        3. Calculate properties
        """
        steps = []
        entities = intent.entities
        
        # Get SMILES
        smiles_ref = None
        
        if "smiles" in entities:
            smiles_ref = entities["smiles"]
        elif "compound" in entities:
            lookup_step = PlanStep(
                step_id=self._next_step_id(),
                tool_name="chembl_search_by_name",
                args={"query": entities["compound"]},
                depends_on=[],
                can_run_parallel=False,
                output_name="compound_data",
                estimated_time_ms=500
            )
            steps.append(lookup_step)
            smiles_ref = "$compound_data.compounds[0].smiles"
        
        # Standardize
        if smiles_ref:
            standardize_step = PlanStep(
                step_id=self._next_step_id(),
                tool_name="rdkit_standardize_smiles",
                args={"smiles": smiles_ref},
                depends_on=[steps[-1].step_id] if steps else [],
                can_run_parallel=False,
                output_name="standardized",
                estimated_time_ms=50
            )
            steps.append(standardize_step)
            
            # Calculate properties
            props_step = PlanStep(
                step_id=self._next_step_id(),
                tool_name="rdkit_calc_properties",
                args={"smiles": "$standardized.smiles"},
                depends_on=[standardize_step.step_id],
                can_run_parallel=False,
                output_name="properties",
                estimated_time_ms=100
            )
            steps.append(props_step)
        
        return QueryPlan(
            steps=steps,
            intent_type=intent.intent_type,
            estimated_time_ms=sum(s.estimated_time_ms for s in steps),
            estimated_cost=0.01,
            can_cache=True
        )
    
    def _plan_property_filter(self, intent: ParsedIntent) -> QueryPlan:
        """
        Plan property-based filtering.
        
        This assumes we have a list of compounds to filter.
        """
        steps = []
        
        filter_step = PlanStep(
            step_id=self._next_step_id(),
            tool_name="filter_by_properties",
            args={"constraints": intent.constraints},
            depends_on=[],
            can_run_parallel=False,
            output_name="filtered",
            estimated_time_ms=200
        )
        steps.append(filter_step)
        
        return QueryPlan(
            steps=steps,
            intent_type=intent.intent_type,
            estimated_time_ms=200,
            estimated_cost=0.01,
            can_cache=True
        )
    
    def _plan_lipinski_check(self, intent: ParsedIntent) -> QueryPlan:
        """
        Plan Lipinski rule checking.
        
        Steps:
        1. Get/resolve SMILES
        2. Standardize
        3. Check Lipinski
        """
        steps = []
        entities = intent.entities
        
        # Get SMILES
        smiles_ref = None
        
        if "smiles" in entities:
            smiles_ref = entities["smiles"]
        elif "compound" in entities:
            lookup_step = PlanStep(
                step_id=self._next_step_id(),
                tool_name="chembl_search_by_name",
                args={"query": entities["compound"]},
                depends_on=[],
                can_run_parallel=False,
                output_name="compound_data",
                estimated_time_ms=500
            )
            steps.append(lookup_step)
            smiles_ref = "$compound_data.compounds[0].smiles"
        
        # Standardize and check
        if smiles_ref:
            standardize_step = PlanStep(
                step_id=self._next_step_id(),
                tool_name="rdkit_standardize_smiles",
                args={"smiles": smiles_ref},
                depends_on=[steps[-1].step_id] if steps else [],
                can_run_parallel=False,
                output_name="standardized",
                estimated_time_ms=50
            )
            steps.append(standardize_step)
            
            lipinski_step = PlanStep(
                step_id=self._next_step_id(),
                tool_name="rdkit_calc_lipinski",
                args={"smiles": "$standardized.smiles"},
                depends_on=[standardize_step.step_id],
                can_run_parallel=False,
                output_name="lipinski",
                estimated_time_ms=100
            )
            steps.append(lipinski_step)
        
        return QueryPlan(
            steps=steps,
            intent_type=intent.intent_type,
            estimated_time_ms=sum(s.estimated_time_ms for s in steps),
            estimated_cost=0.01,
            can_cache=True
        )
    
    def _plan_activity_lookup(self, intent: ParsedIntent) -> QueryPlan:
        """
        Plan bioactivity data lookup.
        
        Steps:
        1. Get compound ID (if needed)
        2. Get activities for compound
        3. Filter by target (optional)
        """
        steps = []
        entities = intent.entities
        
        compound_ref = None
        
        if "chembl_id" in entities:
            compound_ref = entities["chembl_id"]
        elif "compound" in entities:
            lookup_step = PlanStep(
                step_id=self._next_step_id(),
                tool_name="chembl_search_by_name",
                args={"query": entities["compound"]},
                depends_on=[],
                can_run_parallel=False,
                output_name="compound_data",
                estimated_time_ms=500
            )
            steps.append(lookup_step)
            compound_ref = "$compound_data.compounds[0].chembl_id"
        
        # Get activities
        if compound_ref:
            activity_args = {"chembl_id": compound_ref}
            if "activity_type" in entities:
                # Map activity_type to target parameter for the tool
                activity_args["target"] = entities["activity_type"]
            
            activity_step = PlanStep(
                step_id=self._next_step_id(),
                tool_name="chembl_get_activities",
                args=activity_args,
                depends_on=[steps[-1].step_id] if steps else [],
                can_run_parallel=False,
                output_name="activities",
                estimated_time_ms=800
            )
            steps.append(activity_step)
        
        return QueryPlan(
            steps=steps,
            intent_type=intent.intent_type,
            estimated_time_ms=sum(s.estimated_time_ms for s in steps),
            estimated_cost=0.02,
            can_cache=True
        )
    
    def _plan_structure_conversion(self, intent: ParsedIntent) -> QueryPlan:
        """
        Plan structure format conversion.
        
        Steps:
        1. Standardize input SMILES
        2. Generate target format
        """
        steps = []
        entities = intent.entities
        
        if "smiles" in entities:
            convert_step = PlanStep(
                step_id=self._next_step_id(),
                tool_name="rdkit_convert_format",
                args={
                    "smiles": entities["smiles"],
                    "to_format": entities.get("format", "inchi")
                },
                depends_on=[],
                can_run_parallel=False,
                output_name="converted",
                estimated_time_ms=50
            )
            steps.append(convert_step)
        
        return QueryPlan(
            steps=steps,
            intent_type=intent.intent_type,
            estimated_time_ms=50,
            estimated_cost=0.0,
            can_cache=True
        )
    
    def _plan_standardization(self, intent: ParsedIntent) -> QueryPlan:
        """
        Plan SMILES standardization.
        
        Steps:
        1. Standardize SMILES
        """
        steps = []
        entities = intent.entities
        
        if "smiles" in entities or "compound" in entities:
            smiles = entities.get("smiles")
            
            if not smiles and "compound" in entities:
                # Need to look up first
                lookup_step = PlanStep(
                    step_id=self._next_step_id(),
                    tool_name="chembl_search_by_name",
                    args={"query": entities["compound"]},
                    depends_on=[],
                    can_run_parallel=False,
                    output_name="compound_data",
                    estimated_time_ms=500
                )
                steps.append(lookup_step)
                smiles = "$compound_data.compounds[0].smiles"
            
            standardize_step = PlanStep(
                step_id=self._next_step_id(),
                tool_name="rdkit_standardize_smiles",
                args={"smiles": smiles},
                depends_on=[steps[-1].step_id] if steps else [],
                can_run_parallel=False,
                output_name="standardized",
                estimated_time_ms=50
            )
            steps.append(standardize_step)
        
        return QueryPlan(
            steps=steps,
            intent_type=intent.intent_type,
            estimated_time_ms=sum(s.estimated_time_ms for s in steps),
            estimated_cost=0.0,
            can_cache=True
        )
    
    def _plan_scaffold_analysis(self, intent: ParsedIntent) -> QueryPlan:
        """
        Plan scaffold extraction.
        
        Steps:
        1. Get/resolve SMILES
        2. Extract Murcko scaffold
        """
        steps = []
        entities = intent.entities
        
        smiles_ref = None
        
        if "smiles" in entities:
            smiles_ref = entities["smiles"]
        elif "compound" in entities:
            lookup_step = PlanStep(
                step_id=self._next_step_id(),
                tool_name="chembl_search_by_name",
                args={"query": entities["compound"]},
                depends_on=[],
                can_run_parallel=False,
                output_name="compound_data",
                estimated_time_ms=500
            )
            steps.append(lookup_step)
            smiles_ref = "$compound_data.compounds[0].smiles"
        
        if smiles_ref:
            scaffold_step = PlanStep(
                step_id=self._next_step_id(),
                tool_name="rdkit_extract_scaffold",
                args={"smiles": smiles_ref},
                depends_on=[steps[-1].step_id] if steps else [],
                can_run_parallel=False,
                output_name="scaffold",
                estimated_time_ms=100
            )
            steps.append(scaffold_step)
        
        return QueryPlan(
            steps=steps,
            intent_type=intent.intent_type,
            estimated_time_ms=sum(s.estimated_time_ms for s in steps),
            estimated_cost=0.01,
            can_cache=True
        )    
    def _plan_comparison(self, intent: ParsedIntent) -> QueryPlan:
        """
        Plan comparison of multiple compounds.
        
        Steps:
        1. Look up each compound (parallel)
        2. Standardize SMILES for each (can be parallel across compounds)
        3. Calculate properties for each (can be parallel across compounds)
        4. Return for comparison formatting
        
        Optimization: Group steps by phase to maximize parallelization
        """
        steps = []
        entities = intent.entities
        
        compounds = entities.get("compounds", [])
        if len(compounds) < 2:
            return QueryPlan(
                steps=steps,
                intent_type=intent.intent_type,
                estimated_time_ms=0,
                estimated_cost=0.0
            )
        
        # Phase 1: Look up all compounds (can run in parallel)
        lookup_step_ids = []
        for i, compound in enumerate(compounds):
            lookup_step = PlanStep(
                step_id=self._next_step_id(),
                tool_name="chembl_search_by_name",
                args={"query": compound},
                depends_on=[],
                can_run_parallel=True,  # All lookups can run in parallel
                output_name=f"compound_{i}",
                estimated_time_ms=500
            )
            steps.append(lookup_step)
            lookup_step_ids.append(lookup_step.step_id)
        
        # Phase 2: Standardize SMILES for each compound
        # Each standardize depends only on its own lookup, so can run in parallel
        standardize_step_ids = []
        for i in range(len(compounds)):
            standardize_step = PlanStep(
                step_id=self._next_step_id(),
                tool_name="rdkit_standardize_smiles",
                args={"smiles": f"$compound_{i}.compounds[0].smiles"},
                depends_on=[lookup_step_ids[i]],
                can_run_parallel=True,  # Can run in parallel with other standardizations
                output_name=f"standardized_{i}",
                estimated_time_ms=50
            )
            steps.append(standardize_step)
            standardize_step_ids.append(standardize_step.step_id)
        
        # Phase 3: Calculate properties for each compound
        # Each calc depends only on its own standardization, so can run in parallel
        for i in range(len(compounds)):
            props_step = PlanStep(
                step_id=self._next_step_id(),
                tool_name="rdkit_calc_properties",
                args={"smiles": f"$standardized_{i}.smiles"},
                depends_on=[standardize_step_ids[i]],
                can_run_parallel=True,  # Can run in parallel with other calculations
                output_name=f"properties_{i}",
                estimated_time_ms=100
            )
            steps.append(props_step)
        
        return QueryPlan(
            steps=steps,
            intent_type=intent.intent_type,
            estimated_time_ms=sum(s.estimated_time_ms for s in steps),
            estimated_cost=0.02
        )
    
    # =========================================================================
    # Open Targets Planning Methods
    # =========================================================================
    
    def _plan_disease_target_lookup(self, intent: ParsedIntent) -> QueryPlan:
        """
        Plan disease-target association lookup using Open Targets.
        
        Steps:
        1. Search for disease in Open Targets
        2. Get targets associated with the disease
        """
        steps = []
        entities = intent.entities
        
        disease = entities.get("disease", "")
        
        if not disease:
            return QueryPlan(
                steps=steps,
                intent_type=intent.intent_type,
                estimated_time_ms=0,
                estimated_cost=0.0
            )
        
        # Step 1: Search for disease
        search_step = PlanStep(
            step_id=self._next_step_id(),
            tool_name="opentargets_search",
            args={"query": disease, "entity_types": ["disease"]},
            depends_on=[],
            output_name="disease_search",
            estimated_time_ms=300
        )
        steps.append(search_step)
        
        # Step 2: Get disease targets
        targets_step = PlanStep(
            step_id=self._next_step_id(),
            tool_name="opentargets_disease_targets",
            args={"efo_id": "$disease_search.results[0].id", "limit": 25},
            depends_on=[search_step.step_id],
            output_name="disease_targets",
            estimated_time_ms=500
        )
        steps.append(targets_step)
        
        return QueryPlan(
            steps=steps,
            intent_type=intent.intent_type,
            estimated_time_ms=sum(s.estimated_time_ms for s in steps),
            estimated_cost=0.0
        )
    
    def _plan_target_disease_lookup(self, intent: ParsedIntent) -> QueryPlan:
        """
        Plan target-disease association lookup using Open Targets.
        
        Steps:
        1. Search for target in Open Targets
        2. Get diseases associated with the target
        """
        steps = []
        entities = intent.entities
        
        target = entities.get("target", "")
        
        if not target:
            return QueryPlan(
                steps=steps,
                intent_type=intent.intent_type,
                estimated_time_ms=0,
                estimated_cost=0.0
            )
        
        # Step 1: Search for target
        search_step = PlanStep(
            step_id=self._next_step_id(),
            tool_name="opentargets_search",
            args={"query": target, "entity_types": ["target"]},
            depends_on=[],
            output_name="target_search",
            estimated_time_ms=300
        )
        steps.append(search_step)
        
        # Step 2: Get target diseases
        diseases_step = PlanStep(
            step_id=self._next_step_id(),
            tool_name="opentargets_target_diseases",
            args={"ensembl_id": "$target_search.results[0].id", "limit": 25},
            depends_on=[search_step.step_id],
            output_name="target_diseases",
            estimated_time_ms=500
        )
        steps.append(diseases_step)
        
        return QueryPlan(
            steps=steps,
            intent_type=intent.intent_type,
            estimated_time_ms=sum(s.estimated_time_ms for s in steps),
            estimated_cost=0.0
        )
    
    def _plan_target_drug_lookup(self, intent: ParsedIntent) -> QueryPlan:
        """
        Plan target-drug lookup using Open Targets.
        
        Steps:
        1. Search for target in Open Targets
        2. Get drugs targeting this gene
        """
        steps = []
        entities = intent.entities
        
        target = entities.get("target", "")
        
        if not target:
            return QueryPlan(
                steps=steps,
                intent_type=intent.intent_type,
                estimated_time_ms=0,
                estimated_cost=0.0
            )
        
        # Step 1: Search for target
        search_step = PlanStep(
            step_id=self._next_step_id(),
            tool_name="opentargets_search",
            args={"query": target, "entity_types": ["target"]},
            depends_on=[],
            output_name="target_search",
            estimated_time_ms=300
        )
        steps.append(search_step)
        
        # Step 2: Get target drugs
        drugs_step = PlanStep(
            step_id=self._next_step_id(),
            tool_name="opentargets_target_drugs",
            args={"ensembl_id": "$target_search.results[0].id", "limit": 25},
            depends_on=[search_step.step_id],
            output_name="target_drugs",
            estimated_time_ms=500
        )
        steps.append(drugs_step)
        
        return QueryPlan(
            steps=steps,
            intent_type=intent.intent_type,
            estimated_time_ms=sum(s.estimated_time_ms for s in steps),
            estimated_cost=0.0
        )
    
    # =========================================================================
    # Structure Planning Methods (PDB/AlphaFold)
    # =========================================================================
    
    def _plan_structure_lookup(self, intent: ParsedIntent) -> QueryPlan:
        """
        Plan protein structure lookup from PDB.
        
        Steps:
        1. If PDB ID provided, get structure directly
        2. If target/UniProt ID provided, search PDB
        """
        steps = []
        entities = intent.entities
        
        pdb_id = entities.get("pdb_id")
        uniprot_id = entities.get("uniprot_id")
        target = entities.get("target")
        
        if pdb_id:
            # Direct PDB lookup
            steps.append(PlanStep(
                step_id=self._next_step_id(),
                tool_name="structure_pdb_detail",
                args={"pdb_id": pdb_id},
                depends_on=[],
                output_name="pdb_structure",
                estimated_time_ms=300
            ))
        elif uniprot_id:
            # Search by UniProt ID
            steps.append(PlanStep(
                step_id=self._next_step_id(),
                tool_name="structure_pdb_by_uniprot",
                args={"uniprot_id": uniprot_id, "limit": 10},
                depends_on=[],
                output_name="pdb_structures",
                estimated_time_ms=500
            ))
        elif target:
            # Search UniProt first, then PDB
            uniprot_step = PlanStep(
                step_id=self._next_step_id(),
                tool_name="uniprot_search",
                args={"query": target, "limit": 1},
                depends_on=[],
                output_name="uniprot_result",
                estimated_time_ms=300
            )
            steps.append(uniprot_step)
            
            pdb_step = PlanStep(
                step_id=self._next_step_id(),
                tool_name="structure_pdb_by_uniprot",
                args={"uniprot_id": "$uniprot_result.results[0].accession", "limit": 10},
                depends_on=[uniprot_step.step_id],
                output_name="pdb_structures",
                estimated_time_ms=500
            )
            steps.append(pdb_step)
        
        return QueryPlan(
            steps=steps,
            intent_type=intent.intent_type,
            estimated_time_ms=sum(s.estimated_time_ms for s in steps),
            estimated_cost=0.0
        )
    
    def _plan_alphafold_lookup(self, intent: ParsedIntent) -> QueryPlan:
        """
        Plan AlphaFold structure prediction lookup.
        
        Steps:
        1. If UniProt ID provided, get AlphaFold structure directly
        2. If target name provided, search UniProt first
        """
        steps = []
        entities = intent.entities
        
        uniprot_id = entities.get("uniprot_id")
        target = entities.get("target")
        
        if uniprot_id:
            # Direct AlphaFold lookup
            steps.append(PlanStep(
                step_id=self._next_step_id(),
                tool_name="structure_alphafold",
                args={"uniprot_id": uniprot_id},
                depends_on=[],
                output_name="alphafold_structure",
                estimated_time_ms=300
            ))
        elif target:
            # Search UniProt first, then AlphaFold
            uniprot_step = PlanStep(
                step_id=self._next_step_id(),
                tool_name="uniprot_search",
                args={"query": target, "limit": 1},
                depends_on=[],
                output_name="uniprot_result",
                estimated_time_ms=300
            )
            steps.append(uniprot_step)
            
            alphafold_step = PlanStep(
                step_id=self._next_step_id(),
                tool_name="structure_alphafold",
                args={"uniprot_id": "$uniprot_result.results[0].accession"},
                depends_on=[uniprot_step.step_id],
                output_name="alphafold_structure",
                estimated_time_ms=300
            )
            steps.append(alphafold_step)
        
        return QueryPlan(
            steps=steps,
            intent_type=intent.intent_type,
            estimated_time_ms=sum(s.estimated_time_ms for s in steps),
            estimated_cost=0.0
        )