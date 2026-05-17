"""
Shared LLM Client module for ResearchHelp-AI-anaylsis-system AI Document Q&A System.
This module provides a singleton client for Google GenAI SDK.
"""

import os
import logging
from typing import Optional, Dict, Any, List
import time
from google import genai
from google.genai import types
from google.genai.errors import APIError

import logging
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)
from dotenv import load_dotenv

# Import logging utility
from src.logging_utils import get_logger

# Import config
from src.config import (
    GEMINI_FLASH_MODEL,
    REASONING_MODELS,
)

load_dotenv(override=True)

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
    Singleton class for shared LLM client access.
    Ensures consistent API configuration across the application.
    """

    _instance: Optional["LLMClient"] = None
    _client: Optional[genai.Client] = None
    _api_key: Optional[str] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LLMClient, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Initialize the client with API configuration."""
        self._api_key = os.getenv("GEMINI_API_KEY")
        if not self._api_key:
            logger.warning("GEMINI_API_KEY not found in environment (tried os.getenv)")
            if "GEMINI_API_KEY" in os.environ:
                self._api_key = os.environ["GEMINI_API_KEY"]
                logger.info("Found GEMINI_API_KEY in os.environ directly")
            else:
                logger.error("GEMINI_API_KEY completely missing from environment variables")
                return

        self._client = genai.Client(api_key=self._api_key)
        logger.info("LLMClient initialized successfully with Gemini")

    @property
    def client(self) -> Optional[genai.Client]:
        """Get the Gemini client instance."""
        if self._client is None:
            self._initialize()
        return self._client

    @property
    def api_key(self) -> Optional[str]:
        """Get the API key."""
        if self._api_key is None:
            self._api_key = os.getenv("GEMINI_API_KEY")
        return self._api_key

    def is_available(self) -> bool:
        """Check if the client is available."""
        return self._client is not None and self._api_key is not None

    def reset(self):
        """Reset the singleton instance (useful for testing)."""
        self._instance = None
        self._client = None
        self._api_key = None

    # ==================== Model Helper Properties ====================
    
    @property
    def glm_model(self) -> str:
        return GEMINI_FLASH_MODEL
    
    @property
    def standard_model(self) -> str:
        return GEMINI_FLASH_MODEL

    @property
    def vision_model(self) -> str:
        return GEMINI_FLASH_MODEL
    
    @property
    def trinity_model(self) -> str:
        return GEMINI_FLASH_MODEL
    
    @property
    def nemotron_model(self) -> str:
        return GEMINI_FLASH_MODEL

    # ==================== Chat Completion Helpers ====================
    
    def _convert_messages(self, messages: List[Dict[str, str]]):
        """Convert OpenAI style messages to Gemini style"""
        system_instruction = None
        contents = []
        for msg in messages:
            role = msg.get("role")
            content = msg.get("content")
            
            # Handle vision content
            if isinstance(content, list):
                parts = []
                for item in content:
                    if item.get("type") == "text":
                        parts.append(types.Part.from_text(text=item.get("text", "")))
                    elif item.get("type") == "image_url":
                        # Simplistic handling, assuming it's a URL or base64
                        # GenAI SDK usually needs a File or blob for images
                        pass # Skipping true vision for this mock/conversion
                
                if role == "user":
                    contents.append(types.Content(role="user", parts=parts))
                elif role in ("assistant", "model"):
                    contents.append(types.Content(role="model", parts=parts))
                continue

            # Standard text content
            if role == "system":
                system_instruction = content
            elif role == "user":
                contents.append(types.Content(role="user", parts=[types.Part.from_text(text=content)]))
            elif role in ("assistant", "model"):
                contents.append(types.Content(role="model", parts=[types.Part.from_text(text=content)]))
                
        return system_instruction, contents

    def create_chat_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        max_tokens: int = 1000,
        temperature: float = 0.3,
        enable_reasoning: bool = False,
        **kwargs
    ) -> Any:
        """
        Create a chat completion.
        """
        sys_inst, contents = self._convert_messages(messages)
        
        config = types.GenerateContentConfig(
            system_instruction=sys_inst,
            max_output_tokens=max_tokens,
            temperature=temperature
        )
        
        @retry(
            retry=retry_if_exception_type((APIError,)),
            wait=wait_exponential(multiplier=2, min=5, max=120),
            stop=stop_after_attempt(5),
            before_sleep=before_sleep_log(logger, logging.INFO),
            reraise=True
        )
        def _execute_completion_with_retry():
            return self.client.models.generate_content(
                model=model,
                contents=contents,
                config=config
            )

        try:
            response = _execute_completion_with_retry()
            return MockResponse(response.text)

        except Exception as e:
            logger.error(f"Gemini API Error: {str(e)}")
            raise e

    def create_fast_completion(self, messages, max_tokens=50, temperature=0.0) -> Any:
        return self.create_chat_completion(self.glm_model, messages, max_tokens, temperature)

    def create_standard_completion(self, messages, max_tokens=1500, temperature=0.5, **kwargs) -> Any:
        return self.create_chat_completion(self.standard_model, messages, max_tokens, temperature)

    def create_qa_completion(self, messages, max_tokens=1000, temperature=0.25) -> Any:
        return self.create_chat_completion(self.trinity_model, messages, max_tokens, temperature)

    def create_research_completion(self, messages, max_tokens=2000, temperature=0.3) -> Any:
        return self.create_chat_completion(self.nemotron_model, messages, max_tokens, temperature)

    def create_mermaid_completion(self, messages, max_tokens=1000, temperature=0.2) -> Any:
        return self.create_chat_completion(self.glm_model, messages, max_tokens, temperature)

    def create_vision_completion(self, text, image_url, max_tokens=1000, temperature=0.3) -> Any:
        # Fallback to text only for now as vision conversion is complex
        messages = [{"role": "user", "content": text}]
        return self.create_chat_completion(self.vision_model, messages, max_tokens, temperature)

    def create_reasoning_completion(self, messages, max_tokens=2000, temperature=0.25, use_nemotron=False) -> Any:
        return self.create_chat_completion(self.nemotron_model, messages, max_tokens, temperature)

def get_llm_client() -> LLMClient:
    return LLMClient()
