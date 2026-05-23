"""
API Connection Test
===================
This test verifies the Gemini API connection:
- API key validation
- Basic completion request

Usage:
    python test_api.py
"""
import os
import logging
from google import genai
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

load_dotenv(override=True)

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError(
        "CRITICAL ERROR: GEMINI_API_KEY not found. Check your .env file."
    )

logging.info("API Key loaded securely. Initializing client...")

client = genai.Client(api_key=api_key)

logging.info("Making test API call to Gemini...")

models_to_test = [
    ("Gemini Flash Preview", "gemini-3-flash-preview"),
]

total_models = len(models_to_test)
passed_models = 0

for name, model_id in models_to_test:
    logging.info(f"Testing {name} [{model_id}]...")
    try:
        response = client.models.generate_content(
            model=model_id,
            contents="Reply with exactly 'OK'",
        )

        content = response.text
        
        if content and "OK" in content.upper():
            logging.info(f"✅ {name} Status: WORKING | Score: 1/1")
            passed_models += 1
        elif content:
            logging.warning(f"⚠️ {name} Status: PARTIAL (Unexpected content) | Response: {content.strip()}")
        else:
            logging.error(f"❌ {name} Status: FAILED (No content)")

    except Exception as e:
        logging.error(f"❌ {name} Status: ERROR | Error: {str(e)[:100]}")


# FINAL SUMMARY
score_percentage = (passed_models / total_models) * 100
logging.info("\n" + "🚀" + "="*48 + "🚀")
logging.info(f"API CONNECTIVITY & SCORING SUMMARY")
logging.info(f"Total Models Tested: {total_models}")
logging.info(f"Models Passed: {passed_models}")
logging.info(f"Final System Score: {score_percentage:.1f}%")

if score_percentage == 100:
    logging.info("ALL SYSTEMS OPERATIONAL ✅✅✅")
elif score_percentage > 0:
    logging.info("SYSTEM PARTIALLY OPERATIONAL ⚠️")
else:
    logging.error("SYSTEM DOWN ❌")
logging.info("🚀" + "="*48 + "🚀\n")
