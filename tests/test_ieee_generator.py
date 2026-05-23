"""
IEEE Paper Generator Test
=======================
This test validates the IEEE paper generation feature:
- IEEE intent classification
- Metadata injection in prompts
- Prompt template structure

Usage:
    python test_ieee_generator.py
"""
import sys
import os
import json

# Add src to path
sys.path.append(os.path.abspath("src"))

from src.intent_classifier import IntentClassifier
from src.prompt_templates import get_prompt_for_intent


def test_ieee_classification():
    print("\n--- Testing IEEE Intent Classification ---")
    classifier = IntentClassifier()

    test_queries = [
        "Generate an IEEE official paper for this project",
        "Write an academic publication about the findings",
        "I need a research paper manuscript in IEEE format",
        "Create an official journal paper based on our analysis",
        "Generate an IEEE conference paper",
    ]

    for q in test_queries:
        intent = classifier._rule_based_classify(q)
        print(f"Query: '{q}' -> Intent: {intent}")
        assert intent == "ieee_paper_gen", f"Failed for query: {q}"

    print("✅ IEEE Intent Classification Passed!")


def test_metadata_injection():
    print("\n--- Testing Metadata Injection in Prompt ---")
    metadata = {
        "title": "AI in VLSI Optimization",
        "authors": "Antigravity, Deepmind Team",
        "emails": "anti@gravity.ai, research@deepmind.com",
        "colleges": "Global Institute of AI, Google Research",
    }

    prompt = get_prompt_for_intent("ieee_paper_gen")
    assert "{metadata}" in prompt

    # Simulate QAEngine injection
    meta_str = json.dumps(metadata, indent=2)
    injected_prompt = prompt.replace("{metadata}", meta_str)

    print("Injected Prompt Preview:")
    print(injected_prompt[:300] + "...")

    assert metadata["title"] in injected_prompt
    assert metadata["authors"] in injected_prompt
    assert "Distinguished Research Scientist" in injected_prompt

    print("✅ Metadata Injection Passed!")


if __name__ == "__main__":
    try:
        test_ieee_classification()
        test_metadata_injection()
        print("\n🎉 ALL IEEE GENERATOR TESTS PASSED!")
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ AN ERROR OCCURRED: {str(e)}")
        sys.exit(1)
