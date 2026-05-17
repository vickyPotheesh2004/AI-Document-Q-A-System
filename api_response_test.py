import os
import sys
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.llm_client import LLMClient
from src.config import GEMINI_FLASH_MODEL
from src.logging_utils import get_logger

logger = get_logger(__name__)

def test_single_api_call():
    load_dotenv(override=True)
    
    print("=" * 60)
    print("      GEMINI API RESPONSE TEST")
    print("=" * 60)
    
    client = LLMClient()
    
    model = GEMINI_FLASH_MODEL
    prompt = "Reply with a short sentence about why AI is useful for research."
    
    print(f"Target Model: {model}")
    print("-" * 60)
    
    try:
        response = client.create_chat_completion(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100
        )
        
        content = response.choices[0].message.content
        print(f"SUCCESS! Response received:")
        print(f"\n{content}\n")
        
        # Check if reasoning was captured (for models that support it)
        if "[Reasoning Mode]" in content:
            print("Note: This model returned reasoning-only content which was automatically captured.")
            
    except Exception as e:
        print(f"FAILED! Error: {str(e)}")
    
    print("=" * 60)

if __name__ == "__main__":
    test_single_api_call()
