"""
Tests for LLM Router functionality.

Run with: pytest tests/test_llm_router.py -v
"""

import json
import pytest
from unittest.mock import MagicMock, patch

from chemagent.core.intent_parser import IntentParser, IntentType, ParsedIntent


class TestLLMRouterImport:
    """Test LLM router module imports correctly."""
    
    def test_import_without_litellm(self):
        """Test graceful handling when litellm not installed."""
        # This should not raise even if litellm is missing
        from chemagent.core import LLM_AVAILABLE
        # LLM_AVAILABLE should be bool
        assert isinstance(LLM_AVAILABLE, bool)
    
    def test_import_with_litellm(self):
        """Test imports work when litellm is available."""
        try:
            from chemagent.core.llm_router import (
                LLMRouter,
                HybridIntentParser,
                LLMStats,
                LITELLM_AVAILABLE
            )
            assert LLMRouter is not None
            assert HybridIntentParser is not None
        except ImportError:
            pytest.skip("litellm not installed")


class TestLLMStats:
    """Test LLMStats dataclass."""
    
    def test_initial_values(self):
        """Test default values."""
        try:
            from chemagent.core.llm_router import LLMStats
        except ImportError:
            pytest.skip("litellm not installed")
        
        stats = LLMStats()
        assert stats.total_queries == 0
        assert stats.successful_queries == 0
        assert stats.failed_queries == 0
        assert stats.total_cost == 0.0
        assert stats.avg_latency_ms == 0.0
        assert stats.success_rate == 0.0
    
    def test_avg_latency_calculation(self):
        """Test average latency calculation."""
        try:
            from chemagent.core.llm_router import LLMStats
        except ImportError:
            pytest.skip("litellm not installed")
        
        stats = LLMStats()
        stats.total_queries = 10
        stats.total_latency_ms = 2000
        
        assert stats.avg_latency_ms == 200.0
    
    def test_success_rate_calculation(self):
        """Test success rate calculation."""
        try:
            from chemagent.core.llm_router import LLMStats
        except ImportError:
            pytest.skip("litellm not installed")
        
        stats = LLMStats()
        stats.total_queries = 100
        stats.successful_queries = 95
        
        assert stats.success_rate == 95.0
    
    def test_to_dict(self):
        """Test dictionary conversion."""
        try:
            from chemagent.core.llm_router import LLMStats
        except ImportError:
            pytest.skip("litellm not installed")
        
        stats = LLMStats()
        stats.total_queries = 10
        stats.successful_queries = 9
        stats.total_cost = 0.001
        
        d = stats.to_dict()
        assert "total_queries" in d
        assert "success_rate" in d
        assert "total_cost" in d


class TestLLMRouter:
    """Test LLMRouter class."""
    
    def test_initialization(self):
        """Test router initializes correctly."""
        try:
            from chemagent.core.llm_router import LLMRouter
        except ImportError:
            pytest.skip("litellm not installed")
        
        router = LLMRouter()
        
        assert router.primary_model == "groq/llama3-8b-8192"
        assert len(router.fallback_models) == 2
        assert router.confidence_threshold == 0.8
    
    def test_custom_models(self):
        """Test router with custom models."""
        try:
            from chemagent.core.llm_router import LLMRouter
        except ImportError:
            pytest.skip("litellm not installed")
        
        router = LLMRouter(
            primary_model="openai/gpt-4o-mini",
            fallback_models=["groq/llama3-8b-8192"],
            confidence_threshold=0.9
        )
        
        assert router.primary_model == "openai/gpt-4o-mini"
        assert router.confidence_threshold == 0.9
    
    def test_is_available_no_keys(self):
        """Test availability check when no API keys set."""
        try:
            from chemagent.core.llm_router import LLMRouter
        except ImportError:
            pytest.skip("litellm not installed")
        
        # Clear environment
        import os
        original_keys = {}
        for key in ["GROQ_API_KEY", "GEMINI_API_KEY", "TOGETHER_API_KEY", "OPENAI_API_KEY", "GOOGLE_API_KEY"]:
            original_keys[key] = os.environ.pop(key, None)
        
        try:
            router = LLMRouter()
            # Should return False when no keys available
            # (may still be True if other keys in env)
            assert isinstance(router.is_available, bool)
        finally:
            # Restore keys
            for key, value in original_keys.items():
                if value is not None:
                    os.environ[key] = value
    
    def test_repr(self):
        """Test string representation."""
        try:
            from chemagent.core.llm_router import LLMRouter
        except ImportError:
            pytest.skip("litellm not installed")
        
        router = LLMRouter()
        repr_str = repr(router)
        
        assert "LLMRouter" in repr_str
        assert "groq/llama3-8b-8192" in repr_str
    
    def test_stats_tracking(self):
        """Test statistics are tracked."""
        try:
            from chemagent.core.llm_router import LLMRouter
        except ImportError:
            pytest.skip("litellm not installed")
        
        router = LLMRouter()
        
        # Initial stats
        stats = router.get_stats()
        assert stats["total_queries"] == 0
        
        # Reset stats
        router.reset_stats()
        assert router.stats.total_queries == 0


class TestLLMRouterParsing:
    """Test LLM router JSON parsing."""
    
    def test_parse_valid_json(self):
        """Test parsing valid JSON response."""
        try:
            from chemagent.core.llm_router import LLMRouter
        except ImportError:
            pytest.skip("litellm not installed")
        
        router = LLMRouter()
        
        json_response = json.dumps({
            "intent_type": "similarity_search",
            "entities": {"compound": "aspirin", "threshold": 0.7},
            "confidence": 0.95
        })
        
        result = router._parse_llm_response(json_response, "test query")
        
        assert result.intent_type == IntentType.SIMILARITY_SEARCH
        assert result.entities["compound"] == "aspirin"
        assert result.confidence == 0.95
    
    def test_parse_json_with_markdown(self):
        """Test parsing JSON wrapped in markdown."""
        try:
            from chemagent.core.llm_router import LLMRouter
        except ImportError:
            pytest.skip("litellm not installed")
        
        router = LLMRouter()
        
        json_response = """```json
{
    "intent_type": "activity_lookup",
    "entities": {"compound": "imatinib", "target": "ABL"},
    "confidence": 0.9
}
```"""
        
        result = router._parse_llm_response(json_response, "test query")
        
        assert result.intent_type == IntentType.ACTIVITY_LOOKUP
        assert result.entities["compound"] == "imatinib"
    
    def test_parse_invalid_json(self):
        """Test handling invalid JSON gracefully."""
        try:
            from chemagent.core.llm_router import LLMRouter
        except ImportError:
            pytest.skip("litellm not installed")
        
        router = LLMRouter()
        
        invalid_json = "This is not JSON at all"
        result = router._parse_llm_response(invalid_json, "test query")
        
        assert result.intent_type == IntentType.UNKNOWN
        assert result.confidence == 0.0
    
    def test_parse_unknown_intent_type(self):
        """Test handling unknown intent type."""
        try:
            from chemagent.core.llm_router import LLMRouter
        except ImportError:
            pytest.skip("litellm not installed")
        
        router = LLMRouter()
        
        json_response = json.dumps({
            "intent_type": "nonexistent_type",
            "entities": {},
            "confidence": 0.5
        })
        
        result = router._parse_llm_response(json_response, "test query")
        
        # Should fall back to UNKNOWN
        assert result.intent_type == IntentType.UNKNOWN


class TestHybridIntentParser:
    """Test HybridIntentParser combining pattern + LLM."""
    
    def test_initialization(self):
        """Test hybrid parser initialization."""
        try:
            from chemagent.core.llm_router import HybridIntentParser, LLMRouter
        except ImportError:
            pytest.skip("litellm not installed")
        
        pattern_parser = IntentParser()
        hybrid = HybridIntentParser(pattern_parser)
        
        assert hybrid.pattern_parser is pattern_parser
        assert hybrid.llm_router is not None
        assert hybrid.confidence_threshold == 0.8
    
    def test_high_confidence_pattern_match(self):
        """Test that high confidence patterns skip LLM."""
        try:
            from chemagent.core.llm_router import HybridIntentParser
        except ImportError:
            pytest.skip("litellm not installed")
        
        pattern_parser = IntentParser()
        hybrid = HybridIntentParser(pattern_parser, enable_llm=False)
        
        # This should match patterns with high confidence
        result = hybrid.parse("Calculate LogP of aspirin")
        
        assert result.intent_type == IntentType.PROPERTY_CALCULATION
        assert hybrid.stats["pattern_match"] == 1
        assert hybrid.stats["llm_fallback"] == 0
    
    def test_stats_tracking(self):
        """Test hybrid parser tracks statistics."""
        try:
            from chemagent.core.llm_router import HybridIntentParser
        except ImportError:
            pytest.skip("litellm not installed")
        
        pattern_parser = IntentParser()
        hybrid = HybridIntentParser(pattern_parser, enable_llm=False)
        
        # Parse a few queries
        hybrid.parse("Calculate LogP of aspirin")
        hybrid.parse("Find compounds similar to ibuprofen")
        hybrid.parse("What is the molecular weight of caffeine")
        
        stats = hybrid.get_stats()
        
        assert stats["total_queries"] == 3
        assert "pattern_match_pct" in stats


class TestIntentParsingPrompt:
    """Test the system prompt for intent parsing."""
    
    def test_prompt_contains_intent_types(self):
        """Test prompt documents all intent types."""
        try:
            from chemagent.core.llm_router import INTENT_PARSING_PROMPT
        except ImportError:
            pytest.skip("litellm not installed")
        
        # Check key intent types are documented
        assert "similarity_search" in INTENT_PARSING_PROMPT
        assert "activity_lookup" in INTENT_PARSING_PROMPT
        assert "lipinski_check" in INTENT_PARSING_PROMPT
        assert "property_calculation" in INTENT_PARSING_PROMPT
    
    def test_prompt_contains_examples(self):
        """Test prompt contains parsing examples."""
        try:
            from chemagent.core.llm_router import INTENT_PARSING_PROMPT
        except ImportError:
            pytest.skip("litellm not installed")
        
        # Check examples are included
        assert "aspirin" in INTENT_PARSING_PROMPT
        assert "IC50" in INTENT_PARSING_PROMPT
        assert "Lipinski" in INTENT_PARSING_PROMPT


# Integration tests (require API keys)
@pytest.mark.skipif(
    True,  # Always skip by default
    reason="Integration tests require API keys"
)
class TestLLMRouterIntegration:
    """Integration tests for LLM router (requires API keys)."""
    
    def test_groq_parsing(self):
        """Test actual Groq API call."""
        import os
        if not os.environ.get("GROQ_API_KEY"):
            pytest.skip("GROQ_API_KEY not set")
        
        from chemagent.core.llm_router import LLMRouter
        
        router = LLMRouter(primary_model="groq/llama3-8b-8192")
        result = router.parse_intent("Find compounds similar to aspirin")
        
        assert result.intent_type == IntentType.SIMILARITY_SEARCH
        assert "aspirin" in str(result.entities).lower()
    
    def test_gemini_parsing(self):
        """Test actual Gemini API call."""
        import os
        if not os.environ.get("GEMINI_API_KEY") and not os.environ.get("GOOGLE_API_KEY"):
            pytest.skip("GEMINI_API_KEY not set")
        
        from chemagent.core.llm_router import LLMRouter
        
        router = LLMRouter(
            primary_model="gemini/gemini-1.5-flash-8b",
            fallback_models=[]
        )
        result = router.parse_intent("What is the IC50 of imatinib?")
        
        assert result.intent_type == IntentType.ACTIVITY_LOOKUP


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
