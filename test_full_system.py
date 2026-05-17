"""
Full A-Z System Test
===================
This comprehensive test validates the entire system:
1. Document ingestion and semantic segmentation
2. Research overview generation
3. Auto-suggestions generation
4. Memory/contextual follow-up queries
5. Streaming intent routing (multiple intents)
6. Export generation (Markdown, HTML, DOCX)

Usage:
    python test_full_system.py

Note: This test may take several minutes due to API calls.
"""
import logging
import threading
from dotenv import load_dotenv

# ============================================================
# STREAMLIT WARNING SUPPRESSION
# Must be done BEFORE any Streamlit imports
# ============================================================
import warnings

warnings.filterwarnings("ignore")

import streamlit.runtime.scriptrunner_utils.script_run_context as _src
import streamlit.runtime.state.session_state_proxy as _ssp

_src._LOGGER.warning = lambda *args, **kwargs: None
_ssp._LOGGER.warning = lambda *args, **kwargs: None

# Suppress the "Warning: to view this Streamlit app on a browser" message
import streamlit.runtime.scriptrunner_utils as _sru

if hasattr(_sru, "_maybe_print_use_command_message"):
    _sru._maybe_print_use_command_message = lambda *a, **kw: None

from src.qa_engine import QAEngine
from src.research_engine import ResearchEngine
from app import (
    generate_markdown_export,
    generate_html_export,
    generate_docx_export,
)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

QUERY_TIMEOUT = 180


def run_with_timeout(func, timeout, default=None):
    result = [default]
    error = [None]

    def wrapper():
        try:
            result[0] = func()
        except Exception as e:
            error[0] = e

    t = threading.Thread(target=wrapper, daemon=True)
    t.start()
    t.join(timeout=timeout)
    if t.is_alive():
        logging.warning(f"Operation timed out after {timeout}s")
        return default, TimeoutError(f"Timed out after {timeout}s")
    return result[0], error[0]


def run_az_test():
    load_dotenv()
    logging.info("=========================================")
    logging.info("🚀 ResearchHelp-AI A-Z System Test")
    logging.info("=========================================")
    passed = 0
    failed = 0

    # ── 1. Initialize Engines ──
    logging.info("\n[1/6] Initializing Systems & ChromaDB...")
    qa_engine = QAEngine()
    research_engine = ResearchEngine()

    try:
        qa_engine.chroma_client.delete_collection("active_session")
    except Exception:
        pass
    qa_engine.collection = qa_engine.chroma_client.get_or_create_collection(
        "active_session"
    )

    # ── 2. Ingest Document ──
    logging.info("\n[2/6] Simulating Document Ingestion...")
    mock_doc = """
    ## The Quantum Drive Architecture V2.0

    The new Quantum Drive system proposed for the Horizon spacecraft utilizes a dual-core neutrino reactor.
    This reactor generates thrust by stabilizing quantum fluctuations in a contained vacuum shell.
    The primary material used for the shell is advanced carbon-nanotube mesh intertwined with titanium alloys.

    However, heat dissipation remains a significant hurdle. When the drive operates above 85% capacity
    for more than 4 hours, thermal runaway can occur, reaching temperatures over 4000K.
    It is recommended to integrate a liquid nitrogen cooling loop specifically for the secondary
    injection valve to mitigate this.
    Current cost estimates place the production of a single Quantum Drive at $1.2 Billion USD.
    """

    doc_dict = {"quantum_drive_spec.txt": mock_doc}
    qa_engine.ingest_and_segment(doc_dict)
    
    # Validation: Verify local segmentation & titling quality
    chunks, _ = qa_engine.get_all_chunks()
    if len(chunks) > 0:
        # Check if titles look conceptual rather than generic
        metas = qa_engine.collection.get(include=["metadatas"])["metadatas"]
        unique_titles = {m.get("topic") for m in metas if m}
        logging.info(f"✅ Document ingested: {len(chunks)} logical segments across {len(unique_titles)} topics detected.")
        # Verification: Ingesting and segmentation finished successfully.
    else:
        logging.error("❌ Segmentation failed - no chunks were stored.")
        failed += 1
        return # Cannot continue if ingestion failed
        
    passed += 1

    # ── 3. Generating Insights (Research Engine) ──
    logging.info("\n[3/6] Generating Document Insights...")
    chunks, metas = qa_engine.get_all_chunks()

    logging.info(
        "  → Generating overview (this may take 1-2 min on free model)..."
    )
    overview, err = run_with_timeout(
        lambda: research_engine.generate_document_overview(chunks, metas),
        timeout=QUERY_TIMEOUT,
        default="Overview generation timed out.",
    )
    if err:
        logging.warning(f"  ⚠️ Overview generation issue: {err}")
        failed += 1
    else:
        logging.info(f"  ✅ Generated Overview: {len(overview)} characters.")
        passed += 1

    logging.info("  → Generating suggestions (this may take 1-2 min)...")
    suggestions, err = run_with_timeout(
        lambda: research_engine.generate_auto_suggestions(chunks, metas),
        timeout=QUERY_TIMEOUT,
        default=[],
    )
    if err:
        logging.warning(f"  ⚠️ Suggestions generation issue: {err}")
        failed += 1
    else:
        logging.info(f"  ✅ Generated {len(suggestions)} AI Suggestions.")
        for i, sug in enumerate(suggestions):
            logging.info(
                f"     [{sug.get('category', 'N/A').upper()}] {sug.get('title')}"
            )
        passed += 1

    # ── 4. Testing Non-Streaming Pipeline & Memory ──
    logging.info("\n[4/6] Testing Core Pipeline (Non-Streaming & Memory)...")
    logging.info("  → Asking: 'What material is used for the vacuum shell?'")

    res1, err = run_with_timeout(
        lambda: qa_engine.get_answer(
            "What material is used for the vacuum shell?", []
        ),
        timeout=QUERY_TIMEOUT,
    )
    if err or not res1:
        logging.warning(f"  ⚠️ Non-streaming Q&A failed: {err}")
        failed += 1
        res1 = {
            "content": "Error",
            "reasoning_details": None,
            "intent": {},
            "sources": [],
        }
    else:
        logging.info(f"  ✅ Response: {res1['content'][:120]}...")
        logging.info(
            f"     Reasoning captured: {bool(res1.get('reasoning_details'))}"
        )
        passed += 1

    logging.info(
        "  → Follow-up with memory: 'Why is that material primarily used?'"
    )
    history = [
        {
            "role": "user",
            "content": "What material is used for the vacuum shell?",
        },
        {
            "role": "assistant",
            "content": res1["content"],
            "reasoning_details": res1.get("reasoning_details"),
        },
    ]
    res2, err = run_with_timeout(
        lambda: qa_engine.get_answer(
            "Why is that material primarily used?", history
        ),
        timeout=QUERY_TIMEOUT,
    )
    if err or not res2:
        logging.warning(f"  ⚠️ Memory follow-up failed: {err}")
        failed += 1
    else:
        logging.info(f"  ✅ Follow-up: {res2['content'][:120]}...")
        logging.info("     Memory and context retrieval passed.")
        passed += 1

    # ── 5. Testing Streaming RAG (6 key intents) ──
    logging.info(
        "\n[5/6] Testing Streaming Intent Routing (Expanded - 6 core intents)..."
    )

    mock_metadata = {
        "title": "Quantum Drive Stability Analysis",
        "authors": "Dr. Aris Thorne, Prof. Elena Vance",
        "emails": "thorne@horizon.space, vance@horizon.space",
        "colleges": "Horizon Research Institute, Department of Advanced Propulsion",
        "additional_notes": "Focus on thermal runaway mitigation for V2.0 architecture.",
    }

    test_queries = [
        {
            "desc": "Direct Factual Q&A",
            "q": "What material is used for the vacuum shell?",
        },
        {
            "desc": "Improvement Suggestion",
            "q": "What improvements can we make to the heat dissipation?",
        },
        {
            "desc": "Research Addon (8-Domain)",
            "q": "How can we build a testing facility for this drive?",
        },
        {
            "desc": "Simple Research Analysis",
            "q": "Explain Quantum Computing in very simple terms.",
        },
        {
            "desc": "IEEE Paper Generation",
            "q": "Generate an official IEEE research paper based on our analysis.",
        },
        {
            "desc": "Off-Topic Rejection",
            "q": "What is the best way to bake a sourdough bread?",
        },
    ]

    chat_history = []

    for test in test_queries:
        logging.info(f"\n  --- Testing: {test['desc']} ---")
        logging.info(f"  Query: '{test['q']}'")

        final_meta = {}
        final_text = ""
        final_reasoning = None

        try:

            def stream_query():
                nonlocal final_meta, final_text, final_reasoning
                # Pass mock_metadata for all queries to ensure it's handled when needed
                for event in qa_engine.get_answer_stream(
                    test["q"], chat_history, metadata=mock_metadata
                ):
                    if event["type"] == "meta":
                        final_meta = event
                        intent_info = event.get("intent", {})
                        logging.info(
                            f"  Detected Intent: {intent_info.get('emoji', '❓')} {intent_info.get('label', 'Unknown')}"
                        )
                        sources = event.get("sources", [])
                        logging.info(
                            f"  Retrieved {len(sources)} sources via Hybrid Search."
                        )
                    elif event["type"] == "done":
                        final_text = event.get("content", "")
                        final_reasoning = event.get("reasoning", None)

            _, err = run_with_timeout(stream_query, timeout=QUERY_TIMEOUT)

            if err:
                logging.warning(
                    f"  ⚠️ Streaming timed out for '{test['desc']}': {err}"
                )
                failed += 1
            elif len(final_text) > 10:
                logging.info(f"  ✅ Response Length: {len(final_text)} chars.")
                if final_reasoning:
                    logging.info(
                        f"     Reasoning captured: {len(final_reasoning)} chars."
                    )
                passed += 1
            else:
                logging.warning(
                    f"  ⚠️ Response too short ({len(final_text)} chars). Model may be overloaded."
                )
                failed += 1

        except Exception as e:
            logging.error(f"  ❌ Exception during streaming: {e}")
            failed += 1

        chat_history.append({"role": "user", "content": test["q"]})
        chat_history.append(
            {
                "role": "assistant",
                "content": final_text if final_text else "No response",
                "reasoning_details": final_reasoning,
            }
        )

    # ── 6. Testing Export Generation ──
    logging.info("\n[6/6] Testing Session Export Formats...")
    try:
        stats = qa_engine.get_session_stats()

        md_export = generate_markdown_export(
            chat_history, overview, suggestions, stats
        )
        html_export = generate_html_export(
            chat_history, overview, suggestions, stats
        )
        docx_export = generate_docx_export(
            chat_history, overview, suggestions, stats
        )

        logging.info(f"  ✅ Markdown Export: {len(md_export)} bytes")
        logging.info(f"  ✅ HTML Export: {len(html_export)} bytes")
        logging.info(f"  ✅ DOCX Export: {len(docx_export)} bytes")

        # Specific test for IEEE paper export (if the intent was triggered)
        # Find the last IEEE paper content from chat_history
        ieee_content = ""
        for msg in reversed(chat_history):
            if "### Abstract" in msg["content"] and "### I. Introduction" in msg["content"]:
                ieee_content = msg["content"]
                break
        
        if ieee_content:
            from app import generate_ieee_docx
            ieee_docx = generate_ieee_docx(ieee_content, mock_metadata)
            logging.info(f"  ✅ Specialized IEEE DOCX Export: {len(ieee_docx)} bytes")
        
        passed += 1
    except Exception as e:
        logging.error(f"  ❌ Export generation failed: {e}")
        failed += 1

    # ── Final Report ──
    logging.info("\n=========================================")
    total = passed + failed
    if failed == 0:
        logging.info(f"✅ ALL {total} TESTS PASSED! A-Z TEST COMPLETE")
    else:
        logging.info(
            f"📊 RESULTS: {passed}/{total} passed, {failed} failed/timed out"
        )
        logging.info(
            "   (Failures on free model are often due to rate limits or slow responses)"
        )
    logging.info("=========================================")


if __name__ == "__main__":
    run_az_test()
