import os
from dotenv import load_dotenv

print("Checking environment variables...")
load_dotenv()
api_key = os.getenv("OPENROUTER_API_KEY")
print(f"OPENROUTER_API_KEY found: {api_key is not None}")
if api_key:
    print(f"Key starts with: {api_key[:10]}...")
else:
    print("Key NOT found!")

from src.llm_client import get_llm_client
client = get_llm_client()
print(f"LLMClient available: {client.is_available()}")
