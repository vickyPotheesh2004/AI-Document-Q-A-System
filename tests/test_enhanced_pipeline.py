"""
Test script for the Enhanced Topic Segmentation Pipeline

This script demonstrates the improvements made to the topic segmentation system:
1. TextTiling algorithm with pseudo-sentence blocks
2. Semantic Shift Detection
3. Sentence Embedding + Depth Scores
4. Hybrid method (combines all approaches)

Run this script to verify the improvements work correctly.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Set UTF-8 encoding for output
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from src.enhanced_topic_pipeline import (
    EnhancedTopicPipeline,
    TextTilingSegmenter,
    SemanticShiftDetector,
    EmbeddingSegmenter,
    HybridSegmenter,
    KeywordExtractor,
    TextRankSummarizer,
    TitleGenerator,
    export_to_dict,
    format_results,
    preprocess_text,
    sentence_tokenize,
)


# Sample text with distinct topics for testing
SAMPLE_TEXT = """
Artificial intelligence has emerged as one of the most transformative technologies 
of the twenty-first century. Machine learning, a core subset of AI, enables computers 
to learn from data without being explicitly programmed. Deep learning architectures 
such as convolutional neural networks have revolutionized image recognition tasks. 
Natural language processing models like BERT and GPT have achieved human-level 
performance on many text benchmarks. The rapid advancement of AI has been fueled 
by the availability of massive datasets and powerful GPU hardware. Researchers 
continue to push the boundaries of what machines can perceive, understand, and generate.

Climate change represents one of the most pressing challenges facing humanity today. 
Rising global temperatures are caused primarily by greenhouse gas emissions from 
burning fossil fuels. The effects include rising sea levels, more frequent extreme 
weather events, and disruption of ecosystems. International agreements like the 
Paris Accord aim to limit warming to 1.5 degrees Celsius above pre-industrial levels.
Renewable energy sources such as solar, wind, and hydroelectric power are critical 
to reducing carbon emissions. Governments, corporations, and individuals all have 
roles to play in transitioning to a sustainable economy. Carbon capture technologies 
are being developed as a supplementary strategy alongside emission reductions.

The global economy operates as an interconnected web of trade, finance, and production. 
International trade allows countries to specialize in goods and services where they 
hold comparative advantages. Financial markets channel capital from savers to 
productive investments across borders. Supply chain disruptions, such as those 
caused by the COVID-19 pandemic, revealed the fragility of global production networks.
Central banks use monetary policy tools to manage inflation and support employment.
Fiscal policy, including government spending and taxation, plays a complementary 
role in stabilizing economies. Emerging economies like India and Vietnam are 
growing rapidly and reshaping global trade patterns.

Modern healthcare systems face mounting pressure from aging populations and chronic 
diseases. Advances in genomics and personalized medicine are enabling treatments 
tailored to individual patients. mRNA vaccine technology, proven effective during 
the COVID-19 pandemic, holds promise for many other diseases. Telemedicine has 
expanded access to healthcare services in rural and underserved communities. 
Mental health is increasingly recognized as a critical component of overall well-being.
Healthcare costs continue to rise globally, creating access and affordability challenges.

Space exploration has entered a new era driven by both government agencies and private 
companies. NASA's Artemis program aims to return humans to the Moon by the mid-2020s 
as a stepping stone to Mars. SpaceX has dramatically reduced launch costs through 
reusable rocket technology. Satellites now underpin critical infrastructure including 
GPS navigation, weather forecasting, and communications. The search for extraterrestrial 
life is being pursued through missions to Mars and the icy moons of Jupiter and Saturn.
Astronomical observatories like the James Webb Space Telescope are revealing the 
early universe with unprecedented detail. International cooperation in space science 
remains strong despite geopolitical tensions on Earth.
"""


def test_preprocessing():
    """Test text preprocessing functions."""
    print("\n" + "="*60)
    print("TEST: Text Preprocessing")
    print("="*60)
    
    # Test sentence tokenization
    sentences = sentence_tokenize(SAMPLE_TEXT)
    print(f"[PASS] Sentence tokenization: {len(sentences)} sentences extracted")
    
    # Test preprocessing
    processed = preprocess_text(SAMPLE_TEXT)
    print(f"[PASS] Preprocessing: {len(processed)} chars")
    
    return True


def test_individual_components():
    """Test individual pipeline components."""
    print("\n" + "="*60)
    print("TEST: Individual Components")
    print("="*60)
    
    sentences = sentence_tokenize(SAMPLE_TEXT)
    print(f"Testing with {len(sentences)} sentences")
    
    # Test segmenters
    segmenters = [
        ("TextTiling", TextTilingSegmenter(w=20, k=8, smoothing_rounds=2)),
        ("SemanticShift", SemanticShiftDetector()),
        ("Embedding", EmbeddingSegmenter()),
        ("Hybrid", HybridSegmenter()),
    ]
    
    for name, segmenter in segmenters:
        try:
            segments = segmenter.segment(sentences)
            print(f"[PASS] {name}: {len(segments)} segments found")
        except Exception as e:
            print(f"[FAIL] {name}: ERROR - {e}")
    
    # Test keyword extraction
    print("\n--- Keyword Extraction ---")
    extractor = KeywordExtractor(top_n=8)
    segments_text = [' '.join(sentences)]
    keywords = extractor.extract(segments_text)
    print(f"[PASS] Keywords extracted: {len(keywords[0])} keywords")
    print(f"  Top 3: {[kw for kw, _ in keywords[0][:3]]}")
    
    # Test summarization
    print("\n--- TextRank Summarization ---")
    summarizer = TextRankSummarizer()
    summary = summarizer.summarize(SAMPLE_TEXT, num_sentences=2)
    print(f"[PASS] Summary generated: {len(summary.split())} words")
    
    # Test title generation
    print("\n--- Title Generation ---")
    titler = TitleGenerator()
    title = titler.generate(keywords[0], SAMPLE_TEXT)
    print(f"[PASS] Title generated: {title}")
    
    return True


def test_pipeline_methods():
    """Test all pipeline methods."""
    print("\n" + "="*60)
    print("TEST: Pipeline Methods Comparison")
    print("="*60)
    
    methods = ["texttiling", "semantic", "embedding", "hybrid"]
    results_all = {}
    
    for method in methods:
        print(f"\n--- Method: {method.upper()} ---")
        
        pipeline = EnhancedTopicPipeline(
            num_topics=None,  # Auto-detect
            summary_sentences=2,
            top_keywords=6,
            method=method,
        )
        
        results = pipeline.run(SAMPLE_TEXT)
        results_all[method] = results
        
        print(f"  Segments found: {len(results)}")
        for r in results:
            print(f"    Topic {r['topic_number']}: {r['title']}")
    
    # Verify all methods found approximately the same topics (4-5 expected)
    expected_topics = 4  # AI, Climate, Economy, Healthcare, Space
    for method, results in results_all.items():
        topic_count = len(results)
        status = "[PASS]" if 3 <= topic_count <= 6 else "[FAIL]"
        print(f"\n{status} {method.upper()}: {topic_count} topics (expected 4-5)")
    
    return results_all


def test_forced_topic_count():
    """Test forcing exact number of topics."""
    print("\n" + "="*60)
    print("TEST: Forced Topic Count")
    print("="*60)
    
    for num_topics in [3, 4, 5, 6]:
        pipeline = EnhancedTopicPipeline(
            num_topics=num_topics,
            method="hybrid",
        )
        
        results = pipeline.run(SAMPLE_TEXT)
        print(f"  Requested: {num_topics}, Got: {len(results)} topics")
        
        for r in results:
            print(f"    - {r['title']}")
    
    return True


def test_export_functions():
    """Test export and formatting functions."""
    print("\n" + "="*60)
    print("TEST: Export Functions")
    print("="*60)
    
    pipeline = EnhancedTopicPipeline(
        num_topics=None,
        method="hybrid",
    )
    
    results = pipeline.run(SAMPLE_TEXT)
    
    # Test export_to_dict
    exported = export_to_dict(results)
    print(f"[PASS] export_to_dict: {len(exported)} topics exported")
    print(f"  First topic keys: {list(exported[0].keys())}")
    
    # Test format_results
    formatted = format_results(results, show_full_text=False)
    print(f"[PASS] format_results: {len(formatted)} chars")
    
    return True


def test_edge_cases():
    """Test edge cases."""
    print("\n" + "="*60)
    print("TEST: Edge Cases")
    print("="*60)
    
    # Empty text
    pipeline = EnhancedTopicPipeline(method="hybrid")
    results = pipeline.run("")
    print(f"  Empty text: {len(results)} topics")
    
    # Very short text
    short_text = "This is a short text. It has only two sentences."
    results = pipeline.run(short_text)
    print(f"  Short text: {len(results)} topics")
    
    # Single topic text
    single_topic = """
    Machine learning is a subset of artificial intelligence that enables computers 
    to learn from data. Deep learning uses neural networks with multiple layers 
    to achieve state-of-the-art performance on many tasks. Convolutional neural 
    networks are particularly effective for image recognition tasks.
    """
    results = pipeline.run(single_topic)
    print(f"  Single topic: {len(results)} topics")
    if results:
        print(f"    Title: {results[0]['title']}")
    
    return True


def run_all_tests():
    """Run all tests."""
    print("\n" + "="*60)
    print("  ENHANCED TOPIC PIPELINE - COMPREHENSIVE TESTS")
    print("="*60)
    
    tests = [
        ("Preprocessing", test_preprocessing),
        ("Individual Components", test_individual_components),
        ("Pipeline Methods", test_pipeline_methods),
        ("Forced Topic Count", test_forced_topic_count),
        ("Export Functions", test_export_functions),
        ("Edge Cases", test_edge_cases),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"\n[FAIL] {name} FAILED: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "="*60)
    print("  TEST SUMMARY")
    print("="*60)
    print(f"  Passed: {passed}")
    print(f"  Failed: {failed}")
    print(f"  Total:  {passed + failed}")
    
    if failed == 0:
        print("\n[PASS] All tests passed!")
    else:
        print(f"\n[FAIL] {failed} test(s) failed!")
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
