import json

def test_json_parsing(raw):
    print(f"Testing raw input: {raw[:50]}...")
    start_idx = raw.find("[")
    end_idx = raw.rfind("]")
    
    if start_idx != -1 and end_idx != -1:
        extracted = raw[start_idx : end_idx + 1]
        print(f"Extracted: {extracted[:50]}...")
        try:
            parsed = json.loads(extracted)
            print("Successfully parsed JSON!")
            return parsed
        except Exception as e:
            print(f"Failed to parse: {e}")
            return None
    else:
        print("No brackets found")
        return None

# Case 1: Standard JSON
test_json_parsing('[{"title": "Test"}]')

# Case 2: Reasoning mode prepended (Current Bug)
test_json_parsing('> [Reasoning Mode]\n\n[{"title": "Test"}]')

# Case 3: Proper extraction logic fix
def robust_json_parsing(raw):
    print(f"\nRobust parsing raw input: {raw[:50]}...")
    
    # Skip the "Reasoning Mode" tag if it exists at the start
    if raw.startswith("> [Reasoning Mode]"):
        json_search_start = raw.find("\n\n")
        if json_search_start != -1:
            raw_to_search = raw[json_search_start:]
        else:
            raw_to_search = raw[18:] # Length of "> [Reasoning Mode]"
    else:
        raw_to_search = raw

    start_idx = raw_to_search.find("[")
    end_idx = raw_to_search.rfind("]")
    
    if start_idx != -1 and end_idx != -1:
        extracted = raw_to_search[start_idx : end_idx + 1]
        print(f"Extracted: {extracted[:50]}...")
        try:
            parsed = json.loads(extracted)
            print("Successfully parsed JSON!")
            return parsed
        except Exception as e:
            print(f"Failed to parse: {e}")
            return None
    return None

robust_json_parsing('> [Reasoning Mode]\n\n[{"title": "Test"}]')
