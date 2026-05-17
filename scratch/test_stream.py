"""Quick test of the streaming path with proper headers/reasoning."""
import os
import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(override=True)

from src.llm_client import get_llm_client
from src.config import REASONING_MODELS

client = get_llm_client()
model = client.trinity_model

print(f"Model: {model}")
print(f"Is reasoning model: {model in REASONING_MODELS}")

extra_headers = {
    "HTTP-Referer": os.getenv("OPENROUTER_SITE_URL", "https://github.com"),
    "X-Title": os.getenv("OPENROUTER_SITE_TITLE", "ResearchHelp AI Analysis System"),
}
extra_body = {}
if model in REASONING_MODELS:
    extra_body["reasoning"] = {"enabled": True}

print("Testing streaming call...")
try:
    stream = client.client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": "Say hello in one word."}],
        max_tokens=20,
        temperature=0.0,
        stream=True,
        extra_headers=extra_headers,
        extra_body=extra_body if extra_body else None,
    )
    
    full = ""
    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            full += chunk.choices[0].delta.content
    
    print(f"Stream result: \"{full.strip()}\"")
    print("[OK] Streaming works!")
except Exception as e:
    print(f"[FAIL] Streaming error: {e}")
