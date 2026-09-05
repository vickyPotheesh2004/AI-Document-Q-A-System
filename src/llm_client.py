"""
Shared LLM Client module for ResearchHelp-AI-anaylsis-system AI Document Q&A System.
This module provides a singleton client for local Ollama LLMs.

Model Routing:
  - llama3.1:8b   → Primary (Q&A, intent classification, general tasks)
  - llama3.1:8b   → Coding (Mermaid diagrams)
  - llama3.1:8b   → Advanced reasoning (deep analysis, IEEE papers)
"""

import os
import json
import logging
from typing import Optional, Dict, Any, List

import requests
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)
from dotenv import load_dotenv  # noqa: F401 — retained for reference; config.py handles .env loading

# Import logging utility
from src.logging_utils import get_logger

# Import config
from src.config import (
    OLLAMA_BASE_URL,
    OLLAMA_PRIMARY_MODEL,
    OLLAMA_CODING_MODEL,
    OLLAMA_REASONING_MODEL,
)

# Get logger - this ensures logging is configured
logger = get_logger(__name__)


class MockMessage:
    def __init__(self, content):
        self.content = content


class MockChoice:
    def __init__(self, message):
        self.message = message


class MockResponse:
    def __init__(self, text):
        self.choices = [MockChoice(MockMessage(text))]


class LLMClient:
    """
    Singleton class for shared LLM client access via local Ollama.
    Routes requests to the appropriate model based on task type.
    """

    _instance: Optional["LLMClient"] = None
    _base_url: Optional[str] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LLMClient, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Initialize the client with Ollama configuration."""
        self._base_url = OLLAMA_BASE_URL
        logger.info(f"LLMClient initialized with Ollama at {self._base_url}")

    @property
    def base_url(self) -> str:
        """Get the Ollama base URL."""
        return self._base_url or OLLAMA_BASE_URL

    def is_available(self) -> bool:
        """Check if Ollama is reachable."""
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return resp.status_code == 200
        except Exception:
            return False

    def reset(self):
        """Reset the singleton instance (useful for testing)."""
        LLMClient._instance = None
        self._base_url = None

    # ==================== Model Helper Properties ====================

    @property
    def primary_model(self) -> str:
        """Llama 3.1 8B — general purpose."""
        return OLLAMA_PRIMARY_MODEL

    @property
    def coding_model(self) -> str:
        """Llama 3.1 8B — coding & Mermaid diagrams."""
        return OLLAMA_CODING_MODEL

    @property
    def reasoning_model(self) -> str:
        """Llama 3.1 8B — advanced reasoning & deep analysis."""
        return OLLAMA_REASONING_MODEL

    # Backwards-compatible aliases used by other modules
    @property
    def glm_model(self) -> str:
        return self.primary_model

    @property
    def standard_model(self) -> str:
        return self.primary_model

    @property
    def vision_model(self) -> str:
        return self.primary_model

    @property
    def trinity_model(self) -> str:
        return self.primary_model

    @property
    def nemotron_model(self) -> str:
        return self.reasoning_model

    # ==================== Chat Completion — Ollama ====================

    def create_chat_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        max_tokens: int = 1000,
        temperature: float = 0.3,
        stream: bool = False,
        **kwargs,
    ) -> Any:
        """
        Create a chat completion via Ollama's /api/chat endpoint.
        Ollama natively accepts the OpenAI-style messages format.
        """
        # Merge any system message into the messages list (Ollama supports role=system)
        payload = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature,
            },
        }

        logger.info(f"Ollama request → model={model}, tokens={max_tokens}, temp={temperature}")

        @retry(
            retry=retry_if_exception_type((requests.ConnectionError, requests.Timeout)),
            wait=wait_exponential(multiplier=2, min=5, max=120),
            stop=stop_after_attempt(5),
            before_sleep=before_sleep_log(logger, logging.INFO),
            reraise=True,
        )
        def _execute_completion_with_retry():
            resp = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=300,  # Local models can be slow on first load
            )
            resp.raise_for_status()
            return resp.json()

        try:
            result = _execute_completion_with_retry()
            text = result.get("message", {}).get("content", "")
            logger.info(f"Ollama response from {model}: {len(text)} chars")
            return MockResponse(text)
        except Exception as e:
            logger.error(f"Ollama API Error ({model}): {str(e)}")
            raise e

    def create_chat_completion_stream(
        self,
        model: str,
        messages: List[Dict[str, str]],
        max_tokens: int = 1000,
        temperature: float = 0.3,
    ):
        """
        Create a streaming chat completion via Ollama.
        Yields individual text tokens as they arrive.
        """
        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature,
            },
        }

        logger.info(f"Ollama stream request → model={model}, tokens={max_tokens}")

        @retry(
            retry=retry_if_exception_type((requests.ConnectionError, requests.Timeout)),
            wait=wait_exponential(multiplier=2, min=2, max=30),
            stop=stop_after_attempt(3),
            before_sleep=before_sleep_log(logger, logging.INFO),
            reraise=True,
        )
        def _start_stream():
            resp = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=300,
                stream=True,
            )
            resp.raise_for_status()
            return resp

        response = _start_stream()

        for line in response.iter_lines():
            if line:
                try:
                    chunk = json.loads(line)
                    token = chunk.get("message", {}).get("content", "")
                    if token:
                        yield token
                    # Check if stream is done
                    if chunk.get("done", False):
                        break
                except json.JSONDecodeError:
                    continue

    # ==================== Task-Specific Completion Helpers ====================

    def create_fast_completion(self, messages, max_tokens=50, temperature=0.0) -> Any:
        """Fast classification tasks — llama3.1:8b."""
        return self.create_chat_completion(self.primary_model, messages, max_tokens, temperature)

    def create_standard_completion(self, messages, max_tokens=1500, temperature=0.5, **kwargs) -> Any:
        """Standard tasks — llama3.1:8b."""
        return self.create_chat_completion(self.primary_model, messages, max_tokens, temperature)

    def create_qa_completion(self, messages, max_tokens=1000, temperature=0.25) -> Any:
        """Q&A tasks — llama3.1:8b."""
        return self.create_chat_completion(self.primary_model, messages, max_tokens, temperature)

    def create_research_completion(self, messages, max_tokens=2000, temperature=0.3) -> Any:
        """Research & deep analysis — gemma3:4b."""
        return self.create_chat_completion(self.reasoning_model, messages, max_tokens, temperature)

    def create_mermaid_completion(self, messages, max_tokens=1000, temperature=0.2) -> Any:
        """Mermaid diagram generation — ALWAYS qwen2.5:3b."""
        return self.create_chat_completion(self.coding_model, messages, max_tokens, temperature)

    def create_vision_completion(self, text, image_url, max_tokens=1000, temperature=0.3) -> Any:
        """Vision fallback — text-only via llama3.1:8b."""
        messages = [{"role": "user", "content": text}]
        return self.create_chat_completion(self.primary_model, messages, max_tokens, temperature)

    def create_reasoning_completion(self, messages, max_tokens=2000, temperature=0.25, **kwargs) -> Any:
        """Advanced reasoning — gemma3:4b."""
        return self.create_chat_completion(self.reasoning_model, messages, max_tokens, temperature)


def get_llm_client() -> LLMClient:
    return LLMClient()
