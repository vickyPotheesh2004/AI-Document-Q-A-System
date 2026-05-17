"""
Centralized configuration module for ResearchHelp-AI-anaylsis-system AI Document Q&A System.
All configurable settings should be defined here and accessed via environment variables.
"""

import os
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

# ==================== LLM MODELS ====================

# Free model identifiers for Gemini
# Model 1: Gemini 3 Flash Preview - Fast general chat (best for simple/fast tasks)
GEMINI_FLASH_MODEL = "gemini-3-flash-preview"

# Default LLM model for general Q&A

DEFAULT_LLM_MODEL = os.getenv(
    "LLM_MODEL", GEMINI_FLASH_MODEL  # Use Gemini Flash for Q&A
)

# Model for research engine
RESEARCH_LLM_MODEL = os.getenv(
    "RESEARCH_LLM_MODEL", GEMINI_FLASH_MODEL
)

# Role-specific model assignments
MERMAID_MODEL = GEMINI_FLASH_MODEL
STANDARD_MODEL = GEMINI_FLASH_MODEL
REASONING_MODELS = [GEMINI_FLASH_MODEL]

# Model for intent classification
INTENT_CLASSIFIER_MODEL = GEMINI_FLASH_MODEL

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

# Gemini API configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# ==================== VALIDATION ====================


def validate_config():
    """Validate required configuration settings."""
    errors = []

    if not GEMINI_API_KEY:
        errors.append("GEMINI_API_KEY is not set in environment variables")
    elif (
        "placeholder" in GEMINI_API_KEY.lower()
        or "your_" in GEMINI_API_KEY.lower()
    ):
        errors.append(
            "GEMINI_API_KEY appears to be a placeholder - please set a valid API key"
        )

    if errors:
        return False, errors
    return True, []


# ==================== LOGGING ====================

# Log level configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Enable/disable detailed error logging
VERBOSE_ERRORS = os.getenv("VERBOSE_ERRORS", "true").lower() == "true"
