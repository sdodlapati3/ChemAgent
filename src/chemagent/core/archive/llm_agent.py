"""
LLM-First Agent for ChemAgent.

Uses LLM as the primary decision maker with tool calling capabilities.
The LLM decides whether to:
1. Answer directly from its knowledge
2. Call specific tools to fetch data
3. Ask for clarification

Architecture:
    Query → LLM Analysis → Decision:
        ├── Direct Answer (LLM knows enough)
        ├── Tool Calls → Results → LLM Synthesis
        └── Clarification Request

This replaces the pattern-based intent parser with intelligent routing.
"""

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)

# Check for litellm
try:
    import litellm
    from litellm import completion
    LITELLM_AVAILABLE = True
except ImportError:
    LITELLM_AVAILABLE = False
    logger.warning("litellm not installed. LLM agent disabled.")


class AgentAction(Enum):
    """Actions the agent can take."""
    DIRECT_ANSWER = "direct_answer"
    USE_TOOLS = "use_tools"
    CLARIFY = "clarify"
    ERROR = "error"


@dataclass
class ToolCall:
    """A tool call requested by the LLM."""
    tool_name: str
    arguments: Dict[str, Any]
    reasoning: str = ""


@dataclass 
class AgentDecision:
    """Decision made by the LLM agent."""
    action: AgentAction
    answer: Optional[str] = None
    tool_calls: List[ToolCall] = field(default_factory=list)
    clarification_question: Optional[str] = None
    confidence: float = 0.0
    reasoning: str = ""


@dataclass
class AgentResponse:
    """Final response from the agent."""
    success: bool
    answer: str
    tool_results: Dict[str, Any] = field(default_factory=dict)
    execution_time_ms: float = 0.0
    tools_used: List[str] = field(default_factory=list)
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)  # Tool calls made
    error: Optional[str] = None  # Error message if failed
    

# =============================================================================
# Tool Descriptions for LLM
# =============================================================================

TOOL_DESCRIPTIONS = """
## Available Tools

You have access to the following chemistry/pharmaceutical research tools:

### Compound Information
- **chembl_search_by_name**: Search for compounds by name (aspirin, ibuprofen, etc.)
  - Args: query (str), limit (int, default=5)
  - Use for: "What is aspirin?", "Find information about metformin"

- **chembl_get_compound**: Get detailed compound info by ChEMBL ID
  - Args: chembl_id (str, e.g., "CHEMBL25")
  - Use for: "Get CHEMBL25 details"

- **chembl_get_activities**: Get bioactivity data for a compound
  - Args: chembl_id (str), target (str, optional), limit (int, default=100)
  - Use for: "What are aspirin's targets?", "Show IC50 data for CHEMBL25"

### Similarity & Structure Search
- **chembl_similarity_search**: Find structurally similar compounds
  - Args: smiles (str), threshold (float, 0.7-1.0), limit (int)
  - Use for: "Find compounds similar to aspirin", "Analogs of ibuprofen"

- **chembl_substructure_search**: Find compounds containing a substructure
  - Args: smiles (str), limit (int)
  - Use for: "Find compounds with benzene ring"

### Property Calculations
- **rdkit_calc_properties**: Calculate molecular properties from SMILES
  - Args: smiles (str)
  - Returns: molecular_weight, logp, tpsa, hbd, hba, rotatable_bonds, etc.
  - Use for: "Calculate LogP of CC(=O)Oc1ccccc1C(=O)O"

- **rdkit_calc_lipinski**: Check Lipinski's Rule of Five
  - Args: smiles (str)
  - Use for: "Is this molecule drug-like?"

### Target/Protein Information
- **uniprot_search**: Search for proteins/targets
  - Args: query (str), limit (int)
  - Use for: "What is COX-2?", "Find EGFR protein info"

- **uniprot_get_protein**: Get protein details by UniProt ID
  - Args: uniprot_id (str, e.g., "P35354")
  
### Structure Conversion
- **rdkit_convert_format**: Convert between chemical formats
  - Args: input_string (str), input_format (str), output_format (str)
  - Formats: smiles, inchi, mol
"""

# =============================================================================
# System Prompts
# =============================================================================

ANALYSIS_PROMPT = """You are ChemAgent, an intelligent pharmaceutical research assistant.

Your role is to help researchers with chemistry and drug discovery questions.

{tool_descriptions}

## Decision Process

For each user query, decide:

1. **DIRECT_ANSWER**: If you can answer comprehensively from your knowledge (general chemistry concepts, drug mechanisms, historical info, etc.)

2. **USE_TOOLS**: If you need specific data:
   - Compound structures, properties, SMILES
   - Bioactivity data (IC50, Ki, EC50)
   - Similar compounds
   - Protein/target information
   
3. **CLARIFY**: If the query is too vague to be helpful

## Response Format

Return ONLY valid JSON:

```json
{{
  "action": "direct_answer" | "use_tools" | "clarify",
  "reasoning": "Brief explanation of your decision",
  "answer": "Your answer if direct_answer (null otherwise)",
  "clarification": "Your question if clarify (null otherwise)", 
  "tool_calls": [
    {{
      "tool": "tool_name",
      "args": {{"arg1": "value1"}},
      "purpose": "Why calling this tool"
    }}
  ]
}}
```

## Examples

Query: "What is aspirin?"
Response: {{
  "action": "use_tools",
  "reasoning": "User wants comprehensive info about aspirin - need structure, properties, and biological activity",
  "tool_calls": [
    {{"tool": "chembl_search_by_name", "args": {{"query": "aspirin", "limit": 1}}, "purpose": "Get aspirin structure and properties"}},
    {{"tool": "chembl_get_activities", "args": {{"chembl_id": "CHEMBL25", "limit": 10}}, "purpose": "Get aspirin's biological targets"}}
  ]
}}

Query: "How does aspirin work?"
Response: {{
  "action": "direct_answer",
  "reasoning": "This is asking about mechanism - I know aspirin inhibits COX enzymes",
  "answer": "Aspirin (acetylsalicylic acid) works by irreversibly inhibiting cyclooxygenase enzymes (COX-1 and COX-2). This blocks the production of prostaglandins and thromboxanes, leading to its anti-inflammatory, analgesic, antipyretic, and antiplatelet effects. At low doses, it preferentially inhibits COX-1 in platelets, preventing blood clot formation."
}}

Query: "Find me something good"
Response: {{
  "action": "clarify",
  "reasoning": "Query is too vague - need to know what type of compound or research goal",
  "clarification": "I'd be happy to help! Could you clarify what you're looking for? For example:\\n- A specific type of compound (kinase inhibitors, antibiotics)?\\n- Compounds with certain properties (drug-like, high potency)?\\n- Information about a particular drug or target?"
}}

Now analyze this query:
"""

SYNTHESIS_PROMPT = """You are ChemAgent, synthesizing tool results into a helpful response.

## Original Query
{query}

## Tool Results
{tool_results}

## Instructions

Create a CONCISE, well-formatted response that directly answers the user's question.

### Formatting Rules:
1. **Identify known compounds**: If the SMILES is a well-known drug (aspirin, ibuprofen, etc.), NAME IT prominently
2. **Use tables for properties** - not verbose bullet points:
   | Property | Value |
   |----------|-------|
   | MW | 180.16 g/mol |
   
3. **Be concise** - No repetitive "Insights and Notes" or "Conclusion" sections
4. **Include Lipinski assessment** for drug queries:
   - ✅ Passes Rule of 5 (drug-like) OR ❌ Fails Rule of 5
   
5. **For known drugs**, mention:
   - What it's used for (1 sentence)
   - Primary mechanism (1 sentence)

### Response Structure:
1. **Header**: Compound name (if known) or "Property Analysis"
2. **Properties Table**: Key molecular properties
3. **Drug-likeness**: Pass/fail with brief explanation
4. **Known uses** (if applicable): 1-2 sentences max

Keep total response under 300 words. Be direct and useful, not verbose.
"""


class LLMAgent:
    """
    LLM-first agent with tool calling capabilities.
    
    The agent uses an LLM to:
    1. Understand the user's intent
    2. Decide whether to answer directly or use tools
    3. Select appropriate tools and arguments
    4. Synthesize final response from tool results
    
    Example:
        >>> agent = LLMAgent(tool_registry)
        >>> response = agent.process("What is aspirin?")
        >>> print(response.answer)
    """
    
    # Default models
    DEFAULT_MODEL = "groq/llama-3.1-8b-instant"
    FALLBACK_MODELS = [
        "gemini/gemini-2.0-flash",
        "openrouter/google/gemini-2.0-flash-exp:free"
    ]
    
    def __init__(
        self,
        tool_registry: Optional[Any] = None,
        model: str = None,
        fallback_models: List[str] = None,
        temperature: float = 0.1,
        max_tool_calls: int = 5,
        enable_direct_answers: bool = True
    ):
        """
        Initialize the LLM agent.
        
        Args:
            tool_registry: Registry of available tools
            model: Primary LLM model to use
            fallback_models: Fallback models if primary fails
            temperature: LLM temperature (lower = more deterministic)
            max_tool_calls: Maximum tool calls per query
            enable_direct_answers: Allow LLM to answer without tools
        """
        self.tool_registry = tool_registry
        self.model = model or self.DEFAULT_MODEL
        self.fallback_models = fallback_models or self.FALLBACK_MODELS
        self.temperature = temperature
        self.max_tool_calls = max_tool_calls
        self.enable_direct_answers = enable_direct_answers
        
        # Statistics
        self.stats = {
            "total_queries": 0,
            "direct_answers": 0,
            "tool_calls": 0,
            "clarifications": 0,
            "errors": 0,
            "total_latency_ms": 0.0
        }
        
        # Check availability
        self.is_available = LITELLM_AVAILABLE
        if not self.is_available:
            logger.warning("LLM Agent not available - litellm not installed")
    
    def process(self, query: str) -> AgentResponse:
        """
        Process a user query.
        
        Args:
            query: Natural language query
            
        Returns:
            AgentResponse with answer and metadata
        """
        start_time = time.time()
        self.stats["total_queries"] += 1
        
        if not self.is_available:
            return AgentResponse(
                success=False,
                answer="LLM agent not available. Please install litellm.",
                execution_time_ms=0,
                error="LLM agent not available"
            )
        
        try:
            # Step 1: Analyze query and decide action
            decision = self._analyze_query(query)
            
            # Step 2: Execute decision
            if decision.action == AgentAction.DIRECT_ANSWER:
                self.stats["direct_answers"] += 1
                answer = decision.answer or "I don't have enough information to answer."
                
            elif decision.action == AgentAction.CLARIFY:
                self.stats["clarifications"] += 1
                answer = decision.clarification_question or "Could you please provide more details?"
                
            elif decision.action == AgentAction.USE_TOOLS:
                self.stats["tool_calls"] += 1
                # Execute tools and synthesize response
                tool_results = self._execute_tools(decision.tool_calls)
                answer = self._synthesize_response(query, tool_results)
                
                execution_time = (time.time() - start_time) * 1000
                self.stats["total_latency_ms"] += execution_time
                
                # Build tool_calls list for response
                tool_calls_data = [
                    {"tool": tc.tool_name, "args": tc.arguments, "purpose": tc.reasoning}
                    for tc in decision.tool_calls
                ]
                
                return AgentResponse(
                    success=True,
                    answer=answer,
                    tool_results=tool_results,
                    execution_time_ms=execution_time,
                    tools_used=[tc.tool_name for tc in decision.tool_calls],
                    tool_calls=tool_calls_data
                )
            else:
                self.stats["errors"] += 1
                answer = "I encountered an error processing your request."
            
            execution_time = (time.time() - start_time) * 1000
            self.stats["total_latency_ms"] += execution_time
            
            return AgentResponse(
                success=True,
                answer=answer,
                execution_time_ms=execution_time
            )
            
        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"Agent error: {e}")
            execution_time = (time.time() - start_time) * 1000
            return AgentResponse(
                success=False,
                answer=f"Error: {str(e)}",
                execution_time_ms=execution_time,
                error=str(e)
            )
    
    def _analyze_query(self, query: str) -> AgentDecision:
        """
        Use LLM to analyze query and decide action.
        """
        prompt = ANALYSIS_PROMPT.format(tool_descriptions=TOOL_DESCRIPTIONS)
        
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": query}
        ]
        
        response = self._call_llm(messages)
        
        if not response:
            return AgentDecision(action=AgentAction.ERROR)
        
        try:
            # Parse JSON response
            # Handle markdown code blocks
            content = response.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            content = content.strip()
            
            data = json.loads(content)
            
            action_str = data.get("action", "error")
            action = AgentAction(action_str) if action_str in [a.value for a in AgentAction] else AgentAction.ERROR
            
            tool_calls = []
            for tc in data.get("tool_calls", []):
                tool_calls.append(ToolCall(
                    tool_name=tc.get("tool", ""),
                    arguments=tc.get("args", {}),
                    reasoning=tc.get("purpose", "")
                ))
            
            return AgentDecision(
                action=action,
                answer=data.get("answer"),
                tool_calls=tool_calls,
                clarification_question=data.get("clarification"),
                reasoning=data.get("reasoning", "")
            )
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response: {e}")
            logger.debug(f"Raw response: {response}")
            return AgentDecision(action=AgentAction.ERROR)
    
    def _execute_tools(self, tool_calls: List[ToolCall]) -> Dict[str, Any]:
        """
        Execute the requested tools.
        """
        results = {}
        
        for tc in tool_calls[:self.max_tool_calls]:
            tool_name = tc.tool_name
            args = tc.arguments
            
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
                    else:
                        results[tool_name] = {
                            "success": False,
                            "error": f"Tool not found: {tool_name}"
                        }
                else:
                    results[tool_name] = {
                        "success": False,
                        "error": "No tool registry available"
                    }
            except Exception as e:
                logger.error(f"Tool {tool_name} failed: {e}")
                results[tool_name] = {
                    "success": False,
                    "error": str(e)
                }
        
        return results
    
    def _synthesize_response(self, query: str, tool_results: Dict[str, Any]) -> str:
        """
        Use LLM to synthesize final response from tool results.
        """
        # Format tool results for the prompt
        results_text = json.dumps(tool_results, indent=2, default=str)
        
        prompt = SYNTHESIS_PROMPT.format(
            query=query,
            tool_results=results_text
        )
        
        messages = [
            {"role": "user", "content": prompt}
        ]
        
        response = self._call_llm(messages, temperature=0.3)
        
        if not response:
            # Fallback to basic formatting
            return self._basic_format(tool_results)
        
        return response
    
    def _basic_format(self, tool_results: Dict[str, Any]) -> str:
        """Basic formatting fallback if LLM synthesis fails."""
        lines = ["## Results\n"]
        
        for tool_name, result in tool_results.items():
            if result.get("success"):
                data = result.get("data", {})
                lines.append(f"### {tool_name}\n")
                lines.append(f"```json\n{json.dumps(data, indent=2, default=str)[:1000]}\n```\n")
            else:
                lines.append(f"### {tool_name} (failed)\n")
                lines.append(f"Error: {result.get('error')}\n")
        
        return "\n".join(lines)
    
    def _call_llm(
        self, 
        messages: List[Dict[str, str]], 
        temperature: float = None
    ) -> Optional[str]:
        """
        Call LLM with automatic fallback.
        """
        temp = temperature if temperature is not None else self.temperature
        
        models_to_try = [self.model] + self.fallback_models
        
        for model in models_to_try:
            try:
                response = completion(
                    model=model,
                    messages=messages,
                    temperature=temp,
                    max_tokens=2000
                )
                
                content = response.choices[0].message.content
                if content:
                    return content.strip()
                    
            except Exception as e:
                logger.warning(f"Model {model} failed: {e}")
                continue
        
        logger.error("All LLM models failed")
        return None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get agent statistics."""
        total = self.stats["total_queries"]
        return {
            **self.stats,
            "avg_latency_ms": self.stats["total_latency_ms"] / max(total, 1),
            "direct_answer_rate": self.stats["direct_answers"] / max(total, 1) * 100,
            "tool_call_rate": self.stats["tool_calls"] / max(total, 1) * 100
        }


# =============================================================================
# Convenience function
# =============================================================================

def create_agent(tool_registry: Optional[Any] = None) -> LLMAgent:
    """
    Create an LLM agent with default settings.
    
    Args:
        tool_registry: Optional tool registry
        
    Returns:
        Configured LLMAgent instance
    """
    return LLMAgent(tool_registry=tool_registry)
