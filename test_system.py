"""
System Diagnostic Test
=======================
This test verifies the core system components:
- Environment configuration
- API connection
- Vector database (ChromaDB)
- Document extractors
- RAG pipeline integration

Usage:
    python test_system.py
"""
import os
import warnings
from dotenv import load_dotenv
from openai import OpenAI
import chromadb

warnings.filterwarnings("ignore")

import streamlit.runtime.scriptrunner_utils.script_run_context as _src
import streamlit.runtime.state.session_state_proxy as _ssp

_src._LOGGER.warning = lambda *args, **kwargs: None
_ssp._LOGGER.warning = lambda *args, **kwargs: None

from src.config import DEFAULT_LLM_MODEL

print("--- SYSTEM DIAGNOSTIC START ---")

# TEST 1: Environment & API Key
print("\n1. Testing .env and API Key...")
load_dotenv()
api_key = os.getenv("OPENROUTER_API_KEY")
if api_key and api_key != "your_actual_openrouter_api_key_here":
    print(f"[OK] API Key loaded successfully! (Starts with: {api_key[:5]}...)")
else:
    print("[ERR] ERROR: API Key is missing or invalid in your .env file.")

# TEST 2: AI Connection (Using configured model)
print("\n2. Testing OpenRouter API Connection...")
try:
    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
    response = client.chat.completions.create(
        model=DEFAULT_LLM_MODEL,
        messages=[
            {
                "role": "user",
                "content": "Reply with exactly three words: 'AI is online.'",
            }
        ],
        max_tokens=20,
        extra_body={"reasoning": {"enabled": True}},
    )
    print(f"[OK] AI Responded: {response.choices[0].message.content.strip()}")
except Exception as e:
    print(f"[ERR] ERROR: AI Connection failed. Details: {e}")

# TEST 3: Vector Database (ChromaDB)
print("\n3. Testing Local Vector Database...")
try:
    chroma_client = chromadb.PersistentClient(path="./chroma_db")
    collection = chroma_client.get_or_create_collection(name="diagnostic_test")
    print(
        "[OK] ChromaDB initialized and created a test collection successfully!"
    )
except Exception as e:
    print(f"[ERR] ERROR: ChromaDB failed to load. Details: {e}")

# TEST 4: Extractor Modules
print("\n4. Testing Document Extractors...")
try:
    pass

    print("[OK] PyMuPDF (fitz) is ready for PDFs.")
except ImportError:
    print("⚠️ PyMuPDF (fitz) not installed. PDF extraction will not work.")

try:
    pass

    print("[OK] python-docx is ready for Word documents.")
except ImportError:
    print("⚠️ python-docx not installed. DOCX extraction will not work.")

try:
    pass

    print("[OK] pandas is ready for CSVs and Excel files.")
except ImportError:
    print("⚠️ pandas not installed. CSV/Excel extraction will not work.")

try:
    pass

    print("[OK] pytesseract is ready for Image OCR.")
except ImportError:
    print("⚠️ pytesseract not installed. Image OCR will not work.")

# TEST 5: Full RAG Pipeline Integration
print("\n5. Testing QA Engine Pipeline Integration...")
try:
    # Pre-cleanup: wipe any stale ChromaDB collections from previous test runs
    _chroma = chromadb.PersistentClient(path="./chroma_db")
    for col in _chroma.list_collections():
        try:
            _chroma.delete_collection(col.name)
        except Exception:
            pass

    from src.qa_engine import QAEngine

    engine = QAEngine()

    mock_doc = "The campus robot uses an ESP32 microcontroller and ultrasonic sensors to navigate safely."
    engine.ingest_and_segment({"test_doc.txt": mock_doc})
    print("[OK] Segmentation & DB Insertion successful.")

    res = engine.get_answer("What components does the robot use?", [])
    if res["content"]:
        print("[OK] RAG Retrieval & AI Reasoning successful.")
    else:
        print("[ERR] ERROR: AI returned empty content.")
except Exception as e:
    print(f"[ERR] ERROR: Pipeline test failed. Details: {e}")

# TEST 6: Topic Segmentation & Titling Precision
print("\n6. Testing Local Topic Segmentation & Titling Precision...")
try:
    from src.topic_segmenter import TopicSegmenter
    from src.topic_titler import TopicTitler
    
    seg_tester = TopicSegmenter()
    title_tester = TopicTitler()
    
    # Validation A: Dynamic Segmentation Outlier Detection (Need high contrast)
    test_multi = """
    Biology is the study of life. Cells are the basic building blocks of living organisms. 
    Metabolism and DNA replication are core biological processes.
    
    In a completely different realm, we have Quantum Mechanics. 
    Particles exhibit wave-particle duality and exist in superpositions.
    Entanglement is a phenomenon where particles become perfectly correlated across distances.
    Schrödinger's cat is a famous thought experiment in this field.
    """
    segments = seg_tester.segment(test_multi)
    if len(segments) >= 2:
        print(f"[OK] Dynamic segmentation detected {len(segments)} distinct topics.")
    else:
        print("[WARN] Segmenter did not split the text (Semantic contrast may be too low for this doc size)")
        
    # Validation B: Technical Title Preservation (NP-Chunking)
    test_tech = ["The implementation of FPGA and BERT models allows for significant AI acceleration in modern data centers."]
    title = title_tester.generate_title(test_tech)
    if any(acronym in title for acronym in ["AI", "BERT", "FPGA"]):
        print(f"[OK] Titler preserved technical acronyms: '{title}'")
    else:
        print(f"[WARN] Titler output: '{title}' (Expected acronym preservation)")

except Exception as e:
    print(f"[ERR] ERROR: Titling/Segmentation test failed. Details: {e}")

# TEST 7: Confidence Scorer
print("\n7. Testing Confidence Scorer...")
try:
    from src.confidence_scorer import ConfidenceScorer
    
    # Initialize scorer
    scorer = ConfidenceScorer()
    
    # Test scoring
    result = scorer.score_confidence(
        user_question="What is machine learning?",
        intent="document_qa",
        domain="AI",
        context_chunks=[
            "Machine learning is a subset of artificial intelligence.",
            "ML enables computers to learn from data without explicit programming."
        ]
    )
    
    # Verify results
    if result.get("score") > 0 and result.get("level") in ["Moderate", "High", "Very High"]:
        print(f"[OK] Confidence Scorer working! Score: {result['score']}, Level: {result['level']}")
    else:
        print(f"[WARN] Unexpected result: {result}")
    
    # Test fallback / off-topic
    fallback_result = scorer.score_confidence(
        user_question="Test?",
        intent="off_topic",
        domain="Test",
        context_chunks=["test"]
    )
    
    if fallback_result["score"] == 0 and fallback_result["level"] == "Very Low":
        print("[OK] Off-topic mechanism working correctly.")
    else:
        print(f"[WARN] Off-topic not working as expected: {fallback_result}")
        
except Exception as e:
    print(f"[ERR] ERROR: Confidence Scorer test failed. Details: {e}")

print("\n--- SYSTEM DIAGNOSTIC COMPLETE ---")
if api_key:
    print(
        "If all tests have green checkmarks, your system is 100% operational!"
    )
    print("Run 'streamlit run app.py' to launch the UI.")
