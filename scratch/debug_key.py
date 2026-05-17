import os
from dotenv import load_dotenv

load_dotenv(override=True)
key = os.getenv("OPENROUTER_API_KEY")

if key:
    print(f"Key found: {key[:10]}...{key[-5:]}")
    print(f"Key length: {len(key)}")
else:
    print("Key NOT found in environment.")
