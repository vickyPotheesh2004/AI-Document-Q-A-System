import os
from google import genai
from google.genai import types

# Test script for google-genai SDK
def main():
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY", "dummy"))
    
    # Check if we can construct messages in OpenAI-ish format or dicts
    messages = [
        {"role": "user", "parts": [{"text": "Hello"}]}
    ]
    print("Messages format:", messages)
    print("SDK version:", genai.__version__)

if __name__ == "__main__":
    main()
