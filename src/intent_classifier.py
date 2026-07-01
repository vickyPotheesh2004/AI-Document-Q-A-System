import re
import threading
from collections import OrderedDict
from dotenv import load_dotenv
from src.config import (
    INTENT_CACHE_MAX_SIZE,
    INTENT_MAX_TOKENS,
    INTENT_TEMPERATURE,
    INTENT_TIMEOUT,
    INTENT_CLASSIFIER_MODEL,
)
from src.llm_client import get_llm_client
from src.logging_utils import get_logger

load_dotenv()

# Get logger - this ensures logging is configured
logger = get_logger(__name__)

# Maximum cache size to prevent memory leaks
MAX_CACHE_SIZE = INTENT_CACHE_MAX_SIZE

# Lock for thread-safe cache operations
_cache_lock = threading.Lock()

INTENT_LABELS = {
    "document_qa": {
        "emoji": "📄",
        "label": "Document Q&A",
        "description": "Answering questions directly from document content",
    },
    "suggestion_request": {
        "emoji": "💡",
        "label": "Suggestion",
        "description": "Providing improvement suggestions for the document",
    },
    "research_addon": {
        "emoji": "🔬",
        "label": "Research Process Analysis",
        "description": "8-Domain Structured Research Methodology",
    },
    "research_analysis": {
        "emoji": "🧪",
        "label": "Deep Analysis (Simple)",
        "description": "Simple English Deep Analysis across 40+ Research Domains",
    },
    "ieee_paper_gen": {
        "emoji": "📄",
        "label": "IEEE Paper Generator",
        "description": "Generate an official format technical paper based on analysis",
    },
    "off_topic": {
        "emoji": "🚫",
        "label": "Off-Topic",
        "description": "Query unrelated to uploaded documents",
    },
}

SUGGESTION_KEYWORDS = re.compile(
    r"\b(suggest|improve|improvement|enhance|better|upgrade|optimize|innovation|recommend|advice|critique|weakness|gap|missing)\b",
    re.IGNORECASE,
)
RESEARCH_KEYWORDS = re.compile(
    r"\b(add|integrate|implement|can we|could we|what if|propose|feasib|extend|attach|include|incorporate|build)\b",
    re.IGNORECASE,
)
OFF_TOPIC_KEYWORDS = re.compile(
    r"\b(weather|joke|hello|hi there|good morning|how are you|what time|who are you|play music|tell me a story)\b",
    re.IGNORECASE,
)
RESEARCH_DOMAIN_KEYWORDS = re.compile(
    r"\b(ai|intelligence|learning|math|physic|chemist|vision|nlp|robot|iot|cyber|cloud|edge|distribut|blockchain|big data|data mining|software|hci|embedded|vlsi|signal|image|speech|wireless|5g|6g|network|optical|satellite|control|power|renewable|grid|electric|vehicle|autonomous|reality|quantum|bioinfo|biomed|smart city)\b",
    re.IGNORECASE,
)
CONTEXTUAL_MARKERS = re.compile(
    r"\b(this|that|here|document|project|system|report|file|context)\b",
    re.IGNORECASE,
)
IEEE_PAPER_KEYWORDS = re.compile(
    r"\b(ieee|official paper|academic paper|publication|manuscript|research paper|journal|conference paper)\b",
    re.IGNORECASE,
)


class IntentClassifier:
    def __init__(self):
        llm_client = get_llm_client()
        self.llm_client = llm_client
        self.model = INTENT_CLASSIFIER_MODEL  # llama3.1:8b for fast classification
        # Use OrderedDict with max size for LRU-like caching
        self._cache = OrderedDict()
        self._cache_max_size = MAX_CACHE_SIZE
        logger.info(f"IntentClassifier initialized with model: {self.model}")

    def _rule_based_classify(self, query: str):
        q = query.strip().lower()

        # Only classify as off_topic if it's very short and matches generic greetings/questions
        if len(q) < 25 and OFF_TOPIC_KEYWORDS.search(q):
            return "off_topic"

        if SUGGESTION_KEYWORDS.search(q):
            return "suggestion_request"

        if RESEARCH_KEYWORDS.search(q) and "?" in q:
            return "research_addon"

        if IEEE_PAPER_KEYWORDS.search(q):
            return "ieee_paper_gen"

        if RESEARCH_DOMAIN_KEYWORDS.search(q):
            # If it matches a research domain and HAS contextual markers (like 'this', 'project'),
            # prioritize document_qa (e.g., "What does this say about AI?").
            # But if it ONLY matches the domain, assume it's a general research query.
            if CONTEXTUAL_MARKERS.search(q):
                return "document_qa"
            return "research_analysis"

        # If it has contextual markers but no other specific intent keywords, it's document QA
        if CONTEXTUAL_MARKERS.search(q):
            return "document_qa"

        # If it doesn't match any specific 'off_topic' or other intent,
        # let it fall through to LLM for a more nuanced check,
        # rather than aggressively classifying.
        return None

    def classify(self, query: str, available_topics: list = None) -> dict:
        cache_key = query.strip().lower()[:100]
        
        # Thread-safe cache access
        with _cache_lock:
            if cache_key in self._cache:
                # Move to end (most recently used)
                self._cache.move_to_end(cache_key)
                return self._cache[cache_key]

            # Evict oldest entries if cache is full
            while len(self._cache) >= self._cache_max_size:
                self._cache.popitem(last=False)

        fast_result = self._rule_based_classify(query)
        if fast_result:
            result = {"intent": fast_result, **INTENT_LABELS[fast_result]}
            with _cache_lock:
                self._cache[cache_key] = result
            return result

        # Strict system prompt - ensure only direct document questions are document_qa
        system_prompt = (
            "You are an Intent Classifier for a Document Q&A system. "
            "Classify the user's query into the most appropriate category.\n\n"
            "Categories:\n"
            "document_qa: Specific questions about the document content. "
            "suggestion_request: Asking for ways to improve or expand the document/project.\n"
            "research_analysis: Deep analysis on specialized research domains.\n"
            "ieee_paper_gen: Generate a full IEEE-style research paper.\n"
            "research_addon: Proposing new features or technical additions.\n"
            "off_topic: Queries completely unrelated to research, projects, or any academic/technical discussion. "
            "Examples: Personal jokes, current weather, pop culture trivia, random chatter.\n\n"
            f"Available Document Topics: {', '.join(available_topics[:30]) if available_topics else 'None listed'}\n\n"
            "If the query is technically related or could be a general research question, prioritize 'document_qa' or 'research_analysis'.\n"
            "Reply ONLY with the category name (e.g., 'document_qa', 'research_analysis', or 'off_topic')."
        )

        try:
            # Use create_fast_completion for GLM 4.5 Air - fastest model for simple classification
            response = self.llm_client.create_fast_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query},
                ],
                max_tokens=INTENT_MAX_TOKENS,
                temperature=INTENT_TEMPERATURE
            )
            raw = response.choices[0].message.content.strip().lower()
            
            # Clean response
            clean_raw = re.sub(r'[^a-z_]', '', raw)

            if "off_topic" in clean_raw:
                result = {"intent": "off_topic", **INTENT_LABELS["off_topic"]}
            elif "document_qa" in clean_raw:
                result = {"intent": "document_qa", **INTENT_LABELS["document_qa"]}
            else:
                # Map to closest matching category
                for key in INTENT_LABELS:
                    if key in clean_raw:
                        result = {"intent": key, **INTENT_LABELS[key]}
                        break
                else:
                    # Default to document_qa if ambiguous/hallucinated (safer than off_topic)
                    result = {"intent": "document_qa", **INTENT_LABELS["document_qa"]}

            with _cache_lock:
                self._cache[cache_key] = result
            return result

        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg:
                logger.warning(f"Intent classification rate limited (429). Falling back to basic document QA.")
            else:
                logger.error(f"Intent classification LLM call failed: {error_msg}")
            
            result = {"intent": "document_qa", **INTENT_LABELS["document_qa"]} # Default to document_qa on failure
            with _cache_lock:
                self._cache[cache_key] = result
            return result
