"""
Comprehensive Pytest Audit for Ollama Migration
Tests all modified modules without requiring a running Ollama instance.
Uses mocking to simulate Ollama HTTP responses.
"""

import sys
import os
import json
import pytest
from unittest.mock import patch, MagicMock, PropertyMock

# Ensure project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ===========================================================================
# 1. CONFIG MODULE TESTS
# ===========================================================================

class TestConfig:
    """Test config.py — Ollama model constants and validation."""

    def test_ollama_base_url_has_default(self):
        from src.config import OLLAMA_BASE_URL
        assert OLLAMA_BASE_URL == "http://localhost:11434"

    def test_primary_model_is_llama(self):
        from src.config import OLLAMA_PRIMARY_MODEL
        assert OLLAMA_PRIMARY_MODEL == "llama3.1:8b"

    def test_coding_model_is_qwen(self):
        from src.config import OLLAMA_CODING_MODEL
        assert OLLAMA_CODING_MODEL == "qwen2.5:3b"

    def test_reasoning_model_is_gemma(self):
        from src.config import OLLAMA_REASONING_MODEL
        assert OLLAMA_REASONING_MODEL == "gemma3:4b"

    def test_role_assignments(self):
        from src.config import (
            DEFAULT_LLM_MODEL, RESEARCH_LLM_MODEL, MERMAID_MODEL,
            STANDARD_MODEL, INTENT_CLASSIFIER_MODEL, REASONING_MODELS,
        )
        assert DEFAULT_LLM_MODEL == "llama3.1:8b"
        assert RESEARCH_LLM_MODEL == "gemma3:4b"
        assert MERMAID_MODEL == "qwen2.5:3b"
        assert STANDARD_MODEL == "llama3.1:8b"
        assert INTENT_CLASSIFIER_MODEL == "llama3.1:8b"
        assert "gemma3:4b" in REASONING_MODELS

    def test_no_gemini_references(self):
        """Ensure no Gemini/Google references leak into config."""
        import src.config as cfg
        source = open(cfg.__file__, "r", encoding="utf-8").read()
        assert "GEMINI" not in source.upper() or "gemini" not in source
        assert "google" not in source.lower()
        assert "genai" not in source.lower()

    def test_validate_config_connection_error(self):
        """validate_config() should return errors when Ollama is unreachable."""
        from src.config import validate_config
        with patch("src.config.requests.get", side_effect=Exception("Connection refused")):
            is_valid, errors = validate_config()
            assert is_valid is False
            assert len(errors) > 0

    def test_validate_config_success(self):
        """validate_config() should pass when Ollama returns expected models."""
        from src.config import validate_config
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "models": [
                {"name": "llama3.1:8b"},
                {"name": "qwen2.5:3b"},
                {"name": "gemma3:4b"},
            ]
        }
        with patch("src.config.requests.get", return_value=mock_resp):
            is_valid, errors = validate_config()
            assert is_valid is True
            assert len(errors) == 0

    def test_validate_config_missing_model(self):
        """validate_config() should report missing models."""
        from src.config import validate_config
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "models": [
                {"name": "llama3.1:8b"},
                # Missing qwen2.5:3b and gemma3:4b
            ]
        }
        with patch("src.config.requests.get", return_value=mock_resp):
            is_valid, errors = validate_config()
            assert is_valid is False
            assert any("qwen2.5:3b" in e for e in errors)
            assert any("gemma3:4b" in e for e in errors)

    def test_app_password_preserved(self):
        from src.config import APP_PASSWORD
        # Should exist (may be empty string)
        assert isinstance(APP_PASSWORD, str)


# ===========================================================================
# 2. LLM CLIENT TESTS
# ===========================================================================

class TestLLMClient:
    """Test llm_client.py — Ollama HTTP client with model routing."""

    def setup_method(self):
        """Reset singleton before each test."""
        from src.llm_client import LLMClient
        LLMClient._instance = None

    def test_singleton_pattern(self):
        from src.llm_client import LLMClient
        a = LLMClient()
        b = LLMClient()
        assert a is b

    def test_no_google_genai_imports(self):
        """Ensure no google/genai imports remain."""
        import src.llm_client as mod
        source = open(mod.__file__, "r", encoding="utf-8").read()
        assert "google" not in source.lower()
        assert "genai" not in source.lower()

    def test_model_routing_primary(self):
        from src.llm_client import LLMClient
        client = LLMClient()
        assert client.primary_model == "llama3.1:8b"
        assert client.glm_model == "llama3.1:8b"
        assert client.standard_model == "llama3.1:8b"
        assert client.trinity_model == "llama3.1:8b"

    def test_model_routing_coding(self):
        from src.llm_client import LLMClient
        client = LLMClient()
        assert client.coding_model == "qwen2.5:3b"

    def test_model_routing_reasoning(self):
        from src.llm_client import LLMClient
        client = LLMClient()
        assert client.reasoning_model == "gemma3:4b"
        assert client.nemotron_model == "gemma3:4b"

    def test_is_available_when_ollama_running(self):
        from src.llm_client import LLMClient
        client = LLMClient()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        with patch("src.llm_client.requests.get", return_value=mock_resp):
            assert client.is_available() is True

    def test_is_available_when_ollama_down(self):
        from src.llm_client import LLMClient
        client = LLMClient()
        with patch("src.llm_client.requests.get", side_effect=Exception("refused")):
            assert client.is_available() is False

    def test_create_chat_completion_success(self):
        """Test non-streaming completion returns MockResponse."""
        from src.llm_client import LLMClient
        client = LLMClient()

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "message": {"role": "assistant", "content": "Hello from Ollama!"},
            "done": True,
        }
        mock_resp.raise_for_status = MagicMock()

        with patch("src.llm_client.requests.post", return_value=mock_resp):
            result = client.create_chat_completion(
                model="llama3.1:8b",
                messages=[{"role": "user", "content": "Hi"}],
            )
            assert result.choices[0].message.content == "Hello from Ollama!"

    def test_create_chat_completion_stream(self):
        """Test streaming completion yields tokens."""
        from src.llm_client import LLMClient
        client = LLMClient()

        # Simulate NDJSON stream
        stream_lines = [
            json.dumps({"message": {"content": "Hello"}, "done": False}).encode(),
            json.dumps({"message": {"content": " world"}, "done": False}).encode(),
            json.dumps({"message": {"content": "!"}, "done": True}).encode(),
        ]

        mock_resp = MagicMock()
        mock_resp.iter_lines.return_value = stream_lines
        mock_resp.raise_for_status = MagicMock()

        with patch("src.llm_client.requests.post", return_value=mock_resp):
            tokens = list(client.create_chat_completion_stream(
                model="llama3.1:8b",
                messages=[{"role": "user", "content": "Hi"}],
            ))
            assert tokens == ["Hello", " world", "!"]

    def test_mermaid_always_uses_qwen(self):
        """Mermaid completion must ALWAYS route to qwen2.5:3b."""
        from src.llm_client import LLMClient
        client = LLMClient()

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "message": {"content": "```mermaid\ngraph TD\nA-->B\n```"},
            "done": True,
        }
        mock_resp.raise_for_status = MagicMock()

        with patch("src.llm_client.requests.post", return_value=mock_resp) as mock_post:
            client.create_mermaid_completion(
                messages=[{"role": "user", "content": "Draw a flowchart"}],
            )
            call_payload = mock_post.call_args[1]["json"]
            assert call_payload["model"] == "qwen2.5:3b"

    def test_research_completion_uses_gemma(self):
        """Research completion must route to gemma3:4b."""
        from src.llm_client import LLMClient
        client = LLMClient()

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "message": {"content": "Deep analysis result"},
            "done": True,
        }
        mock_resp.raise_for_status = MagicMock()

        with patch("src.llm_client.requests.post", return_value=mock_resp) as mock_post:
            client.create_research_completion(
                messages=[{"role": "user", "content": "Analyze this"}],
            )
            call_payload = mock_post.call_args[1]["json"]
            assert call_payload["model"] == "gemma3:4b"

    def test_fast_completion_uses_llama(self):
        """Fast/intent completion must route to llama3.1:8b."""
        from src.llm_client import LLMClient
        client = LLMClient()

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "message": {"content": "document_qa"},
            "done": True,
        }
        mock_resp.raise_for_status = MagicMock()

        with patch("src.llm_client.requests.post", return_value=mock_resp) as mock_post:
            client.create_fast_completion(
                messages=[{"role": "user", "content": "What is AI?"}],
            )
            call_payload = mock_post.call_args[1]["json"]
            assert call_payload["model"] == "llama3.1:8b"

    def test_reasoning_completion_uses_gemma(self):
        """Reasoning completion must route to gemma3:4b."""
        from src.llm_client import LLMClient
        client = LLMClient()

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "message": {"content": "Reasoned answer"},
            "done": True,
        }
        mock_resp.raise_for_status = MagicMock()

        with patch("src.llm_client.requests.post", return_value=mock_resp) as mock_post:
            client.create_reasoning_completion(
                messages=[{"role": "user", "content": "Reason about X"}],
            )
            call_payload = mock_post.call_args[1]["json"]
            assert call_payload["model"] == "gemma3:4b"

    def test_payload_structure(self):
        """Verify Ollama payload has correct structure."""
        from src.llm_client import LLMClient
        client = LLMClient()

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"message": {"content": "ok"}, "done": True}
        mock_resp.raise_for_status = MagicMock()

        with patch("src.llm_client.requests.post", return_value=mock_resp) as mock_post:
            client.create_chat_completion(
                model="llama3.1:8b",
                messages=[{"role": "system", "content": "You are helpful"}, {"role": "user", "content": "Hi"}],
                max_tokens=500,
                temperature=0.5,
            )
            payload = mock_post.call_args[1]["json"]
            assert payload["model"] == "llama3.1:8b"
            assert payload["stream"] is False
            assert payload["options"]["num_predict"] == 500
            assert payload["options"]["temperature"] == 0.5
            assert len(payload["messages"]) == 2

    def test_mock_response_structure(self):
        """Verify MockResponse matches expected interface."""
        from src.llm_client import MockResponse
        resp = MockResponse("test content")
        assert resp.choices[0].message.content == "test content"

    def test_get_llm_client_returns_singleton(self):
        from src.llm_client import get_llm_client, LLMClient
        c1 = get_llm_client()
        c2 = get_llm_client()
        assert c1 is c2
        assert isinstance(c1, LLMClient)


# ===========================================================================
# 3. INTENT CLASSIFIER TESTS
# ===========================================================================

class TestIntentClassifier:
    """Test intent_classifier.py — no genai references, correct routing."""

    def test_no_genai_references(self):
        import src.intent_classifier as mod
        source = open(mod.__file__, "r", encoding="utf-8").read()
        assert "genai" not in source.lower()
        assert "self.client = " not in source  # No direct client assignment

    def test_rule_based_off_topic(self):
        from src.llm_client import LLMClient
        LLMClient._instance = None
        with patch("src.llm_client.requests.get", return_value=MagicMock(status_code=200)):
            from src.intent_classifier import IntentClassifier
            clf = IntentClassifier()
            result = clf._rule_based_classify("hello")
            assert result == "off_topic"

    def test_rule_based_suggestion(self):
        from src.llm_client import LLMClient
        LLMClient._instance = None
        with patch("src.llm_client.requests.get", return_value=MagicMock(status_code=200)):
            from src.intent_classifier import IntentClassifier
            clf = IntentClassifier()
            result = clf._rule_based_classify("Can you suggest improvements to the algorithm?")
            assert result == "suggestion_request"

    def test_rule_based_ieee(self):
        from src.llm_client import LLMClient
        LLMClient._instance = None
        with patch("src.llm_client.requests.get", return_value=MagicMock(status_code=200)):
            from src.intent_classifier import IntentClassifier
            clf = IntentClassifier()
            result = clf._rule_based_classify("Generate an IEEE paper about this project")
            assert result == "ieee_paper_gen"

    def test_rule_based_document_qa(self):
        from src.llm_client import LLMClient
        LLMClient._instance = None
        with patch("src.llm_client.requests.get", return_value=MagicMock(status_code=200)):
            from src.intent_classifier import IntentClassifier
            clf = IntentClassifier()
            result = clf._rule_based_classify("What does this document say about AI?")
            assert result == "document_qa"


# ===========================================================================
# 4. RESEARCH ENGINE TESTS
# ===========================================================================

class TestResearchEngine:
    """Test research_engine.py — no genai references, correct model."""

    def test_no_genai_references(self):
        import src.research_engine as mod
        source = open(mod.__file__, "r", encoding="utf-8").read()
        assert "genai" not in source.lower()
        assert "self.client = " not in source

    def test_model_is_gemma(self):
        from src.llm_client import LLMClient
        LLMClient._instance = None
        with patch("src.llm_client.requests.get", return_value=MagicMock(status_code=200)):
            from src.research_engine import ResearchEngine
            engine = ResearchEngine()
            assert engine.model == "gemma3:4b"


# ===========================================================================
# 5. QA ENGINE TESTS
# ===========================================================================

class TestQAEngine:
    """Test qa_engine.py — streaming, error messages, no genai references."""

    def test_no_genai_references(self):
        import src.qa_engine as mod
        source = open(mod.__file__, "r", encoding="utf-8").read()
        assert "genai" not in source.lower()
        assert "google" not in source.lower()

    def test_no_openrouter_references(self):
        import src.qa_engine as mod
        source = open(mod.__file__, "r", encoding="utf-8").read()
        assert "openrouter" not in source.lower()
        assert "OPENROUTER" not in source

    def test_ollama_error_messages(self):
        """Verify error messages reference Ollama, not OpenRouter."""
        import src.qa_engine as mod
        source = open(mod.__file__, "r", encoding="utf-8").read()
        assert "Ollama" in source
        assert "ollama serve" in source


# ===========================================================================
# 6. REQUIREMENTS TESTS
# ===========================================================================

class TestRequirements:
    """Test requirements.txt — google-genai removed, requests present."""

    def test_no_google_genai(self):
        req_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "requirements.txt"
        )
        content = open(req_path, "r", encoding="utf-8").read()
        assert "google-genai" not in content

    def test_requests_present(self):
        req_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "requirements.txt"
        )
        content = open(req_path, "r", encoding="utf-8").read()
        assert "requests" in content


# ===========================================================================
# 7. ENV FILE TESTS
# ===========================================================================

class TestEnvFile:
    """Test .env — no Gemini key, has Ollama URL."""

    def test_no_gemini_key(self):
        env_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            ".env"
        )
        content = open(env_path, "r", encoding="utf-8").read()
        assert "GEMINI_API_KEY" not in content

    def test_ollama_url_present(self):
        env_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            ".env"
        )
        content = open(env_path, "r", encoding="utf-8").read()
        assert "OLLAMA_BASE_URL" in content


# ===========================================================================
# 8. CROSS-MODULE INTEGRATION TESTS
# ===========================================================================

class TestCrossModuleIntegration:
    """Verify end-to-end model routing across all modules."""

    def setup_method(self):
        from src.llm_client import LLMClient
        LLMClient._instance = None

    def test_all_completion_methods_exist(self):
        """Verify all expected helper methods exist on LLMClient."""
        from src.llm_client import LLMClient
        client = LLMClient()
        methods = [
            "create_fast_completion",
            "create_standard_completion",
            "create_qa_completion",
            "create_research_completion",
            "create_mermaid_completion",
            "create_vision_completion",
            "create_reasoning_completion",
            "create_chat_completion",
            "create_chat_completion_stream",
        ]
        for method in methods:
            assert hasattr(client, method), f"Missing method: {method}"
            assert callable(getattr(client, method)), f"{method} not callable"

    def test_all_model_properties_exist(self):
        """Verify all model properties exist and return strings."""
        from src.llm_client import LLMClient
        client = LLMClient()
        props = [
            "primary_model", "coding_model", "reasoning_model",
            "glm_model", "standard_model", "vision_model",
            "trinity_model", "nemotron_model",
        ]
        for prop in props:
            val = getattr(client, prop)
            assert isinstance(val, str), f"{prop} should return str, got {type(val)}"
            assert len(val) > 0, f"{prop} should not be empty"

    def test_model_routing_matrix(self):
        """Comprehensive model routing verification."""
        from src.llm_client import LLMClient
        client = LLMClient()

        routing = {
            # Method → Expected model
            "create_fast_completion": "llama3.1:8b",
            "create_standard_completion": "llama3.1:8b",
            "create_qa_completion": "llama3.1:8b",
            "create_research_completion": "gemma3:4b",
            "create_mermaid_completion": "qwen2.5:3b",
            "create_reasoning_completion": "gemma3:4b",
        }

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"message": {"content": "ok"}, "done": True}
        mock_resp.raise_for_status = MagicMock()

        for method_name, expected_model in routing.items():
            with patch("src.llm_client.requests.post", return_value=mock_resp) as mock_post:
                method = getattr(client, method_name)
                method(messages=[{"role": "user", "content": "test"}])
                actual_model = mock_post.call_args[1]["json"]["model"]
                assert actual_model == expected_model, (
                    f"{method_name} routed to {actual_model}, expected {expected_model}"
                )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
