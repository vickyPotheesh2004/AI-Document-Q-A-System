"""
Confidence Scorer Module for ResearchHelp-AI Analysis System.

Deterministic 4-factor scoring engine that evaluates answer confidence
without relying on external LLM API calls.

Confidence Score (%) =
  (0.4 × Retrieval Relevance) +
  (0.3 × Answer Grounding) +
  (0.2 × Source Overlap) +
  (0.1 × Model Certainty Heuristic)
"""

from __future__ import annotations

import re
import math
import logging
from collections import Counter

logger = logging.getLogger(__name__)


HEDGING_WORDS = {
    "maybe", "possibly", "perhaps", "might", "could", "likely",
    "unlikely", "uncertain", "unclear", "not sure", "not certain",
    "debatable", "arguable", "questionable", "speculative",
    "it seems", "it appears", "it may", "it might",
    "i think", "i believe", "i suppose", "presumably",
    "roughly", "approximately", "around", "about",
}

STRONG_ASSERTION_WORDS = {
    "definitely", "certainly", "clearly", "undoubtedly",
    "obviously", "precisely", "exactly", "always", "never",
    "proven", "confirmed", "established", "demonstrated",
    "evidence shows", "data confirms", "results indicate",
}


class ConfidenceScorer:
    """
    Deterministic confidence scoring engine using a 4-factor weighted formula:
      - Retrieval Relevance (40%): normalized retrieval scores from hybrid search
      - Answer Grounding (30%): sentence-level overlap between answer and sources
      - Source Overlap (20%): keyword overlap ratio between query and chunks
      - Model Certainty (10%): hedging word penalty scanner
    """

    WEIGHTS = {
        "retrieval": 0.4,
        "grounding": 0.3,
        "overlap": 0.2,
        "certainty": 0.1,
    }

    FALLBACK = {"score": 50, "level": "Moderate", "reason": "Score unavailable — showing default."}

    def __init__(self, llm_client=None):
        self.client = llm_client

    def score_confidence(
        self,
        user_question: str,
        intent: str,
        domain: str,
        context_chunks: list[str],
        retrieval_scores: list[float] | None = None,
        answer_text: str = "",
        has_sources: bool = True,
        max_context_chars: int = 3000,
    ) -> dict:
        """
        Computes a deterministic confidence score using 4 weighted factors.

        Returns dict with keys:
          score (int 0-100), level (str), reason (str),
          breakdown (dict with 4 factor scores)
        """
        if intent == "off_topic":
            return {
                "score": 0,
                "level": "Very Low",
                "reason": "Query is classified as off-topic — unrelated to uploaded documents.",
                "breakdown": {"retrieval": 0, "grounding": 0, "overlap": 0, "certainty": 0},
            }

        retrieval = self._compute_retrieval_relevance(retrieval_scores, context_chunks)
        overlap = self._compute_source_overlap(user_question, context_chunks)
        grounding = self._compute_grounding_score(answer_text, context_chunks) if answer_text else overlap * 0.8
        certainty = self._compute_certainty_heuristic(answer_text) if answer_text else 70.0

        raw_score = (
            self.WEIGHTS["retrieval"] * retrieval
            + self.WEIGHTS["grounding"] * grounding
            + self.WEIGHTS["overlap"] * overlap
            + self.WEIGHTS["certainty"] * certainty
        )

        if not has_sources or not context_chunks:
            raw_score *= 0.3

        if domain and domain != "General":
            raw_score = min(100, raw_score + 5)

        score = max(0, min(100, int(round(raw_score))))
        level = self._score_to_level(score)
        reason = self._generate_explanation(retrieval, grounding, overlap, certainty, score)

        breakdown = {
            "retrieval": int(round(retrieval)),
            "grounding": int(round(grounding)),
            "overlap": int(round(overlap)),
            "certainty": int(round(certainty)),
        }

        logger.info(
            f"[ConfidenceScorer] score={score} retrieval={retrieval:.1f} "
            f"grounding={grounding:.1f} overlap={overlap:.1f} certainty={certainty:.1f} intent={intent}"
        )

        return {"score": score, "level": level, "reason": reason, "breakdown": breakdown}

    def update_with_answer(self, previous_result: dict, answer_text: str, context_chunks: list[str]) -> dict:
        """
        Re-scores confidence after the answer is generated,
        using the actual answer text for grounding and certainty factors.
        """
        if not answer_text or not previous_result:
            return previous_result

        grounding = self._compute_grounding_score(answer_text, context_chunks)
        certainty = self._compute_certainty_heuristic(answer_text)

        retrieval = previous_result.get("breakdown", {}).get("retrieval", 50)
        overlap = previous_result.get("breakdown", {}).get("overlap", 50)

        raw_score = (
            self.WEIGHTS["retrieval"] * retrieval
            + self.WEIGHTS["grounding"] * grounding
            + self.WEIGHTS["overlap"] * overlap
            + self.WEIGHTS["certainty"] * certainty
        )

        score = max(0, min(100, int(round(raw_score))))
        level = self._score_to_level(score)
        reason = self._generate_explanation(retrieval, grounding, overlap, certainty, score)

        return {
            "score": score,
            "level": level,
            "reason": reason,
            "breakdown": {
                "retrieval": int(round(retrieval)),
                "grounding": int(round(grounding)),
                "overlap": int(round(overlap)),
                "certainty": int(round(certainty)),
            },
        }

    # ── Factor 1: Retrieval Relevance (40%) ──────────────────────────────────

    def _compute_retrieval_relevance(
        self, retrieval_scores: list[float] | None, context_chunks: list[str]
    ) -> float:
        """
        Normalizes hybrid retrieval scores to 0-100.
        Retrieval scores from QAEngine are already 0-1 (semantic*0.7 + BM25*0.3).
        """
        if retrieval_scores and len(retrieval_scores) > 0:
            valid_scores = [s for s in retrieval_scores if s > 0]
            if valid_scores:
                avg = sum(valid_scores) / len(valid_scores)
                top_score = max(valid_scores)
                relevance = (avg * 0.6 + top_score * 0.4) * 100
                chunk_bonus = min(len(valid_scores) * 3, 15)
                return min(100, relevance + chunk_bonus)

        if context_chunks:
            return min(40 + len(context_chunks) * 5, 65)

        return 10.0

    # ── Factor 2: Answer Grounding (30%) ─────────────────────────────────────

    def _compute_grounding_score(self, answer_text: str, context_chunks: list[str]) -> float:
        """
        Measures what percentage of the answer content is supported by source chunks.
        Splits answer into sentences and checks keyword overlap with chunks.
        """
        if not answer_text or not context_chunks:
            return 10.0

        combined_source = " ".join(context_chunks).lower()
        source_words = set(re.findall(r'\b[a-z]{3,}\b', combined_source))

        if not source_words:
            return 10.0

        sentences = re.split(r'[.!?]+', answer_text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 10]

        if not sentences:
            return 30.0

        grounded_count = 0
        for sentence in sentences:
            sentence_words = set(re.findall(r'\b[a-z]{3,}\b', sentence.lower()))
            if not sentence_words:
                continue
            overlap = len(sentence_words & source_words) / len(sentence_words)
            if overlap >= 0.25:
                grounded_count += 1

        grounding_ratio = grounded_count / len(sentences) if sentences else 0
        return min(100, grounding_ratio * 100)

    # ── Factor 3: Source Overlap (20%) ───────────────────────────────────────

    def _compute_source_overlap(self, query: str, context_chunks: list[str]) -> float:
        """
        Measures keyword overlap between the user query and retrieved context chunks.
        Uses both exact word matching and n-gram similarity.
        """
        if not query or not context_chunks:
            return 5.0

        q_words = set(re.findall(r'\b[a-z]{3,}\b', query.lower()))
        if not q_words:
            return 15.0

        combined_ctx = " ".join(context_chunks).lower()
        ctx_words = set(re.findall(r'\b[a-z]{3,}\b', combined_ctx))

        if not ctx_words:
            return 5.0

        exact_matches = len(q_words & ctx_words)
        exact_ratio = exact_matches / len(q_words)

        q_bigrams = self._get_bigrams(query.lower())
        ctx_bigrams = self._get_bigrams(combined_ctx)

        if q_bigrams and ctx_bigrams:
            bigram_overlap = len(q_bigrams & ctx_bigrams) / len(q_bigrams)
        else:
            bigram_overlap = 0

        score = (exact_ratio * 70) + (bigram_overlap * 30)
        return min(100, score)

    # ── Factor 4: Model Certainty Heuristic (10%) ───────────────────────────

    def _compute_certainty_heuristic(self, answer_text: str) -> float:
        """
        Detects hedging language in the answer text.
        More hedging → lower certainty score.
        Strong assertions → higher certainty score.
        """
        if not answer_text:
            return 70.0

        text_lower = answer_text.lower()
        word_count = len(text_lower.split())

        if word_count == 0:
            return 70.0

        hedge_count = sum(1 for phrase in HEDGING_WORDS if phrase in text_lower)
        strong_count = sum(1 for phrase in STRONG_ASSERTION_WORDS if phrase in text_lower)

        hedge_density = hedge_count / max(word_count / 50, 1)
        strong_density = strong_count / max(word_count / 50, 1)

        certainty = 70.0
        certainty -= min(hedge_density * 15, 50)
        certainty += min(strong_density * 10, 25)

        apology_patterns = [
            r"i cannot", r"i can't", r"i apologize",
            r"i don't have", r"not mentioned", r"not available",
            r"no information", r"not in the document",
        ]
        for pattern in apology_patterns:
            if re.search(pattern, text_lower):
                certainty -= 12

        return max(5, min(100, certainty))

    # ── Helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _get_bigrams(text: str) -> set:
        words = re.findall(r'\b[a-z]{3,}\b', text)
        return {(words[i], words[i + 1]) for i in range(len(words) - 1)} if len(words) >= 2 else set()

    @staticmethod
    def _generate_explanation(retrieval: float, grounding: float, overlap: float, certainty: float, score: int) -> str:
        parts = []
        if retrieval >= 70:
            parts.append("strong retrieval match")
        elif retrieval >= 40:
            parts.append("moderate retrieval match")
        else:
            parts.append("weak retrieval match")

        if grounding >= 60:
            parts.append("well-grounded in sources")
        elif grounding < 30:
            parts.append("limited source grounding")

        if overlap < 25:
            parts.append("low query-context overlap")

        if certainty < 40:
            parts.append("hedging language detected")

        return "; ".join(parts[:3]) if parts else "Score based on multi-factor analysis."

    @staticmethod
    def _score_to_level(score: int) -> str:
        if score >= 85:
            return "Very High"
        if score >= 65:
            return "High"
        if score >= 45:
            return "Moderate"
        if score >= 25:
            return "Low"
        return "Very Low"

    # ── Legacy compatibility (fallback) ──────────────────────────────────────

    def _criteria_based_scoring(
        self,
        user_question: str,
        intent: str,
        domain: str,
        context_chunks: list[str],
        has_sources: bool = True,
    ) -> dict:
        """Legacy fallback — redirects to the new deterministic scorer."""
        return self.score_confidence(
            user_question=user_question,
            intent=intent,
            domain=domain,
            context_chunks=context_chunks,
            has_sources=has_sources,
        )
