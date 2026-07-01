"""
Centralized configuration module for ResearchHelp-AI-anaylsis-system AI Document Q&A System.
All configurable settings should be defined here and accessed via environment variables.
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv(override=True)

# ==================== PATHS ====================

# Tesseract OCR path - configurable via environment variable
# Default to common Windows installation path
TESSERACT_PATH = os.getenv(
    "TESSERACT_PATH", r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

# ChromaDB persistence path
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "./chroma_db")

# ==================== OLLAMA LLM MODELS ====================

# Ollama server URL
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# Model 1: Llama 3.1 8B — Primary general-purpose model
OLLAMA_PRIMARY_MODEL = os.getenv("OLLAMA_PRIMARY_MODEL", "llama3.1:8b")

# Model 2: Qwen 2.5 3B — Coding & diagram generation (always used for Mermaid)
OLLAMA_CODING_MODEL = os.getenv("OLLAMA_CODING_MODEL", "qwen2.5:3b")

# Model 3: Gemma 3 4B — Advanced reasoning & deep analysis
OLLAMA_REASONING_MODEL = os.getenv("OLLAMA_REASONING_MODEL", "gemma3:4b")

# Default LLM model for general Q&A
DEFAULT_LLM_MODEL = OLLAMA_PRIMARY_MODEL

# Model for research engine (advanced reasoning)
RESEARCH_LLM_MODEL = OLLAMA_REASONING_MODEL

# Role-specific model assignments
MERMAID_MODEL = OLLAMA_CODING_MODEL
STANDARD_MODEL = OLLAMA_PRIMARY_MODEL
REASONING_MODELS = [OLLAMA_REASONING_MODEL]

# Model for intent classification (fast, lightweight)
INTENT_CLASSIFIER_MODEL = OLLAMA_PRIMARY_MODEL

# ==================== LLM PARAMETERS ====================

# Topic titler / generator parameters
TOPIC_TEXT_CHUNK_SIZE = int(os.getenv("TOPIC_TEXT_CHUNK_SIZE", "500"))

# Research engine parameters
RESEARCH_OVERVIEW_MAX_TOKENS = int(
    os.getenv("RESEARCH_OVERVIEW_MAX_TOKENS", "2000")
)
RESEARCH_OVERVIEW_TEMPERATURE = float(
    os.getenv("RESEARCH_OVERVIEW_TEMPERATURE", "0.3")
)
RESEARCH_SUGGESTIONS_MAX_TOKENS = int(
    os.getenv("RESEARCH_SUGGESTIONS_MAX_TOKENS", "1000")
)
RESEARCH_SUGGESTIONS_TEMPERATURE = float(
    os.getenv("RESEARCH_SUGGESTIONS_TEMPERATURE", "0.4")
)
RESEARCH_ADDON_MAX_TOKENS = int(os.getenv("RESEARCH_ADDON_MAX_TOKENS", "3000"))
RESEARCH_ADDON_TEMPERATURE = float(
    os.getenv("RESEARCH_ADDON_TEMPERATURE", "0.3")
)

# QA engine parameters
QA_MAX_TOKENS = int(os.getenv("QA_MAX_TOKENS", "3000"))
QA_TEMPERATURE = float(os.getenv("QA_TEMPERATURE", "0.25"))

# Intent classifier parameters
INTENT_MAX_TOKENS = int(os.getenv("INTENT_MAX_TOKENS", "10"))
INTENT_TEMPERATURE = float(os.getenv("INTENT_TEMPERATURE", "0.0"))
INTENT_TIMEOUT = float(os.getenv("INTENT_TIMEOUT", "25.0"))

# ==================== RETRIEVAL SETTINGS ====================

# Hybrid retrieval weights
SEMANTIC_SEARCH_WEIGHT = float(os.getenv("SEMANTIC_SEARCH_WEIGHT", "0.7"))
BM25_SEARCH_WEIGHT = float(os.getenv("BM25_SEARCH_WEIGHT", "0.3"))

# Number of results to retrieve
DEFAULT_TOP_K = int(os.getenv("DEFAULT_TOP_K", "8"))

# Topic segmentation threshold
TOPIC_SIMILARITY_THRESHOLD = float(
    os.getenv("TOPIC_SIMILARITY_THRESHOLD", "0.78")
)

# Topic segment overlap (number of sentences to overlap between segments)
TOPIC_SEGMENT_OVERLAP = int(os.getenv("TOPIC_SEGMENT_OVERLAP", "2"))

# Enhanced Topic Pipeline Settings
# Number of sentences per segment summary (TextRank)
TOPIC_SUMMARY_SENTENCES = int(os.getenv("TOPIC_SUMMARY_SENTENCES", "3"))

# Number of keywords to extract per topic (TF-IDF)
TOPIC_KEYWORDS_COUNT = int(os.getenv("TOPIC_KEYWORDS_COUNT", "8"))

# Minimum words per segment
TOPIC_MIN_SEGMENT_WORDS = int(os.getenv("TOPIC_MIN_SEGMENT_WORDS", "50"))

# Use enhanced pipeline (zero API dependency) vs LLM-based
USE_ENHANCED_PIPELINE = os.getenv("USE_ENHANCED_PIPELINE", "true").lower() == "true"

# Intent classifier cache size
INTENT_CACHE_MAX_SIZE = int(os.getenv("INTENT_CACHE_MAX_SIZE", "1000"))

# ==================== PERFORMANCE SETTINGS ====================

# Thread pool for concurrent operations
THREAD_POOL_MAX_WORKERS = int(os.getenv("THREAD_POOL_MAX_WORKERS", "2"))

# Retrieval and intent timeout (seconds)
RETRIEVAL_TIMEOUT = float(os.getenv("RETRIEVAL_TIMEOUT", "30"))
INTENT_TIMEOUT_SECONDS = float(os.getenv("INTENT_TIMEOUT_SECONDS", "30"))

# Chat history size to include in context
CHAT_HISTORY_CONTEXT_SIZE = int(os.getenv("CHAT_HISTORY_CONTEXT_SIZE", "6"))

# ==================== EMBEDDINGS ====================

# Sentence transformer model for embeddings
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-mpnet-base-v2")

# ==================== FILE LIMITS ====================

# File size limits (in bytes)
MAX_FILE_SIZE = int(
    os.getenv("MAX_FILE_SIZE", str(50 * 1024 * 1024))
)  # 50MB default
MAX_TEXT_LENGTH = int(
    os.getenv("MAX_TEXT_LENGTH", str(10 * 1024 * 1024))
)  # 10MB default

# ==================== API SETTINGS ====================

# Security
# If set, the Streamlit app will require this password to access the UI.
APP_PASSWORD = os.getenv("APP_PASSWORD", "")

# ==================== VALIDATION ====================


def validate_config():
    """Validate required configuration settings — checks Ollama connectivity."""
    errors = []

    try:
        resp = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        if resp.status_code != 200:
            errors.append(
                f"Ollama server at {OLLAMA_BASE_URL} returned status {resp.status_code}. "
                "Make sure Ollama is running (`ollama serve`)."
            )
        else:
            # Check that required models are available
            available_models = [m.get("name", "") for m in resp.json().get("models", [])]
            for model_name, role in [
                (OLLAMA_PRIMARY_MODEL, "Primary (Q&A)"),
                (OLLAMA_CODING_MODEL, "Coding (Mermaid)"),
                (OLLAMA_REASONING_MODEL, "Reasoning (Analysis)"),
            ]:
                # Match model name with or without tag suffix
                found = any(
                    m == model_name or m.startswith(model_name.split(":")[0] + ":")
                    for m in available_models
                )
                if not found:
                    errors.append(
                        f"Model '{model_name}' ({role}) not found in Ollama. "
                        f"Run: ollama pull {model_name}"
                    )
    except requests.ConnectionError:
        errors.append(
            f"Cannot connect to Ollama at {OLLAMA_BASE_URL}. "
            "Make sure Ollama is installed and running (`ollama serve`)."
        )
    except Exception as e:
        errors.append(f"Error checking Ollama: {str(e)}")

    if errors:
        return False, errors
    return True, []


# ==================== LOGGING ====================

# Log level configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Enable/disable detailed error logging
VERBOSE_ERRORS = os.getenv("VERBOSE_ERRORS", "true").lower() == "true"
