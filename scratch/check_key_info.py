"""
OpenRouter API Key & Model Connectivity Check
===============================================
Validates your API key and tests each model used by the system.
"""
import os
import sys
import json
import requests
from dotenv import load_dotenv

# Fix Windows console encoding
sys.stdout.reconfigure(encoding='utf-8')

load_dotenv(override=True)
api_key = os.getenv("OPENROUTER_API_KEY")

if not api_key:
    print("ERROR: No API key found in .env file.")
    exit(1)

print("=" * 60)
print("  OPENROUTER API KEY CHECK")
print("=" * 60)
print(f"Key:  {api_key[:15]}...{api_key[-5:]}  (length: {len(api_key)})")

headers = {
    "Authorization": f"Bearer {api_key}",
    "HTTP-Referer": "https://github.com",
    "X-Title": "ResearchHelp AI Analysis System",
    "Content-Type": "application/json",
}

# -- Step 1: Validate API Key --
try:
    resp = requests.get("https://openrouter.ai/api/v1/key", headers=headers)
    if resp.status_code == 200:
        data = resp.json().get("data", {})
        print(f"Status:      [OK] Valid")
        print(f"Free Tier:   {'Yes' if data.get('is_free_tier') else 'No'}")
        print(f"Usage Today: {data.get('usage_daily', 0)}")
        print(f"Expires:     {data.get('expires_at', 'N/A')}")
    else:
        print(f"Status:      [FAIL] Invalid (HTTP {resp.status_code})")
        print(f"Response:    {resp.text[:200]}")
        exit(1)
except Exception as e:
    print(f"Status:      [FAIL] Connection Error: {e}")
    exit(1)

# -- Step 2: Test Model Connectivity --
print("\n" + "=" * 60)
print("  MODEL CONNECTIVITY TEST")
print("=" * 60)

models_to_test = [
    ("GLM 4.5 Air (Intent/Mermaid)", "z-ai/glm-4.5-air:free", False),
    ("Nemotron 3 Super (QA/Research)", "nvidia/nemotron-3-super-120b-a12b:free", True),
    ("Nemotron Nano VL (Vision)", "nvidia/nemotron-nano-12b-v2-vl:free", False),
]

passed = 0
for name, model_id, use_reasoning in models_to_test:
    print(f"\n  Testing: {name}")
    print(f"  Model:   {model_id}")
    try:
        body = {
            "model": model_id,
            "messages": [{"role": "user", "content": "Reply with exactly: OK"}],
            "max_tokens": 10,
            "temperature": 0.0,
        }
        if use_reasoning:
            body["reasoning"] = {"enabled": True}

        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=body,
            timeout=30,
        )

        if resp.status_code == 200:
            result = resp.json()
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            print(f"  Result:  [OK] WORKING  ->  \"{content.strip()[:50]}\"")
            passed += 1
        else:
            error = resp.json().get("error", {})
            print(f"  Result:  [FAIL] HTTP {resp.status_code} -- {error.get('message', resp.text[:100])}")
    except requests.exceptions.Timeout:
        print(f"  Result:  [TIMEOUT] Model may be busy, try again")
    except Exception as e:
        print(f"  Result:  [FAIL] ERROR -- {str(e)[:100]}")

# -- Summary --
total = len(models_to_test)
pct = (passed / total) * 100 if total else 0
print("\n" + "=" * 60)
print(f"  SUMMARY: {passed}/{total} models passed ({pct:.0f}%)")
if passed == total:
    print("  ALL SYSTEMS OPERATIONAL")
elif passed > 0:
    print("  PARTIALLY OPERATIONAL")
else:
    print("  SYSTEM DOWN")
print("=" * 60 + "\n")
