"""
Multi-Agent Orchestration System for ChemAgent.

Architecture:
    Coordinator Agent (Nemotron) - Orchestrates specialist agents
    ├── CompoundAgent - Compound search, lookup, similarity
    ├── ActivityAgent - Bioactivity data, IC50, Ki, targets
    ├── PropertyAgent - Property calculations, Lipinski, descriptors
    └── TargetAgent - Target resolution, protein lookups

Each agent has:
    - Assigned role and expertise
    - Specific tools it can use
    - Communication with coordinator
"""

import json
import logging
import time
import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Callable
from enum import Enum

logger = logging.getLogger(__name__)

# Check for litellm
try:
    from litellm import completion
    LITELLM_AVAILABLE = True
except ImportError:
    LITELLM_AVAILABLE = False
    logger.warning("litellm not installed. Multi-agent features disabled.")

from chemagent.core.context_manager import (
    OrchestrationContext,
    get_context_manager,
    AgentOutput,
    SubTask,
)


# =============================================================================
# Model Configuration
# =============================================================================

class ModelConfig:
    """Model configuration for different agent roles."""
    
    # Coordinator uses Nemotron for best orchestration
    COORDINATOR_MODEL = "nvidia/llama-3.3-nemotron-super-49b-v1"
    COORDINATOR_FALLBACK = "groq/llama-3.3-70b-versatile"
    
    # Specialist agents use faster, cheaper models
    SPECIALIST_MODEL = "groq/llama-3.1-8b-instant"
    
    # For complex reasoning tasks
    REASONING_MODEL = "groq/llama-3.3-70b-versatile"
    
    @classmethod
    def get_coordinator_model(cls) -> str:
        """Get coordinator model with fallback."""
        # Try Nemotron first, fallback to Groq
        return cls.COORDINATOR_FALLBACK  # Using fallback for now until NVIDIA API configured
    
    @classmethod
    def get_specialist_model(cls) -> str:
        return cls.SPECIALIST_MODEL


# =============================================================================
# Agent Base Classes
# =============================================================================

class AgentRole(Enum):
    """Agent roles in the multi-agent system."""
    COORDINATOR = "coordinator"
    COMPOUND_SPECIALIST = "compound_specialist"
    ACTIVITY_SPECIALIST = "activity_specialist"
    PROPERTY_SPECIALIST = "property_specialist"
    TARGET_SPECIALIST = "target_specialist"


@dataclass
class AgentTask:
    """A task assigned to an agent."""
    task_id: str
    description: str
    input_data: Dict[str, Any]
    expected_output: str
    priority: int = 1
    dependencies: List[str] = field(default_factory=list)


@dataclass
class AgentResult:
    """Result from an agent execution."""
    agent_id: str
    agent_role: AgentRole
    task_id: str
    success: bool
    result: Any
    confidence: float = 1.0
    execution_time_ms: float = 0.0
    error: Optional[str] = None


class BaseAgent(ABC):
    """
    Base class for all agents in the multi-agent system.
    
    Each agent has:
    - A unique ID
    - An assigned role
    - A set of tools it can use
    - A system prompt defining its expertise
    """
    
    def __init__(
        self,
        agent_id: str,
        role: AgentRole,
        tool_registry: Any = None,
        model: str = None
    ):
        self.agent_id = agent_id
        self.role = role
        self.tool_registry = tool_registry
        self.model = model or ModelConfig.get_specialist_model()
        self.tools: Dict[str, Callable] = {}
        self._setup_tools()
    
    @abstractmethod
    def _setup_tools(self):
        """Setup tools available to this agent."""
        pass
    
    @abstractmethod
    def get_system_prompt(self) -> str:
        """Get the system prompt defining this agent's role."""
        pass
    
    @abstractmethod
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get tool definitions for this agent."""
        pass
    
    def execute(self, task: AgentTask) -> AgentResult:
        """Execute a task and return result."""
        start_time = time.time()
        
        try:
            logger.info(f"Agent {self.agent_id} ({self.role.value}): Starting task {task.task_id}")
            logger.info(f"  Task: {task.description}")
            
            result = self._execute_task(task)
            
            execution_time = (time.time() - start_time) * 1000
            logger.info(f"Agent {self.agent_id}: Completed in {execution_time:.0f}ms")
            
            return AgentResult(
                agent_id=self.agent_id,
                agent_role=self.role,
                task_id=task.task_id,
                success=True,
                result=result,
                execution_time_ms=execution_time
            )
            
        except Exception as e:
            logger.error(f"Agent {self.agent_id} error: {e}")
            return AgentResult(
                agent_id=self.agent_id,
                agent_role=self.role,
                task_id=task.task_id,
                success=False,
                result=None,
                error=str(e),
                execution_time_ms=(time.time() - start_time) * 1000
            )
    
    def _execute_task(self, task: AgentTask) -> Any:
        """Execute task with LLM reasoning and tool use."""
        if not LITELLM_AVAILABLE:
            return self._execute_tools_directly(task)
        
        # Build messages for LLM
        messages = [
            {"role": "system", "content": self.get_system_prompt()},
            {"role": "user", "content": self._format_task_prompt(task)}
        ]
        
        # Call LLM to decide what to do
        response = completion(
            model=self.model,
            messages=messages,
            temperature=0.3,
            max_tokens=2000
        )
        
        llm_response = response.choices[0].message.content
        
        # Parse tool calls from response and execute
        tool_calls = self._parse_tool_calls(llm_response)
        
        if tool_calls:
            results = {}
            for tool_name, args in tool_calls:
                if tool_name in self.tools:
                    results[tool_name] = self.tools[tool_name](**args)
                elif self.tool_registry:
                    tool = self.tool_registry.get(tool_name)
                    if tool:
                        results[tool_name] = tool(**args)
            return {"llm_reasoning": llm_response, "tool_results": results}
        
        return {"llm_reasoning": llm_response}
    
    def _execute_tools_directly(self, task: AgentTask) -> Any:
        """Execute tools directly without LLM (fallback)."""
        results = {}
        # Execute based on task input
        if "compound_name" in task.input_data:
            if "chembl_search_by_name" in self.tools:
                results["search"] = self.tools["chembl_search_by_name"](
                    query=task.input_data["compound_name"],
                    limit=5
                )
        return results
    
    def _format_task_prompt(self, task: AgentTask) -> str:
        """Format task as prompt for LLM."""
        return f"""Task: {task.description}

Input Data:
{json.dumps(task.input_data, indent=2)}

Expected Output: {task.expected_output}

Available Tools:
{json.dumps(self.get_available_tools(), indent=2)}

Instructions:
1. Analyze the task and input data
2. Decide which tools to call
3. Format tool calls as: <TOOL>tool_name(arg1=value1, arg2=value2)</TOOL>
4. Provide your reasoning and final answer

Response:"""
    
    def _parse_tool_calls(self, response: str) -> List[tuple]:
        """Parse tool calls from LLM response."""
        import re
        tool_calls = []
        
        # Pattern: <TOOL>tool_name(args)</TOOL>
        pattern = r'<TOOL>(\w+)\(([^)]*)\)</TOOL>'
        matches = re.findall(pattern, response)
        
        for tool_name, args_str in matches:
            # Parse args
            args = {}
            if args_str:
                for arg in args_str.split(','):
                    if '=' in arg:
                        key, value = arg.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"\'')
                        # Try to parse as number
                        try:
                            value = float(value) if '.' in value else int(value)
                        except ValueError:
                            pass
                        args[key] = value
            tool_calls.append((tool_name, args))
        
        return tool_calls


# =============================================================================
# Specialist Agents
# =============================================================================

class CompoundAgent(BaseAgent):
    """
    Compound Specialist Agent.
    
    Role: Finding, identifying, and searching for chemical compounds
    Expertise: ChEMBL search, compound lookup, similarity search
    """
    
    def __init__(self, tool_registry=None):
        super().__init__(
            agent_id="compound_agent",
            role=AgentRole.COMPOUND_SPECIALIST,
            tool_registry=tool_registry
        )
    
    def _setup_tools(self):
        """Setup compound-related tools."""
        if self.tool_registry:
            self.tools = {
                "chembl_search_by_name": self.tool_registry.get("chembl_search_by_name"),
                "chembl_get_compound": self.tool_registry.get("chembl_get_compound"),
                "chembl_similarity_search": self.tool_registry.get("chembl_similarity_search"),
            }
            # Remove None values
            self.tools = {k: v for k, v in self.tools.items() if v is not None}
    
    def get_system_prompt(self) -> str:
        return """You are the Compound Specialist Agent for ChemAgent.

ROLE: Finding, identifying, and searching for chemical compounds
EXPERTISE: ChEMBL database queries, compound identification, similarity search

CAPABILITIES:
- Search compounds by name (aspirin, ibuprofen, etc.)
- Look up compounds by ChEMBL ID (CHEMBL25)
- Find similar compounds using SMILES structures
- Identify compound names from structures

TOOLS AVAILABLE:
- chembl_search_by_name(query, limit): Search by compound name
- chembl_get_compound(chembl_id): Get compound details
- chembl_similarity_search(smiles, threshold, limit): Find similar compounds

FORMAT TOOL CALLS AS: <TOOL>tool_name(arg=value)</TOOL>

Be precise with compound names and IDs. Return structured data."""
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "chembl_search_by_name",
                "description": "Search compounds by name",
                "parameters": {"query": "str", "limit": "int (default 5)"}
            },
            {
                "name": "chembl_get_compound",
                "description": "Get compound details by ChEMBL ID",
                "parameters": {"chembl_id": "str"}
            },
            {
                "name": "chembl_similarity_search",
                "description": "Find similar compounds",
                "parameters": {"smiles": "str", "threshold": "float", "limit": "int"}
            }
        ]


class ActivityAgent(BaseAgent):
    """
    Activity Specialist Agent.
    
    Role: Retrieving and analyzing bioactivity data
    Expertise: IC50, Ki, EC50, target interactions, assay data
    """
    
    def __init__(self, tool_registry=None):
        super().__init__(
            agent_id="activity_agent",
            role=AgentRole.ACTIVITY_SPECIALIST,
            tool_registry=tool_registry
        )
    
    def _setup_tools(self):
        if self.tool_registry:
            self.tools = {
                "chembl_get_activities": self.tool_registry.get("chembl_get_activities"),
                "chembl_get_targets": self.tool_registry.get("chembl_get_targets"),
            }
            self.tools = {k: v for k, v in self.tools.items() if v is not None}
    
    def get_system_prompt(self) -> str:
        return """You are the Activity Specialist Agent for ChemAgent.

ROLE: Retrieving and analyzing bioactivity data
EXPERTISE: IC50, Ki, EC50 values, target interactions, assay interpretation

CAPABILITIES:
- Get bioactivity data for compounds
- Find compounds active against specific targets
- Analyze activity profiles
- Compare activity across compounds

TOOLS AVAILABLE:
- chembl_get_activities(chembl_id, limit): Get activity data for compound
- chembl_get_targets(chembl_id): Get targets for compound

FORMAT TOOL CALLS AS: <TOOL>tool_name(arg=value)</TOOL>

Focus on quantitative activity data. Report IC50/Ki in appropriate units (nM, µM)."""
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "chembl_get_activities",
                "description": "Get bioactivity data for a compound",
                "parameters": {"chembl_id": "str", "limit": "int (default 30)"}
            },
            {
                "name": "chembl_get_targets",
                "description": "Get targets for a compound",
                "parameters": {"chembl_id": "str"}
            }
        ]


class PropertyAgent(BaseAgent):
    """
    Property Specialist Agent.
    
    Role: Calculating and analyzing molecular properties
    Expertise: Lipinski rules, LogP, MW, TPSA, drug-likeness
    """
    
    def __init__(self, tool_registry=None):
        super().__init__(
            agent_id="property_agent",
            role=AgentRole.PROPERTY_SPECIALIST,
            tool_registry=tool_registry
        )
    
    def _setup_tools(self):
        if self.tool_registry:
            self.tools = {
                "rdkit_calculate_properties": self.tool_registry.get("rdkit_calculate_properties"),
                "rdkit_check_lipinski": self.tool_registry.get("rdkit_check_lipinski"),
            }
            self.tools = {k: v for k, v in self.tools.items() if v is not None}
    
    def get_system_prompt(self) -> str:
        return """You are the Property Specialist Agent for ChemAgent.

ROLE: Calculating and analyzing molecular properties
EXPERTISE: Lipinski's Rule of Five, LogP, molecular weight, TPSA, drug-likeness

CAPABILITIES:
- Calculate molecular properties from SMILES
- Check Lipinski rule compliance
- Assess drug-likeness
- Compare property profiles

TOOLS AVAILABLE:
- rdkit_calculate_properties(smiles): Calculate all properties
- rdkit_check_lipinski(smiles): Check Lipinski Rule of Five

FORMAT TOOL CALLS AS: <TOOL>tool_name(arg=value)</TOOL>

Provide quantitative property values with units. Interpret drug-likeness."""
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "rdkit_calculate_properties",
                "description": "Calculate molecular properties",
                "parameters": {"smiles": "str"}
            },
            {
                "name": "rdkit_check_lipinski",
                "description": "Check Lipinski Rule of Five",
                "parameters": {"smiles": "str"}
            }
        ]


class TargetAgent(BaseAgent):
    """
    Target Specialist Agent.
    
    Role: Resolving and analyzing drug targets
    Expertise: Protein identification, UniProt lookups, target validation
    """
    
    def __init__(self, tool_registry=None):
        super().__init__(
            agent_id="target_agent",
            role=AgentRole.TARGET_SPECIALIST,
            tool_registry=tool_registry
        )
    
    def _setup_tools(self):
        if self.tool_registry:
            self.tools = {
                "uniprot_get_protein": self.tool_registry.get("uniprot_get_protein"),
                "uniprot_search": self.tool_registry.get("uniprot_search"),
            }
            self.tools = {k: v for k, v in self.tools.items() if v is not None}
    
    def get_system_prompt(self) -> str:
        return """You are the Target Specialist Agent for ChemAgent.

ROLE: Resolving and analyzing drug targets
EXPERTISE: Protein identification, UniProt database, target validation

CAPABILITIES:
- Resolve protein names to UniProt IDs
- Get protein/target information
- Find targets by name or function
- Validate target druggability

TOOLS AVAILABLE:
- uniprot_get_protein(uniprot_id): Get protein details
- uniprot_search(query, limit): Search for proteins

FORMAT TOOL CALLS AS: <TOOL>tool_name(arg=value)</TOOL>

Provide UniProt IDs, protein names, and relevant biological context."""
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "uniprot_get_protein",
                "description": "Get protein details by UniProt ID",
                "parameters": {"uniprot_id": "str"}
            },
            {
                "name": "uniprot_search",
                "description": "Search for proteins",
                "parameters": {"query": "str", "limit": "int"}
            }
        ]


# =============================================================================
# Coordinator Agent
# =============================================================================

class CoordinatorAgent:
    """
    Coordinator Agent - Orchestrates the multi-agent system.
    
    Uses Nemotron model for:
    - Task decomposition
    - Agent routing
    - Result synthesis
    - Complex reasoning
    """
    
    def __init__(self, tool_registry=None):
        self.agent_id = "coordinator"
        self.role = AgentRole.COORDINATOR
        self.tool_registry = tool_registry
        self.model = ModelConfig.get_coordinator_model()
        
        # Initialize specialist agents
        self.specialists: Dict[AgentRole, BaseAgent] = {
            AgentRole.COMPOUND_SPECIALIST: CompoundAgent(tool_registry),
            AgentRole.ACTIVITY_SPECIALIST: ActivityAgent(tool_registry),
            AgentRole.PROPERTY_SPECIALIST: PropertyAgent(tool_registry),
            AgentRole.TARGET_SPECIALIST: TargetAgent(tool_registry),
        }
        
        # Context manager for orchestration
        self.context_manager = get_context_manager()
        
        # Stats
        self.stats = {
            "total_queries": 0,
            "tasks_delegated": 0,
            "successful_orchestrations": 0,
            "errors": 0
        }
    
    def get_system_prompt(self) -> str:
        return """You are the Coordinator Agent for ChemAgent, a pharmaceutical research assistant.

ROLE: Orchestrate specialist agents to answer complex chemistry queries
MODE: detailed thinking on

SPECIALIST AGENTS AVAILABLE:
1. COMPOUND_SPECIALIST - Search compounds, similarity, lookups
2. ACTIVITY_SPECIALIST - Bioactivity data, IC50, Ki, targets  
3. PROPERTY_SPECIALIST - Calculate properties, Lipinski, LogP
4. TARGET_SPECIALIST - Protein resolution, UniProt lookups

YOUR RESPONSIBILITIES:
1. Analyze user queries to understand intent
2. Decompose complex queries into sub-tasks
3. Assign tasks to appropriate specialists
4. Handle dependencies between tasks
5. Synthesize results into coherent response

TASK ASSIGNMENT FORMAT:
<DELEGATE agent="AGENT_ROLE" task="description" depends_on="task_ids or none">
{input_data as JSON}
</DELEGATE>

SYNTHESIS FORMAT:
<SYNTHESIZE>
Your final response combining all agent results
</SYNTHESIZE>

Be strategic about task decomposition. Minimize unnecessary agent calls."""
    
    def process(self, query: str, session_id: str = None) -> Dict[str, Any]:
        """
        Process a query through multi-agent orchestration.
        
        Flow:
        1. Analyze query with LLM
        2. Decompose into sub-tasks
        3. Route to specialist agents
        4. Collect and synthesize results
        """
        start_time = time.time()
        self.stats["total_queries"] += 1
        
        logger.info("=" * 70)
        logger.info(f"COORDINATOR: Processing query")
        logger.info(f"Query: {query}")
        logger.info("=" * 70)
        
        # Create orchestration context
        orch_context = self.context_manager.create_orchestration(query)
        
        try:
            # Step 1: Analyze and plan
            logger.info("STEP 1: Query Analysis & Planning")
            plan = self._plan_execution(query, orch_context)
            
            if not plan.get("tasks"):
                # Simple query - handle directly
                logger.info("  → Simple query, handling directly")
                answer = self._direct_answer(query)
                return {
                    "success": True,
                    "answer": answer,
                    "orchestration": "direct",
                    "execution_time_ms": (time.time() - start_time) * 1000
                }
            
            # Step 2: Execute tasks (respecting dependencies)
            logger.info("STEP 2: Task Execution")
            results = self._execute_plan(plan, orch_context)
            
            # Step 3: Synthesize results
            logger.info("STEP 3: Result Synthesis")
            answer = self._synthesize_results(query, results, orch_context)
            
            self.stats["successful_orchestrations"] += 1
            execution_time = (time.time() - start_time) * 1000
            
            logger.info(f"COORDINATOR: Completed in {execution_time:.0f}ms")
            logger.info("=" * 70)
            
            return {
                "success": True,
                "answer": answer,
                "orchestration": "multi_agent",
                "tasks_executed": len(results),
                "agents_used": list(set(r.agent_role.value for r in results.values())),
                "execution_time_ms": execution_time
            }
            
        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"Coordinator error: {e}", exc_info=True)
            return {
                "success": False,
                "answer": f"Error during orchestration: {str(e)}",
                "error": str(e),
                "execution_time_ms": (time.time() - start_time) * 1000
            }
    
    def _plan_execution(self, query: str, context: OrchestrationContext) -> Dict[str, Any]:
        """Plan task execution using LLM."""
        if not LITELLM_AVAILABLE:
            return self._plan_without_llm(query)
        
        prompt = f"""Analyze this query and create an execution plan.

Query: {query}

Available Agents:
- COMPOUND_SPECIALIST: Search compounds, similarity, lookups
- ACTIVITY_SPECIALIST: Bioactivity data, IC50, Ki, targets
- PROPERTY_SPECIALIST: Calculate properties, Lipinski, LogP
- TARGET_SPECIALIST: Protein resolution, UniProt lookups

Create a plan with tasks. For each task specify:
1. Which agent should handle it
2. What the task is
3. What input data is needed
4. Dependencies (if any)

Respond with JSON:
{{
    "analysis": "Your analysis of the query",
    "tasks": [
        {{
            "id": "task_1",
            "agent": "COMPOUND_SPECIALIST",
            "description": "task description",
            "input": {{"key": "value"}},
            "depends_on": []
        }}
    ]
}}

If this is a simple query that doesn't need specialists, return:
{{"analysis": "...", "tasks": []}}
"""
        
        try:
            response = completion(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.get_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1500
            )
            
            content = response.choices[0].message.content
            
            # Extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                plan = json.loads(json_match.group())
                logger.info(f"  → Plan created: {len(plan.get('tasks', []))} tasks")
                return plan
            
        except Exception as e:
            logger.warning(f"Planning with LLM failed: {e}")
        
        return self._plan_without_llm(query)
    
    def _plan_without_llm(self, query: str) -> Dict[str, Any]:
        """Create execution plan without LLM (pattern-based fallback)."""
        query_lower = query.lower()
        tasks = []
        
        # Detect what's needed
        needs_compound = any(w in query_lower for w in ['compound', 'drug', 'what is', 'find', 'search', 'similar'])
        needs_activity = any(w in query_lower for w in ['activity', 'ic50', 'target', 'binding', 'inhibit'])
        needs_property = any(w in query_lower for w in ['property', 'lipinski', 'logp', 'weight', 'calculate'])
        needs_target = any(w in query_lower for w in ['protein', 'uniprot', 'receptor', 'enzyme'])
        
        # Extract compound name or SMILES (simple extraction)
        import re
        compound_match = re.search(r'\b(aspirin|ibuprofen|acetaminophen|CHEMBL\d+)\b', query, re.I)
        compound = compound_match.group(1) if compound_match else None
        
        if needs_compound and compound:
            tasks.append({
                "id": "task_1",
                "agent": "COMPOUND_SPECIALIST",
                "description": f"Look up compound: {compound}",
                "input": {"compound_name": compound},
                "depends_on": []
            })
        
        if needs_activity:
            tasks.append({
                "id": f"task_{len(tasks)+1}",
                "agent": "ACTIVITY_SPECIALIST",
                "description": "Get activity data",
                "input": {"compound_name": compound} if compound else {},
                "depends_on": ["task_1"] if needs_compound else []
            })
        
        if needs_property:
            tasks.append({
                "id": f"task_{len(tasks)+1}",
                "agent": "PROPERTY_SPECIALIST",
                "description": "Calculate properties",
                "input": {"compound_name": compound} if compound else {},
                "depends_on": ["task_1"] if needs_compound else []
            })
        
        return {"analysis": "Pattern-based planning", "tasks": tasks}
    
    def _execute_plan(
        self, 
        plan: Dict[str, Any], 
        context: OrchestrationContext
    ) -> Dict[str, AgentResult]:
        """Execute the plan by delegating to specialists."""
        results: Dict[str, AgentResult] = {}
        tasks = plan.get("tasks", [])
        
        # Build dependency graph
        remaining = {t["id"]: t for t in tasks}
        completed = set()
        
        while remaining:
            # Find tasks with satisfied dependencies
            ready = [
                t for t in remaining.values()
                if all(dep in completed for dep in t.get("depends_on", []))
            ]
            
            if not ready:
                logger.error("Deadlock detected in task dependencies!")
                break
            
            # Execute ready tasks (could be parallel in future)
            for task_def in ready:
                task_id = task_def["id"]
                agent_role = AgentRole(task_def["agent"].lower())
                
                # Get specialist agent
                specialist = self.specialists.get(agent_role)
                if not specialist:
                    logger.warning(f"No specialist for role: {agent_role}")
                    continue
                
                # Build input data (inject results from dependencies)
                input_data = task_def.get("input", {})
                for dep_id in task_def.get("depends_on", []):
                    if dep_id in results and results[dep_id].success:
                        input_data[f"from_{dep_id}"] = results[dep_id].result
                
                # Create and execute task
                task = AgentTask(
                    task_id=task_id,
                    description=task_def["description"],
                    input_data=input_data,
                    expected_output="Relevant data for the query"
                )
                
                logger.info(f"  → Delegating to {agent_role.value}: {task.description}")
                self.stats["tasks_delegated"] += 1
                
                result = specialist.execute(task)
                results[task_id] = result
                completed.add(task_id)
                del remaining[task_id]
                
                # Record in context
                context.record_agent_output(
                    agent_id=specialist.agent_id,
                    agent_type=agent_role.value,
                    task=task.description,
                    result=result.result,
                    confidence=result.confidence
                )
        
        return results
    
    def _synthesize_results(
        self, 
        query: str, 
        results: Dict[str, AgentResult],
        context: OrchestrationContext
    ) -> str:
        """Synthesize all agent results into final response."""
        if not LITELLM_AVAILABLE:
            return self._synthesize_without_llm(query, results)
        
        # Format results for LLM
        results_text = ""
        for task_id, result in results.items():
            results_text += f"\n### {result.agent_role.value} (Task: {task_id})\n"
            if result.success:
                results_text += f"```json\n{json.dumps(result.result, indent=2, default=str)[:2000]}\n```\n"
            else:
                results_text += f"Error: {result.error}\n"
        
        prompt = f"""Synthesize these agent results into a helpful response.

Original Query: {query}

Agent Results:
{results_text}

Instructions:
- Create a clear, well-formatted response
- Include key data points (MW, LogP, IC50, etc.)
- Use tables where appropriate
- Identify known drugs and their uses
- Be concise but informative

Response:"""
        
        try:
            response = completion(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are synthesizing results from multiple specialist agents into a unified response. Be concise and use markdown formatting."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=2000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.warning(f"Synthesis with LLM failed: {e}")
            return self._synthesize_without_llm(query, results)
    
    def _synthesize_without_llm(self, query: str, results: Dict[str, AgentResult]) -> str:
        """Simple synthesis without LLM."""
        parts = [f"## Results for: {query}\n"]
        
        for task_id, result in results.items():
            parts.append(f"\n### {result.agent_role.value}")
            if result.success:
                parts.append(f"```\n{json.dumps(result.result, indent=2, default=str)[:500]}\n```")
            else:
                parts.append(f"Error: {result.error}")
        
        return "\n".join(parts)
    
    def _direct_answer(self, query: str) -> str:
        """Handle simple queries directly without delegation."""
        if not LITELLM_AVAILABLE:
            return "Unable to process query without LLM support."
        
        try:
            response = completion(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are ChemAgent, a pharmaceutical research assistant. Answer chemistry questions directly and concisely."},
                    {"role": "user", "content": query}
                ],
                temperature=0.3,
                max_tokens=500
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error: {str(e)}"
    
    def get_stats(self) -> Dict[str, Any]:
        """Get orchestration statistics."""
        return {
            **self.stats,
            "specialists": {
                role.value: agent.agent_id 
                for role, agent in self.specialists.items()
            }
        }


# =============================================================================
# Factory Function
# =============================================================================

def create_multi_agent_system(tool_registry=None) -> CoordinatorAgent:
    """Create and configure the multi-agent system."""
    coordinator = CoordinatorAgent(tool_registry=tool_registry)
    logger.info("Multi-agent system initialized")
    logger.info(f"  Coordinator model: {coordinator.model}")
    logger.info(f"  Specialists: {list(coordinator.specialists.keys())}")
    return coordinator
