import os
from google import genai
from google.genai import types

def main():
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY", "dummy"))
    
    # Check if models has generate_content_stream
    print("Has generate_content_stream:", hasattr(client.models, 'generate_content_stream'))

if __name__ == "__main__":
    main()
