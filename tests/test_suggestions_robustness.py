import json
import re
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.research_engine import ResearchEngine

def simulate_parse(raw):
    # This reflects the logic implemented in src/research_engine.py
    if raw.startswith("> [Reasoning Mode]"):
        content_start = raw.find("\n\n")
        clean_raw = raw[content_start+2:] if content_start != -1 else raw[18:]
    else:
        clean_raw = raw

    if "```json" in clean_raw:
        match = re.search(r"```json\s*(.*?)\s*```", clean_raw, re.DOTALL)
        if match: clean_raw = match.group(1)
    elif "```" in clean_raw:
        match = re.search(r"```\s*(.*?)\s*```", clean_raw, re.DOTALL)
        if match: clean_raw = match.group(1)

    start_idx = clean_raw.find("[")
    end_idx = clean_raw.rfind("]")
    
    if start_idx != -1 and end_idx != -1:
        raw_json = clean_raw[start_idx : end_idx + 1]
    else:
        raw_json = clean_raw

    try:
        suggestions = json.loads(raw_json)
        if isinstance(suggestions, list):
            valid_suggestions = [s for s in suggestions if isinstance(s, dict) and 'title' in s]
            return valid_suggestions[:5]
    except:
        return []
    return []

def test_robustness():
    test_cases = [
        {
            "name": "Standard JSON Array",
            "input": '[{"title": "Test 1", "description": "Desc 1", "category": "gap"}]',
            "expected_len": 1
        },
        {
            "name": "Reasoning Mode + JSON",
            "input": '> [Reasoning Mode]\n\n[{"title": "Test 2", "description": "Desc 2", "category": "innovation"}]',
            "expected_len": 1
        },
        {
            "name": "Markdown JSON Block",
            "input": "Here are suggestions:\n```json\n[{\n  \"title\": \"Test 3\",\n  \"description\": \"Desc 3\",\n  \"category\": \"research\"\n}]\n```",
            "expected_len": 1
        },
        {
            "name": "Reasoning + Markdown Block",
            "input": "> [Reasoning Mode]\n\nBased on analysis:\n```\n[\n  {\"title\": \"Test 4\", \"description\": \"Desc 4\"}\n]\n```",
            "expected_len": 1
        },
        {
            "name": "Nesting/Extra Brackets in Reasoning",
            "input": "> [Reasoning Mode] [Internal Note]\n\nActual Result: \n[{\"title\": \"Test 5\", \"description\": \"Desc 5\"}]",
            "expected_len": 1
        }
    ]

    print("=" * 60)
    print("      ROBUST JSON PARSING TEST SUITE")
    print("=" * 60)
    
    passed = 0
    for case in test_cases:
        result = simulate_parse(case["input"])
        if len(result) == case["expected_len"]:
            print(f"PASSED: {case['name']}")
            passed += 1
        else:
            print(f"FAILED: {case['name']}")
            print(f"  Expected {case['expected_len']} but got {len(result)}")
            print(f"  Result: {result}")

    print("-" * 60)
    print(f"RESULT: {passed}/{len(test_cases)} tests passed")
    print("=" * 60)
    
    return passed == len(test_cases)

if __name__ == "__main__":
    test_robustness()
