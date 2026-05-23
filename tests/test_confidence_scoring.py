import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))
from src.confidence_scorer import ConfidenceScorer


@pytest.fixture
def scorer():
    return ConfidenceScorer()


def test_off_topic_returns_very_low(scorer):
    result = scorer.score_confidence(
        user_question="What is the weather today?",
        intent="off_topic",
        domain="General",
        context_chunks=["Machine learning is a subset of AI."],
    )
    assert result["score"] <= 15
    assert result["level"] == "Very Low"
    assert "breakdown" in result


def test_relevant_query_high_score(scorer):
    result = scorer.score_confidence(
        user_question="What is the attention mechanism in transformers?",
        intent="document_qa",
        domain="AI",
        context_chunks=[
            "The attention mechanism allows transformers to focus on relevant parts of the input sequence.",
            "Self-attention computes query, key, and value vectors from the input embeddings.",
            "Multi-head attention enables the model to attend to information from different positions.",
        ],
        retrieval_scores=[0.85, 0.72, 0.65],
        answer_text="The attention mechanism in transformers allows the model to weigh the importance of different input tokens. It uses query, key, and value vectors.",
        has_sources=True,
    )
    assert result["score"] >= 50
    assert result["level"] in ["High", "Very High", "Moderate"]


def test_irrelevant_query_low_score(scorer):
    result = scorer.score_confidence(
        user_question="How to cook pasta?",
        intent="document_qa",
        domain="General",
        context_chunks=[
            "Neural networks consist of layers of interconnected nodes.",
            "Backpropagation is used to train deep learning models.",
        ],
        retrieval_scores=[0.15, 0.10],
        answer_text="I apologize, but I cannot provide information about cooking pasta as it is not in the document.",
        has_sources=True,
    )
    assert result["score"] <= 45


def test_different_queries_different_scores(scorer):
    chunks = [
        "Machine learning is used for pattern recognition.",
        "Neural networks are inspired by biological neurons.",
        "Deep learning uses multiple layers for feature extraction.",
    ]
    scores = [0.8, 0.7, 0.6]

    result1 = scorer.score_confidence(
        user_question="What is machine learning?",
        intent="document_qa", domain="AI",
        context_chunks=chunks, retrieval_scores=scores,
    )
    result2 = scorer.score_confidence(
        user_question="What is quantum computing?",
        intent="document_qa", domain="General",
        context_chunks=chunks, retrieval_scores=scores,
    )
    assert result1["score"] != result2["score"]


def test_empty_chunks_low_score(scorer):
    result = scorer.score_confidence(
        user_question="What is deep learning?",
        intent="document_qa",
        domain="General",
        context_chunks=[],
        has_sources=False,
    )
    assert result["score"] <= 25


def test_breakdown_contains_all_factors(scorer):
    result = scorer.score_confidence(
        user_question="Explain transformers",
        intent="document_qa",
        domain="AI",
        context_chunks=["Transformers use self-attention mechanisms."],
        retrieval_scores=[0.75],
    )
    breakdown = result.get("breakdown", {})
    assert "retrieval" in breakdown
    assert "grounding" in breakdown
    assert "overlap" in breakdown
    assert "certainty" in breakdown


def test_hedging_lowers_certainty(scorer):
    hedging_answer = "Maybe the model could possibly work, but it might not be entirely accurate. Perhaps further testing is needed."
    confident_answer = "The model definitely works. Evidence shows that it consistently achieves high accuracy across all benchmarks."

    hedging_cert = scorer._compute_certainty_heuristic(hedging_answer)
    confident_cert = scorer._compute_certainty_heuristic(confident_answer)

    assert hedging_cert < confident_cert


def test_source_overlap_high_when_relevant(scorer):
    score = scorer._compute_source_overlap(
        query="transformer attention mechanism",
        context_chunks=["The transformer model uses multi-head attention mechanism for sequence processing."]
    )
    assert score >= 40


def test_source_overlap_low_when_irrelevant(scorer):
    score = scorer._compute_source_overlap(
        query="cooking pasta recipe",
        context_chunks=["The transformer model uses self-attention for NLP tasks."]
    )
    assert score <= 30


def test_grounding_score_high_when_supported(scorer):
    answer = "Machine learning uses pattern recognition. Neural networks have layers of nodes."
    chunks = ["Machine learning is about pattern recognition.", "Neural networks consist of multiple layers of interconnected nodes."]
    score = scorer._compute_grounding_score(answer, chunks)
    assert score >= 40


def test_grounding_score_low_when_unsupported(scorer):
    answer = "Quantum teleportation enables faster communication across galaxies."
    chunks = ["Machine learning is about pattern recognition."]
    score = scorer._compute_grounding_score(answer, chunks)
    assert score <= 50


def test_update_with_answer_changes_score(scorer):
    initial = scorer.score_confidence(
        user_question="What is deep learning?",
        intent="document_qa", domain="AI",
        context_chunks=["Deep learning uses neural networks with many layers."],
        retrieval_scores=[0.8],
    )

    updated = scorer.update_with_answer(
        initial,
        "Deep learning is a subset of machine learning that uses neural networks with many layers for feature extraction.",
        ["Deep learning uses neural networks with many layers."],
    )

    assert initial["score"] != updated["score"]
    assert "breakdown" in updated


def test_retrieval_relevance_scales_with_scores(scorer):
    low = scorer._compute_retrieval_relevance([0.1, 0.05], ["a", "b"])
    high = scorer._compute_retrieval_relevance([0.9, 0.85], ["a", "b"])
    assert high > low


def test_score_to_level_complete_mapping():
    test_cases = [
        (0, "Very Low"), (24, "Very Low"),
        (25, "Low"), (44, "Low"),
        (45, "Moderate"), (64, "Moderate"),
        (65, "High"), (84, "High"),
        (85, "Very High"), (100, "Very High"),
    ]
    for score, expected in test_cases:
        actual = ConfidenceScorer._score_to_level(score)
        assert actual == expected


def test_score_bounded_0_100(scorer):
    result = scorer.score_confidence(
        user_question="test",
        intent="document_qa", domain="",
        context_chunks=["test context"] * 20,
        retrieval_scores=[0.99] * 20,
        answer_text="test " * 500,
        has_sources=True,
    )
    assert 0 <= result["score"] <= 100


def test_criteria_based_delegates_to_score_confidence(scorer):
    result = scorer._criteria_based_scoring(
        user_question="test",
        intent="document_qa",
        domain="AI",
        context_chunks=["test data"],
    )
    assert "score" in result
    assert "level" in result
    assert "reason" in result


def test_apology_lowers_certainty(scorer):
    apology = "I apologize, but I cannot provide that information as it is not mentioned in the documents."
    normal = "The transformer architecture uses self-attention for efficient sequence processing."

    apology_cert = scorer._compute_certainty_heuristic(apology)
    normal_cert = scorer._compute_certainty_heuristic(normal)

    assert apology_cert < normal_cert


def run_demo():
    """Prints a clear, visual demo of the Confidence Scorer in action."""
    print("=" * 60)
    print(" [DEMO] CONFIDENCE SCORING LIVE DEMO")
    print("=" * 60)
    
    scorer = ConfidenceScorer()
    
    query = "What is the attention mechanism in transformers?"
    context = [
        "The attention mechanism allows transformers to focus on relevant parts of the input sequence.",
        "Self-attention computes query, key, and value vectors from the input embeddings."
    ]
    answer = "The attention mechanism in transformers allows the model to weigh the importance of different input tokens by computing query, key, and value vectors."
    
    print(f"User Query: '{query}'")
    print(f"Context Provided:")
    for i, c in enumerate(context):
        print(f"  [{i+1}] {c}")
    print(f"\nGenerated Answer: '{answer}'")
    print("-" * 60)
    print("Scoring Answer...")
    
    result = scorer.score_confidence(
        user_question=query,
        intent="document_qa",
        domain="AI",
        context_chunks=context,
        retrieval_scores=[0.85, 0.72],
        answer_text=answer,
        has_sources=True,
    )
    
    print(f"\n [SCORE] Final Score: {result['score']} / 100")
    print(f" [LEVEL] Level:       {result['level']}")
    print("\n [INFO] Score Breakdown (out of 100):")
    for metric, val in result.get('breakdown', {}).items():
        print(f"  - {metric.capitalize():<10}: {val:.1f} / 100")
        
    print(f"\n [REASON] Explanatory Reason:")
    print(f" {result.get('reason', 'N/A')}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    import pytest
    run_demo()
    print("\n" + "="*50)
    print(" [TESTS] RUNNING CONFIDENCE SCORING TESTS")
    print("="*50 + "\n")
    pytest.main(["-v", "-s", __file__])
