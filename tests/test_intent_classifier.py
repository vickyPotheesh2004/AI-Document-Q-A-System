import sys
import os
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.intent_classifier import IntentClassifier, INTENT_LABELS


@pytest.fixture
def classifier():
    with patch('src.intent_classifier.get_llm_client') as mock_get_llm_client:
        mock_client = MagicMock()
        mock_get_llm_client.return_value = mock_client
        
        c = IntentClassifier()
        c.mock_llm = mock_client
        return c


def test_rule_based_off_topic(classifier):
    # Rule based off_topic length must be < 25 chars and match keyword
    res = classifier.classify("Hello there buddy")
    assert res["intent"] == "off_topic"
    assert res["label"] == INTENT_LABELS["off_topic"]["label"]


def test_rule_based_suggestion_request(classifier):
    res = classifier.classify("Can you suggest some improvements for this architecture?")
    assert res["intent"] == "suggestion_request"


def test_rule_based_ieee_paper_gen(classifier):
    res = classifier.classify("Please generate an IEEE official paper from this.")
    assert res["intent"] == "ieee_paper_gen"


def test_rule_based_research_addon(classifier):
    res = classifier.classify("Can we add a solar panel to the drone design?")
    assert res["intent"] == "research_addon"


def test_rule_based_research_analysis(classifier):
    res = classifier.classify("Explain how quantum computing works.")
    assert res["intent"] == "research_analysis"


def test_rule_based_document_qa(classifier):
    res = classifier.classify("What does this document claim about the specific latency?")
    assert res["intent"] == "document_qa"


def test_llm_fallback_classification(classifier):
    # Setup the mock LLM to return 'off_topic' for a complex unrecognized string
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "off_topic"
    classifier.mock_llm.create_fast_completion.return_value = mock_response

    res = classifier.classify("I want a new pet dog.")
    assert res["intent"] == "off_topic"


def test_caching_mechanism(classifier):
    # Ensure cache works and doesn't call LLM twice for the same query
    query = "Unique phrase involving arbitrary fruits like orange and apple"
    
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "document_qa"
    classifier.mock_llm.create_fast_completion.return_value = mock_response

    # First call
    res1 = classifier.classify(query)
    
    # Second call
    res2 = classifier.classify(query)
    
    # Should only be called once because of cache
    classifier.mock_llm.create_fast_completion.assert_called_once()
    assert res1["intent"] == res2["intent"] == "document_qa"


def test_llm_failure_defaults_to_document_qa(classifier):
    # If the LLM call throws an exception, it should safely default to document_qa
    classifier.mock_llm.create_fast_completion.side_effect = Exception("API Timeout")
    
    res = classifier.classify("Random non matching query here.")
    assert res["intent"] == "document_qa"


if __name__ == "__main__":
    print("\n" + "="*50)
    print(" [TESTS] RUNNING INTENT CLASSIFIER TESTS")
    print("="*50 + "\n")
    pytest.main(["-v", "-s", __file__])
