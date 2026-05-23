import re
import json

def test_mermaid_safe_code():
    mermaid_code = 'graph TD\nA["Command, Control & Sync (C2)"] --> B["Sync & Control"]'
    # Simulation of app.py fix
    safe_code = mermaid_code.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    
    # The bug was using {mermaid_code} instead of {safe_code}
    html_output = f'<div class="mermaid">{safe_code}</div>'
    
    print("--- Mermaid Safe Code Test ---")
    print(f"Original: {mermaid_code}")
    print(f"Safe: {safe_code}")
    print(f"Output: {html_output}")
    assert "&amp;" in safe_code
    print("✅ Mermaid Safe Code Test Passed")

def test_suggestion_json_extraction():
    raw_response = """
    Based on my analysis, here are the suggestions:
    ```json
    [
        {"title": "Improve Drone Range", "description": "Increase battery capacity.", "category": "optimization"},
        {"title": "Add GPS", "description": "Include GPS module.", "category": "innovation"}
    ]
    ```
    I hope these help!
    """
    
    # Step 1: Remove common markdown code block markers
    clean_raw = raw_response
    if "```json" in raw_response:
        match = re.search(r"```json\s*(.*?)\s*```", raw_response, re.DOTALL)
        if match: clean_raw = match.group(1)
    elif "```" in raw_response:
        match = re.search(r"```\s*(.*?)\s*```", raw_response, re.DOTALL)
        if match: clean_raw = match.group(1)

    # Step 2: Extract the largest JSON array block
    json_match = re.search(r"\[.*\]", clean_raw, re.DOTALL)
    raw_json = json_match.group(0) if json_match else clean_raw
    
    print("\n--- Suggestion JSON Extraction Test ---")
    print(f"Extracted: {raw_json}")
    suggestions = json.loads(raw_json)
    assert len(suggestions) == 2
    assert suggestions[0]["title"] == "Improve Drone Range"
    print("✅ Suggestion JSON Extraction Test Passed")

def test_regex_labels():
    # Verify the regex used in app.py to find mermaid blocks
    text = """
    Here is a diagram:
    ```mermaid
    graph TD
        A["Test & Debug"] --> B["Release"]
    ```
    """
    mermaid_blocks = re.findall(r"```mermaid\s*(.*?)\s*```", text, re.DOTALL)
    print("\n--- Mermaid Regex Test ---")
    print(f"Found: {mermaid_blocks}")
    assert len(mermaid_blocks) == 1
    assert "graph TD" in mermaid_blocks[0]
    print("✅ Mermaid Regex Test Passed")

if __name__ == "__main__":
    test_mermaid_safe_code()
    test_suggestion_json_extraction()
    test_regex_labels()
