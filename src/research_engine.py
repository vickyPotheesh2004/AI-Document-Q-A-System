import json
import re
from dotenv import load_dotenv
from src.prompt_templates import (
    DOCUMENT_OVERVIEW_PROMPT,
    AUTO_SUGGESTIONS_PROMPT,
)
from src.config import (
    RESEARCH_OVERVIEW_MAX_TOKENS,
    RESEARCH_OVERVIEW_TEMPERATURE,
    RESEARCH_SUGGESTIONS_MAX_TOKENS,
    RESEARCH_SUGGESTIONS_TEMPERATURE,
    RESEARCH_ADDON_MAX_TOKENS,
    RESEARCH_ADDON_TEMPERATURE,
)
from src.llm_client import get_llm_client
from src.logging_utils import get_logger

load_dotenv()

# Get logger - this ensures logging is configured
logger = get_logger(__name__)


class ResearchEngine:
    def __init__(self):
        llm_client = get_llm_client()
        self.llm_client = llm_client
        self.model = llm_client.reasoning_model  # gemma3:4b for deep analysis
        logger.info(f"ResearchEngine initialized with model: {self.model}")

    def generate_document_overview(
        self, all_chunks: list, all_metadata: list
    ) -> str:
        logger.info("Generating document overview...")
        combined = []
        for doc, meta in zip(all_chunks, all_metadata):
            combined.append(
                f"[{meta.get('source_file', 'Unknown')} | {meta.get('topic', 'General')}]\n{doc}"
            )

        context = "\n\n".join(combined[:20])

        try:
            # Use create_research_completion for Nemotron 3 Super with reasoning
            response = self.llm_client.create_research_completion(
                messages=[
                    {"role": "system", "content": DOCUMENT_OVERVIEW_PROMPT},
                    {
                        "role": "user",
                        "content": f"Analyze these document segments:\n\n{context}",
                    },
                ],
                max_tokens=RESEARCH_OVERVIEW_MAX_TOKENS,
                temperature=RESEARCH_OVERVIEW_TEMPERATURE
            )
            result = response.choices[0].message.content.strip()
            logger.info(
                f"Document overview generated successfully ({len(result)} chars)"
            )
            return result
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Failed to generate document overview: {error_msg}")
            return f"Could not generate overview due to an unexpected error: {error_msg}"

    def generate_auto_suggestions(
        self, all_chunks: list, all_metadata: list
    ) -> list:
        logger.info("Generating auto suggestions...")
        combined = []
        for doc, meta in zip(all_chunks, all_metadata):
            combined.append(
                f"[{meta.get('source_file', 'Unknown')} | {meta.get('topic', 'General')}]\n{doc[:300]}"
            )

        context = "\n\n".join(combined[:15])

        try:
            # Use create_research_completion for Nemotron 3 Super with reasoning
            response = self.llm_client.create_research_completion(
                messages=[
                    {"role": "system", "content": AUTO_SUGGESTIONS_PROMPT},
                    {
                        "role": "user",
                        "content": f"Document content:\n\n{context}",
                    },
                ],
                max_tokens=RESEARCH_SUGGESTIONS_MAX_TOKENS,
                temperature=RESEARCH_SUGGESTIONS_TEMPERATURE
            )
            message = response.choices[0].message
            raw = message.content.strip()

            # Step 1: Remove reasoning tags or common markdown code block markers
            # More aggressive cleaning for Nemotron reasoning blocks
            reasoning = getattr(message, "reasoning", None)
            clean_raw = re.sub(r"^>(.*?)\n\n", "", raw, flags=re.DOTALL | re.MULTILINE)
            # Remove any thinking blocks if they leaked
            clean_raw = re.sub(r"<think>.*?</think>", "", clean_raw, flags=re.DOTALL | re.IGNORECASE)
            clean_raw = clean_raw.strip()

            # Step 2: Handle markdown code blocks
            json_match = re.search(r"```json\s*(.*?)\s*```", clean_raw, re.DOTALL | re.IGNORECASE)
            if json_match:
                clean_raw = json_match.group(1)
            else:
                generic_match = re.search(r"```\s*(.*?)\s*```", clean_raw, re.DOTALL)
                if generic_match:
                    clean_raw = generic_match.group(1)

            # Step 3: Extract the first [ and last ] or { and }
            # Try to find the outermost array first
            s_arr = clean_raw.find("[")
            e_arr = clean_raw.rfind("]")
            
            # Also check for an outermost object (sometimes models wrap list in a key)
            s_obj = clean_raw.find("{")
            e_obj = clean_raw.rfind("}")

            raw_json = clean_raw
            if s_arr != -1 and e_arr != -1:
                # If there's an object wrapping the array, take the object instead
                if s_obj != -1 and s_obj < s_arr and e_obj != -1 and e_obj > e_arr:
                    raw_json = clean_raw[s_obj : e_obj + 1]
                else:
                    raw_json = clean_raw[s_arr : e_arr + 1]
            elif s_obj != -1 and e_obj != -1:
                raw_json = clean_raw[s_obj : e_obj + 1]

            suggestions = []
            try:
                parsed = json.loads(raw_json)
            except json.JSONDecodeError:
                try:
                    # Remove potential trailing commas before ] or }
                    fixed_json = re.sub(r",\s*(\]|})", r"\1", raw_json)
                    parsed = json.loads(fixed_json)
                except Exception as e:
                    logger.warning(f"Failed to parse suggestions JSON: {str(e)}")
                    # Last resort: try to find anything that looks like a list
                    return []

            # Step 4: Normalize the output
            if isinstance(parsed, dict):
                # Check for common keys like 'suggestions', 'research_suggestions', etc.
                for key in ['suggestions', 'research_suggestions', 'items', 'data']:
                    if key in parsed and isinstance(parsed[key], list):
                        suggestions = parsed[key]
                        break
                if not suggestions:
                    # Maybe it's a single suggestion?
                    suggestions = [parsed]
            elif isinstance(parsed, list):
                suggestions = parsed

            # Step 5: Validate and clean individual suggestions
            final_suggestions = []
            for item in suggestions:
                if isinstance(item, str):
                    # Convert simple string suggestions to dict format
                    final_suggestions.append({
                        "title": item[:50],
                        "description": item,
                        "category": "research"
                    })
                elif isinstance(item, dict):
                    # Handle case-insensitive keys
                    s_norm = {k.lower(): v for k, v in item.items()}
                    title = s_norm.get('title', s_norm.get('suggestion', ''))
                    desc = s_norm.get('description', s_norm.get('explanation', ''))
                    cat = s_norm.get('category', 'research')
                    
                    if title:
                        final_suggestions.append({
                            "title": title,
                            "description": desc or "No description provided.",
                            "category": cat
                        })

            if final_suggestions:
                logger.info(f"Generated {len(final_suggestions[:5])} valid suggestions")
                return final_suggestions[:5]
            
            logger.warning("No valid suggestions found after normalization")
            return []
        except Exception as e:
            error_msg = str(e)
            # Only log full traceback for unexpected errors, not simple rate limits
            if "429" in error_msg:
                logger.warning(f"Auto-suggestions skipped: Rate limit exceeded (429).")
            else:
                logger.error(f"Critical error in suggestion generation: {error_msg}", exc_info=True)
            return []

    def evaluate_addon_feasibility(self, proposal: str, context: str) -> str:
        from src.prompt_templates import RESEARCH_ADDON_PROMPT

        logger.info(f"Evaluating addon feasibility: {proposal[:30]}...")
        try:
            # Use create_research_completion for Nemotron 3 Super with reasoning
            response = self.llm_client.create_research_completion(
                messages=[
                    {
                        "role": "system",
                        "content": f"{RESEARCH_ADDON_PROMPT}\n\nDOCUMENT CONTEXT:\n{context}",
                    },
                    {"role": "user", "content": proposal},
                ],
                max_tokens=RESEARCH_ADDON_MAX_TOKENS,
                temperature=RESEARCH_ADDON_TEMPERATURE
            )
            result = response.choices[0].message.content.strip()
            logger.info("Addon feasibility evaluation completed")
            return result
        except Exception as e:
            logger.error(f"Failed to evaluate addon feasibility: {e}")
            return f"Could not evaluate proposal: {str(e)}"
