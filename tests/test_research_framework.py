"""
Research Framework Test
====================
This test validates the research analysis framework:
- Research domain intent classification
- Contextual sensitivity (near-document queries)
- Prompt template retrieval

Usage:
    python test_research_framework.py
"""
import os
import sys
from dotenv import load_dotenv

# Add src to path
sys.path.append(os.getcwd())

from src.intent_classifier import IntentClassifier


def test_research_classification():
    classifier = IntentClassifier()

    test_queries = [
        "Explain Quantum Computing in simple terms",
        "How does 5G technology work?",
        "What are the basics of Artificial Intelligence?",
        "Tell me about VLSI Design",
        "What is Blockchain?",
        "How do autonomous vehicles function?",
    ]

    print("--- Testing Intent Classification ---")
    for query in test_queries:
        result = classifier.classify(query)
        print(f"Query: {query}")
        print(f"Intent: {result['intent']} ({result['label']})")
        assert result["intent"] == "research_analysis"
        print("OK")
    print("Classification tests passed!\n")


def test_sensitivity_classification():
    classifier = IntentClassifier()
    # Mock some topics that might be in a document
    available_topics = [
        "Project Architecture",
        "System Requirements",
        "Cloud Deployment",
    ]

    test_queries = [
        "Tell me more about the project",  # Near-document
        "What are the requirements for this?",  # Near-document
        "How do I deploy this to the cloud?",  # Near-document
        "Explain the architecture mentioned here",  # Near-document
    ]

    print("--- Testing Intent Sensitivity (Near-Document Queries) ---")
    for query in test_queries:
        result = classifier.classify(query, available_topics=available_topics)
        print(f"Query: {query}")
        print(f"Intent: {result['intent']} ({result['label']})")
        # These should be document_qa because they are 'near' the topic or context
        assert result["intent"] == "document_qa"
        print("OK")
    print("Sensitivity tests passed!\n")


def test_research_response_structure():
    # This requires an active session with some documents
    # For now, we'll just check if we can get the prompt correctly
    from src.prompt_templates import get_prompt_for_intent

    print("--- Testing Prompt Retrieval ---")
    prompt = get_prompt_for_intent("research_analysis")
    assert "ANTIGRAVITY_SIMPLE_RESEARCH_ENGINE" in prompt
    assert "Question Understanding" in prompt
    assert "Basic Idea" in prompt
    assert "Deep Explanation" in prompt
    print("Prompt retrieval test passed!\n")


if __name__ == "__main__":
    load_dotenv()
    try:
        test_research_classification()
        test_sensitivity_classification()
        test_research_response_structure()
        print("All tests passed successfully!")
    except AssertionError as e:
        print(f"Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)
