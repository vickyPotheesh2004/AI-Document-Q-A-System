import sys
import os
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.research_engine import ResearchEngine
from src.logging_utils import get_logger

logger = get_logger(__name__)

def test_suggestions():
    load_dotenv()
    engine = ResearchEngine()
    
    # Dummy data
    chunks = ["Artificial intelligence is transforming healthcare by improving diagnostics and personalized medicine. Deep learning models can analyze medical images with high accuracy."]
    metas = [{"source_file": "health_ai.pdf", "topic": "AI in Healthcare"}]
    
    print("=" * 60)
    print("      AI SUGGESTIONS GENERATION TEST")
    print("=" * 60)
    
    try:
        suggestions = engine.generate_auto_suggestions(chunks, metas)
        print(f"Suggestions received: {len(suggestions)}")
        for i, s in enumerate(suggestions):
            print(f"{i+1}. [{s.get('category', 'N/A')}] {s.get('title', 'N/A')}")
            print(f"   {s.get('description', 'N/A')}")
            
        if not suggestions:
            print("No suggestions generated. Check logs for JSON errors.")
            
    except Exception as e:
        print(f"FAILED! Error: {str(e)}")
    
    print("=" * 60)

if __name__ == "__main__":
    test_suggestions()
