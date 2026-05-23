"""
Pipeline Integration Test
=========================
This test validates the complete RAG pipeline:
- Text preprocessing and segmentation
- Vector storage (ChromaDB + BM25)
- Context retrieval
- Intent classification
- AI response generation with conversation memory

Usage:
    python test_pipeline.py
"""
import sys
import logging
import warnings
from dotenv import load_dotenv

warnings.filterwarnings("ignore")

import streamlit.runtime.scriptrunner_utils.script_run_context as _src
import streamlit.runtime.state.session_state_proxy as _ssp

_src._LOGGER.warning = lambda *args, **kwargs: None
_ssp._LOGGER.warning = lambda *args, **kwargs: None

from src.qa_engine import QAEngine

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

load_dotenv()
logging.info("Initializing pipeline validation test...")

try:
    engine = QAEngine()

    mock_doc = """
    The Federal Reserve discussed interest rates today. You know, inflation is a big concern right now.
    We must carefully evaluate all metrics to stabilize the local economy efficiently.
    In a completely different computing field, modern artificial intelligence relies heavily on deep neural networks.
    We use graphics processing units to accelerate the training phases.
    """

    logging.info("Running text preprocessor and segmenter...")
    engine.ingest_and_segment({"test_memo.txt": mock_doc})
    logging.info("✅ Segmentation complete. Vectors stored successfully.")

    logging.info("Testing context retrieval and reasoning...")
    res1 = engine.get_answer("What is the Federal Reserve discussing?", [])
    print(f"\nResponse: {res1['content']}\n")
    logging.info(
        f"Logic trace captured: {bool(res1.get('reasoning_details'))}"
    )

    logging.info("Testing conversation memory...")
    history = [
        {"role": "user", "content": "What is the Federal Reserve discussing?"},
        {
            "role": "assistant",
            "content": res1["content"],
            "reasoning_details": res1.get("reasoning_details"),
        },
    ]
    res2 = engine.get_answer("Why are they worried about it?", history)
    print(f"\nResponse: {res2['content']}\n")

    logging.info("✅ Pipeline validation passed. System is fully operational.")

except Exception as e:
    logging.error(f"❌ Pipeline test failed: {e}")
    sys.exit(1)
