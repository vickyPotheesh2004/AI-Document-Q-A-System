from dotenv import load_dotenv
from src.llm_client import get_llm_client
from src.config import (
    DEFAULT_LLM_MODEL,
    TOPIC_MAX_TOKENS,
    TOPIC_TEMPERATURE,
    TOPIC_TEXT_CHUNK_SIZE,
)
from src.logging_utils import get_logger

load_dotenv()

# Get logger - this ensures logging is configured
logger = get_logger(__name__)


class TopicGenerator:
    def __init__(self):
        self.llm_client = get_llm_client()
        self.client = self.llm_client.client
        # Use configurable model for simple labeling
        self.model = DEFAULT_LLM_MODEL

    def generate_label(self, text_chunk):
        """Generates a 3-word topic title for a text block."""
        if len(text_chunk.strip()) < 100:
            return "General Snippet"

        try:
            response = self.llm_client.create_chat_completion(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": f"Label this text with a 3-word title: {text_chunk[:TOPIC_TEXT_CHUNK_SIZE]}",
                    }
                ],
                max_tokens=TOPIC_MAX_TOKENS,  # Strict token limit for speed
                temperature=TOPIC_TEMPERATURE,  # Low randomness for consistent labels
            )
            return response.choices[0].message.content.strip().replace('"', "")
        except Exception as e:
            logger.warning(f"Topic generation failed: {e}. Using fallback.")
            return " ".join(text_chunk.split()[:4]) + "..."
