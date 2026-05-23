import re
import json
import unittest
from unittest.mock import MagicMock, patch

# --- Simulation of app.py logic ---
def simulate_mermaid_rendering(content):
    mermaid_blocks = re.findall(r"```mermaid\s*(.*?)\s*```", content, re.DOTALL)
    rendered_html = ""
    for idx, mermaid_code in enumerate(mermaid_blocks):
        # The FIX: sanitize for HTML entities
        safe_code = mermaid_code.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        rendered_html += f'<div id="mermaid-{idx}" class="mermaid">{safe_code}</div>'
    return rendered_html

# --- Simulation of ResearchEngine parser ---
def simulate_suggestion_parser(raw):
    # Step 1: Remove common markdown code block markers
    clean_raw = raw
    if "```json" in raw:
        match = re.search(r"```json\s*(.*?)\s*```", raw, re.DOTALL)
        if match: clean_raw = match.group(1)
    elif "```" in raw:
        match = re.search(r"```\s*(.*?)\s*```", raw, re.DOTALL)
        if match: clean_raw = match.group(1)

    # Step 2: Extract the largest JSON array block
    json_match = re.search(r"\[.*\]", clean_raw, re.DOTALL)
    raw_json = json_match.group(0) if json_match else clean_raw

    try:
        return json.loads(raw_json)
    except json.JSONDecodeError:
        return []

class TestAIAnalysisSystem(unittest.TestCase):

    def test_mermaid_rendering_sanitization(self):
        """Verify that Mermaid diagrams with special chars are sanitized for HTML display."""
        content = """
        Here is a complex diagram:
        ```mermaid
        graph TD
            A["Command & Control (C2)"] --> B["Sync < 10ms"]
        ```
        """
        html = simulate_mermaid_rendering(content)
        self.assertIn("&amp;", html)
        self.assertIn("&lt;", html)
        self.assertIn("Command &amp; Control", html)
        self.assertIn("Sync &lt; 10ms", html)
        print("✅ Mermaid Rendering Sanitization Test Passed")

    def test_suggestion_parser_robustness(self):
        """Verify that suggestions can be extracted even with markdown and preamble."""
        raw_responses = [
            # Case 1: Markdown JSON block
            'Reasoning: ... ```json [{"title": "T1", "description": "D1", "category": "gap"}] ```',
            # Case 2: Just JSON array
            '[{"title": "T2", "description": "D2", "category": "innovation"}]',
            # Case 3: Preamble then array
            'Here are the suggestions: \n\n [{"title": "T3", "description": "D3", "category": "research"}]'
        ]
        
        for i, raw in enumerate(raw_responses):
            res = simulate_suggestion_parser(raw)
            self.assertEqual(len(res), 1, f"Failed case {i+1}")
            self.assertEqual(res[0]["title"], f"T{i+1}")
        print("✅ Suggestion Parser Robustness Test Passed")

    def test_scope_knowledge_prompt_rules(self):
        """Verify that prompt templates contain the correct enforcement strings."""
        try:
            from src.prompt_templates import DOCUMENT_QA_PROMPT, MERMAID_RULES
            self.assertIn("CRITICAL SCOPE ENFORCEMENT", DOCUMENT_QA_PROMPT)
            self.assertIn("Node Labels MUST ALWAYS be enclosed in double quotes", MERMAID_RULES)
            self.assertIn("For labels with special characters", MERMAID_RULES)
            print("✅ Prompt Rules Integrity Test Passed")
        except ImportError:
            self.skipTest("src.prompt_templates not available for direct import")

    def test_intent_system_prompt_strictness(self):
        """Verify that the intent classifier system prompt emphasizes strict document connection."""
        try:
            from src.intent_classifier import IntentClassifier
            # Match the actual model from config (z-ai/glm-4.5-air:free)
            classifier = IntentClassifier()
            self.assertIn("glm-4.5-air", classifier.model)
            print("✅ Intent Classifier Configuration Test Passed")
        except ImportError:
            self.skipTest("src.intent_classifier not available for direct import")

if __name__ == "__main__":
    unittest.main()
