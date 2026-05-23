import sys
import os
from typing import List

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.topic_segmenter import TopicSegmenter
from src.topic_titler import TopicTitler

def run_sample_analysis():
    print("="*60)
    print("      RESEARCHHELP-AI ANALYSIS SYSTEM: SAMPLE TEST")
    print("="*60)
    
    segmenter = TopicSegmenter()
    titler = TopicTitler()
    
    # --- Sample 1: Dense Technical Text (Titling Precision) ---
    print("\n[TEST 1] Technical Titling Precision (NP-Chunking & Case Preservation)")
    tech_text = [
        "Modern deep learning architectures utilize GPU acceleration for BERT training.",
        "FPGA implementations of Neural Networks show significant power efficiency.",
        "Generative AI and Large Language Models require massive TPU clusters.",
        "Advanced LLM optimization techniques like Quantization and Pruning are vital."
    ]
    title = titler.generate_title(tech_text)
    print(f"Generated Title: {title}")
    print("Note: Should preserve technical acronyms like GPU, FPGA, AI, BERT, etc.")
    
    # --- Sample 2: Dynamic Segmentation (Statistical Analysis) ---
    print("\n" + "-"*60)
    print("[TEST 2] Dynamic Thematic Segmentation (No Hardcoded Boundaries)")
    
    document = """
    Document Overview: This segment discusses Artificial Intelligence in Healthcare.
    Machine learning models are being used to predict patient outcomes and diagnose diseases early.
    Computer vision helps radiologists identify anomalies in X-ray and MRI scans more accurately.
    Natural language processing allows for the extraction of metadata from unstructured medical records.
    The primary goal is to improve the efficiency and accuracy of clinical decision-making.
    
    Switching topics, let us examine the history of Urban Architecture in the 20th century.
    The rise of modernism led to the use of steel and glass in skyscraper construction.
    Le Corbusier and Frank Lloyd Wright were influential architects who redefined domestic spaces.
    Post-war reconstruction in Europe focused on functionalist designs and affordable housing.
    Brutalist architecture, characterized by raw concrete, became popular in institutional buildings.
    
    Finally, we look at Renewable Energy and the Global Climate Crisis.
    Solar and wind power are now cheaper than fossil fuels in many parts of the world.
    Energy storage systems like lithium-ion batteries are essential for grid stability.
    Policy markers are looking at carbon tax and green incentives to accelerate the transition.
    The biodiversity of the planet depends on our ability to reach net-zero emissions by 2050.
    """
    
    print("Running dynamic segmentation analysis...")
    segments = segmenter.segment(document)
    print(f"Total topics discovered: {len(segments)}")
    
    for seg in segments:
        print(f"\n- TOPIC {seg['topic_id']}: {seg['title']}")
        # Show first 80 chars of content
        print(f"  Snippet: {seg['content'][:80]}...")

    print("\n" + "="*60)
    print("SAMPLE TEST COMPLETE")
    print("="*60)

if __name__ == "__main__":
    run_sample_analysis()
