import os
import json
import atexit
import chromadb
import re
from dotenv import load_dotenv
from tenacity import retry, retry_if_exception_type, wait_exponential, stop_after_attempt
from concurrent.futures import ThreadPoolExecutor
from rank_bm25 import BM25Okapi
from src.topic_segmenter import TopicSegmenter
from src.text_preprocessor import clean_text
from src.intent_classifier import IntentClassifier
from src.prompt_templates import get_prompt_for_intent
from src.research_engine import ResearchEngine
from src.config import CHROMA_DB_PATH, DEFAULT_TOP_K, THREAD_POOL_MAX_WORKERS, RETRIEVAL_TIMEOUT, CHAT_HISTORY_CONTEXT_SIZE, QA_MAX_TOKENS, QA_TEMPERATURE
from src.llm_client import get_llm_client
from src.confidence_scorer import ConfidenceScorer
from src.logging_utils import get_logger

load_dotenv(override=True)

# Get logger - this ensures logging is configured
logger = get_logger(__name__)


def sanitize_user_input(text: str, max_length: int = 500) -> str:
    """Sanitize user input to prevent prompt injection attacks.
    
    Args:
        text: Raw user input
        max_length: Maximum allowed length
        
    Returns:
        Sanitized text safe for LLM consumption
    """
    if not text:
        return ""
    
    # Limit length to prevent buffer overflow attacks
    text = text[:max_length]
    
    # Remove null bytes and other control characters
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    
    # Remove common prompt injection patterns
    injection_patterns = [
        r'\bignore\s+(previous|all|above)\s+(instructions?|commands?|rules?)\b',
        r'\b(disregard|forget|ignore)\s+your\s+(system|instructions?)\b',
        r'\byou\s+are\s+(now|actually)\s+(a|an)\s+',
        r'<\s*script[^>]*>',
        r'javascript:',
        r'on\w+\s*=',  # event handlers like onclick=
    ]
    
    for pattern in injection_patterns:
        text = re.sub(pattern, '[FILTERED]', text, flags=re.IGNORECASE)
    
    # Escape potential prompt manipulation characters
    text = text.replace('\u200b', '').replace('\u200c', '').replace('\u200d', '')  # Zero-width chars
    
    return text.strip()


class QAEngine:
    def __init__(self):
        llm_client = get_llm_client()
        if not llm_client.is_available():
            raise ValueError("OPENROUTER_API_KEY not found in environment variables.")
        
        self.client = llm_client.client
        self.llm_client = llm_client  # Use the full client for helper methods
        self.model = llm_client.trinity_model  # Use Nemotron 3 - reasoning for Q&A

        self.chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        self.collection = self.chroma_client.get_or_create_collection(name="active_session")
        self.segmenter = TopicSegmenter()
        self.intent_classifier = IntentClassifier()
        self.research_engine = ResearchEngine()
        self.confidence_scorer = ConfidenceScorer(self.llm_client)

        self._bm25_corpus = []
        self._bm25_docs = []
        self._bm25_metas = []
        self._bm25_index = None
        self._available_topics = []
        # Use list instead of set for serialization compatibility
        self._session_stats = {"questions_asked": 0, "topics_accessed": [], "sources_used": []}
        # Internal sets for deduplication tracking during session
        self._session_stats_topics = set()
        self._session_stats_sources = set()
        self._executor = ThreadPoolExecutor(max_workers=THREAD_POOL_MAX_WORKERS)
        
        # Register cleanup handler
        atexit.register(self._cleanup)
    
    def _cleanup(self):
        """Clean up resources on application exit."""
        if hasattr(self, '_executor') and self._executor is not None:
            self._executor.shutdown(wait=True)
            logger.info("ThreadPoolExecutor shutdown complete")

    def ingest_and_segment(self, documents_dict, progress_callback=None):
        try:
            self.chroma_client.delete_collection(name="active_session")
        except Exception:
            pass

        self.collection = self.chroma_client.create_collection(name="active_session")
        self._bm25_corpus = []
        self._bm25_docs = []
        self._bm25_metas = []
        self._available_topics = []
        # Use list instead of set for serialization compatibility
        self._session_stats = {"questions_asked": 0, "topics_accessed": [], "sources_used": []}
        # Reset internal sets for deduplication tracking
        self._session_stats_topics = set()
        self._session_stats_sources = set()

        for filename, raw_content in documents_dict.items():
            cleaned_content = clean_text(raw_content)
            topics = self.segmenter.segment(cleaned_content)

            for i, topic_data in enumerate(topics):
                doc_id = f"{filename}_{topic_data['topic_id']}"
                meta = {"source_file": filename, "topic": topic_data["title"]}

                self.collection.add(
                    documents=[topic_data["content"]],
                    metadatas=[meta],
                    ids=[doc_id]
                )

                self._bm25_corpus.append(topic_data["content"].lower().split())
                self._bm25_docs.append(topic_data["content"])
                self._bm25_metas.append(meta)
                self._available_topics.append(topic_data["title"])

                if progress_callback:
                    progress_callback(filename, i + 1, len(topics), topic_data["title"])

        if self._bm25_corpus:
            self._bm25_index = BM25Okapi(self._bm25_corpus)

    def _hybrid_retrieve(self, query: str, n_results: int = DEFAULT_TOP_K) -> list:
        """
        Perform hybrid retrieval combining semantic (ChromaDB) and keyword (BM25) search.
        Weights: 70% semantic, 30% BM25
        """
        logger.info(f"Starting hybrid retrieval for query: {query[:50]}...")
        
        semantic_results = self.collection.query(query_texts=[query], n_results=n_results)
        # Defensive null checks to prevent KeyError
        semantic_docs = semantic_results.get('documents', [[]])[0] if semantic_results.get('documents') else []
        semantic_metas = semantic_results.get('metadatas', [[]])[0] if semantic_results.get('metadatas') else []
        semantic_distances = semantic_results.get('distances', [[]])[0] if semantic_results.get('distances') else []

        logger.info(f"Semantic search returned {len(semantic_docs)} results")

        seen = set()
        combined = []

        for doc, meta, dist in zip(semantic_docs, semantic_metas, semantic_distances):
            key = doc[:100]
            if key not in seen:
                seen.add(key)
                relevance = max(0, 1 - dist) if dist else 0.5
                combined.append({"doc": doc, "meta": meta, "score": relevance * 0.7})

        if self._bm25_index:
            tokenized_query = query.lower().split()
            bm25_scores = self._bm25_index.get_scores(tokenized_query)
            max_bm25 = max(bm25_scores) if max(bm25_scores) > 0 else 1
            top_bm25_indices = sorted(range(len(bm25_scores)), key=lambda i: bm25_scores[i], reverse=True)[:n_results]

            logger.info(f"BM25 search returned {sum(1 for s in bm25_scores if s > 0)} non-zero scores")

            for idx in top_bm25_indices:
                if bm25_scores[idx] > 0:
                    key = self._bm25_docs[idx][:100]
                    norm_score = (bm25_scores[idx] / max_bm25) * 0.3
                    if key not in seen:
                        seen.add(key)
                        combined.append({
                            "doc": self._bm25_docs[idx],
                            "meta": self._bm25_metas[idx],
                            "score": norm_score
                        })
                    else:
                        for item in combined:
                            if item["doc"][:100] == key:
                                item["score"] += norm_score
                                break

        combined.sort(key=lambda x: x["score"], reverse=True)
        return combined[:n_results]

    def get_all_chunks(self):
        try:
            all_data = self.collection.get()
            return all_data.get("documents", []), all_data.get("metadatas", [])
        except Exception:
            return [], []

    def get_session_stats(self):
        return {
            "questions_asked": self._session_stats["questions_asked"],
            "topics_accessed": len(self._session_stats["topics_accessed"]),
            "sources_used": len(self._session_stats["sources_used"]),
            "total_topics": len(self._available_topics),
        }

    def get_available_topics(self):
        return list(set(self._available_topics))

    def _classify_intent(self, question):
        return self.intent_classifier.classify(question, self._available_topics)

    def _retrieve_context(self, question):
        # Use hybrid retrieval to find the most relevant chunks instead of returning everything
        # Increased n_results from 10 to 20 for broader document coverage
        return self._hybrid_retrieve(question, n_results=20)

    def get_answer_stream(self, question, chat_history, metadata=None):
        # Sanitize user input to prevent prompt injection
        question = sanitize_user_input(question)
        
        if not question:
            yield {"type": "done", "content": "Your question appears to be empty or invalid.", "reasoning": None}
            return
            
        intent_future = self._executor.submit(self._classify_intent, question)
        retrieval_future = self._executor.submit(self._retrieve_context, question)

        try:
            intent_result = intent_future.result(timeout=RETRIEVAL_TIMEOUT)
        except Exception:
            intent_result = {"intent": "document_qa", "emoji": "📄", "label": "Document Q&A"}
            
        try:
            retrieved = retrieval_future.result(timeout=RETRIEVAL_TIMEOUT)
        except Exception:
            retrieved = []
            
        intent = intent_result["intent"]

        self._session_stats["questions_asked"] += 1

        source_citations = []
        context_blocks = []
        for item in retrieved:
            topic = item["meta"].get("topic", "")
            source = item["meta"].get("source_file", "")
            # Use internal sets for deduplication, then convert to list for stats
            if topic and topic not in self._session_stats_topics:
                self._session_stats_topics.add(topic)
                self._session_stats["topics_accessed"].append(topic)
            if source and source not in self._session_stats_sources:
                self._session_stats_sources.add(source)
                self._session_stats["sources_used"].append(source)
            context_blocks.append(f"SOURCE: {item['meta']['source_file']} | TOPIC: {item['meta']['topic']}\n{item['doc']}")
            source_citations.append({
                "file": item["meta"]["source_file"],
                "topic": item["meta"]["topic"],
                "score": round(item["score"], 3),
                "preview": item["doc"][:200] + "..."
            })
        context = "\n\n".join(context_blocks)

        from src.prompt_templates import DOMAIN_PROMPTS
        detected_domains = []
        combined_text = f"{question} {context}".lower()
        for domain in DOMAIN_PROMPTS.keys():
            if domain.lower() in combined_text:
                detected_domains.append(domain)

        # Score confidence (deterministic — no API call needed)
        confidence_result = self.confidence_scorer.score_confidence(
            user_question=question,
            intent=intent,
            domain=detected_domains[0] if detected_domains else "General",
            context_chunks=[item['doc'] for item in retrieved],
            retrieval_scores=[item['score'] for item in retrieved],
            has_sources=len(retrieved) > 0,
        )

        system_prompt = get_prompt_for_intent(intent, detected_domains=detected_domains)
        
        # Inject metadata if it's the IEEE intent
        if intent == "ieee_paper_gen" and metadata:
            meta_str = json.dumps(metadata, indent=2)
            system_prompt = system_prompt.replace("{metadata}", meta_str)
        elif "{metadata}" in system_prompt:
            system_prompt = system_prompt.replace("{metadata}", "N/A - Information not provided by user.")

        messages = [{"role": "system", "content": f"{system_prompt}\n\nDOCUMENT CONTEXT:\n{context}"}]

        for msg in chat_history[-CHAT_HISTORY_CONTEXT_SIZE:]:
            m = {"role": msg["role"], "content": msg["content"]}
            if "reasoning_details" in msg and msg["reasoning_details"]:
                m["reasoning_details"] = msg["reasoning_details"]
            messages.append(m)

        messages.append({"role": "user", "content": question})

        try:
            @retry(
                retry=retry_if_exception_type(Exception),
                wait=wait_exponential(multiplier=2, min=2, max=10),
                stop=stop_after_attempt(3),
                reraise=True
            )
            def _create_stream():
                sys_inst, contents = self.llm_client._convert_messages(messages)
                from google.genai import types
                config = types.GenerateContentConfig(
                    system_instruction=sys_inst,
                    max_output_tokens=QA_MAX_TOKENS,
                    temperature=QA_TEMPERATURE
                )
                return self.client.models.generate_content_stream(
                    model=self.model,
                    contents=contents,
                    config=config
                )
            
            stream = _create_stream()

            yield {"type": "meta", "intent": intent_result, "sources": source_citations[:5], "confidence": confidence_result}

            full_content = ""
            full_reasoning = ""
            for chunk in stream:
                try:
                    if chunk.text:
                        token = chunk.text
                        full_content += token
                        yield {"type": "token", "token": token}
                except Exception:
                    pass

            # Finalize reasoning and content
            if full_reasoning:
                reasoning = full_reasoning
                content = full_content
            elif "<think>" in full_content and "</think>" in full_content:
                start = full_content.find("<think>") + 7
                end = full_content.find("</think>")
                reasoning = full_content[start:end].strip()
                content = full_content[end + 8:].strip()
            else:
                content = full_content
                reasoning = None

            # Re-score confidence with the actual answer text (grounding + certainty)
            confidence_result = self.confidence_scorer.update_with_answer(
                confidence_result, content, [item['doc'] for item in retrieved]
            )

            yield {"type": "confidence_update", "confidence": confidence_result}
            yield {"type": "done", "content": content, "reasoning": reasoning}

        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg:
                if "daily" in error_msg.lower() or "quota" in error_msg.lower():
                    user_msg = "🛑 **Daily Free Quota Exhausted**\n\nYou've reached the OpenRouter daily limit for free models (50 requests). \n\n**Solutions**:\n1. Wait 24 hours for reset.\n2. [Add credits ($5)](https://openrouter.ai/settings/credits) to increase limit to 1,000+ requests/day.\n3. Try a different free model in `.env`."
                else:
                    user_msg = "⏳ **Model is Busy (Rate Limit)**\n\nThe free model is currently receiving too many requests. \n\n**To Fix**: Wait 10-20 seconds and try again, or [add credits](https://openrouter.ai/settings/credits) for priority access."
            elif "500" in error_msg:
                user_msg = "🛠️ **Model Provider Error (500)**\n\nThe model provider is experiencing temporary issues. \n\n**To Fix**: Please try again in 30-60 seconds. If it persists, the model may be undergoing maintenance."
            else:
                user_msg = f"An error occurred while generating the response. Please try again.\n\n*Details: {error_msg[:200]}*"
            
            yield {"type": "meta", "intent": intent_result, "sources": [], "confidence": confidence_result}
            yield {"type": "done", "content": user_msg, "reasoning": None}

    def get_answer(self, question, chat_history, metadata=None):
        """
        Get answer for a question using RAG pipeline.
        Includes error handling with logging for intent classification and retrieval.
        """
        # Sanitize user input to prevent prompt injection
        question = sanitize_user_input(question)
        
        if not question:
            return {"answer": "Your question appears to be empty or invalid.", "sources": [], "intent": None}
        
        logger.info(f"Processing question: {question[:50]}...")
        
        intent_future = self._executor.submit(self._classify_intent, question)
        retrieval_future = self._executor.submit(self._retrieve_context, question)

        try:
            intent_result = intent_future.result(timeout=RETRIEVAL_TIMEOUT)
            logger.info(f"Intent classified: {intent_result.get('intent', 'unknown')}")
        except TimeoutError as e:
            logger.warning(f"Intent classification timed out: {e}. Using fallback.")
            intent_result = {"intent": "document_qa", "emoji": "📄", "label": "Document Q&A"}
        except Exception as e:
            logger.error(f"Intent classification failed: {e}. Using fallback.")
            intent_result = {"intent": "document_qa", "emoji": "📄", "label": "Document Q&A"}
            
        try:
            retrieved = retrieval_future.result(timeout=RETRIEVAL_TIMEOUT)
            logger.info(f"Retrieval completed: {len(retrieved)} chunks retrieved")
        except TimeoutError as e:
            logger.warning(f"Context retrieval timed out: {e}. Using empty context.")
            retrieved = []
        except Exception as e:
            logger.error(f"Context retrieval failed: {e}. Using empty context.")
            retrieved = []
            
        intent = intent_result["intent"]

        self._session_stats["questions_asked"] += 1

        source_citations = []
        context_blocks = []
        for item in retrieved:
            topic = item["meta"].get("topic", "")
            source = item["meta"].get("source_file", "")
            # Use internal sets for deduplication, then convert to list for stats
            if topic and topic not in self._session_stats_topics:
                self._session_stats_topics.add(topic)
                self._session_stats["topics_accessed"].append(topic)
            if source and source not in self._session_stats_sources:
                self._session_stats_sources.add(source)
                self._session_stats["sources_used"].append(source)
            context_blocks.append(f"SOURCE: {item['meta']['source_file']} | TOPIC: {item['meta']['topic']}\n{item['doc']}")
            source_citations.append({
                "file": item["meta"]["source_file"],
                "topic": item["meta"]["topic"],
                "score": round(item["score"], 3),
                "preview": item["doc"][:200] + "..."
            })
        context = "\n\n".join(context_blocks)

        # Detect domains BEFORE confidence scoring
        from src.prompt_templates import DOMAIN_PROMPTS
        detected_domains = []
        combined_text = f"{question} {context}".lower()
        for domain in DOMAIN_PROMPTS.keys():
            if domain.lower() in combined_text:
                detected_domains.append(domain)
        
        # Score confidence (deterministic — no API call needed)
        confidence_result = self.confidence_scorer.score_confidence(
            user_question=question,
            intent=intent,
            domain=detected_domains[0] if detected_domains else "General",
            context_chunks=[item['doc'] for item in retrieved],
            retrieval_scores=[item['score'] for item in retrieved],
            has_sources=len(retrieved) > 0,
        )

        system_prompt = get_prompt_for_intent(intent, detected_domains=detected_domains)
        
        # Inject metadata if it's the IEEE intent
        if intent == "ieee_paper_gen" and metadata:
            meta_str = json.dumps(metadata, indent=2)
            system_prompt = system_prompt.replace("{metadata}", meta_str)
        elif "{metadata}" in system_prompt:
            system_prompt = system_prompt.replace("{metadata}", "N/A - Information not provided by user.")

        messages = [{"role": "system", "content": f"{system_prompt}\n\nDOCUMENT CONTEXT:\n{context}"}]

        for msg in chat_history[-CHAT_HISTORY_CONTEXT_SIZE:]:
            m = {"role": msg["role"], "content": msg["content"]}
            if "reasoning_details" in msg and msg["reasoning_details"]:
                m["reasoning_details"] = msg["reasoning_details"]
            messages.append(m)

        messages.append({"role": "user", "content": question})

        try:
            # Use create_qa_completion which enables reasoning for Nemotron 3 model
            response = self.llm_client.create_qa_completion(
                messages=messages,
                max_tokens=QA_MAX_TOKENS,
                temperature=QA_TEMPERATURE
            )
            msg = response.choices[0].message
            content = msg.content

            reasoning_data = getattr(msg, "reasoning", getattr(msg, "reasoning_details", None))

            if not reasoning_data and content and "<think>" in content and "</think>" in content:
                start = content.find("<think>") + 7
                end = content.find("</think>")
                reasoning_data = content[start:end].strip()
                content = content[end + 8:].strip()

            if not reasoning_data:
                reasoning_data = "Model processed logic internally (Invisible Reasoning Pipeline)."

            # Re-score confidence with the actual answer text
            confidence_result = self.confidence_scorer.update_with_answer(
                confidence_result, content, [item['doc'] for item in retrieved]
            )

            return {
                "content": content,
                "reasoning_details": reasoning_data,
                "intent": intent_result,
                "sources": source_citations[:5],
                "confidence": confidence_result,
            }
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg:
                if "daily" in error_msg.lower() or "quota" in error_msg.lower():
                    user_msg = "🛑 **Daily Free Quota Exhausted** — You've reached the OpenRouter daily limit. Please wait 24h or [add credits](https://openrouter.ai/settings/credits) for higher limits."
                else:
                    user_msg = "⏳ **Model is Busy** — Rate limit reached for this free model. Please wait a few seconds and try again."
            else:
                user_msg = f"An error occurred while generating the response. Please try again.\n\n*Details: {error_msg[:200]}*"
            return {
                "content": user_msg,
                "reasoning_details": None,
                "intent": intent_result,
                "sources": [],
                "confidence": self.confidence_scorer.score_confidence(
                    user_question=question,
                    intent=intent_result.get("intent", "general") if isinstance(intent_result, dict) else "general",
                    domain="",
                    context_chunks=[],
                    has_sources=False,
                ),
            }
