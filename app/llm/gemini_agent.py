import os
import json
import logging
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY:
    # Initialize client (v2 SDK style)
    client = genai.Client(api_key=GEMINI_API_KEY)
else:
    logger.warning("GEMINI_API_KEY not found in environment variables.")

from .prompts import get_system_prompt

def process_prescription_text(raw_text: str, patient_id: str, timezone: str = "UTC") -> dict:
    """
    Sends text to Gemini and returns structured data using the new google-genai SDK.
    """
    
    prompt = f"""
    Context:
    Patient ID: {patient_id}
    Timezone: {timezone}

    Raw OCR Text:
    {raw_text}

    Extract the data as per the system instructions.
    """
    
    system_instruction = get_system_prompt()
    
    # Retry logic
    max_retries = 2
    for attempt in range(max_retries):
        try:
            logger.info(f"Calling Gemini API (v2). Attempt {attempt+1}/{max_retries}")
            
            # Using models.generate_content from the new SDK
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json"
                )
            )
            
            logger.info("Gemini response received.")
            
            response_text = response.text
            # Clean up potential markdown formatting if model ignores "NO MARKDOWN"
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            
            data = json.loads(response_text)
            
            # Simple validation: check keys
            if "medications" in data and "notifications" in data:
                return data
            else:
                logger.error(f"Attempt {attempt+1}: Invalid JSON structure. Missing keys.")
                continue

        except json.JSONDecodeError:
            logger.error(f"Attempt {attempt+1}: Failed to decode JSON.")
        except Exception as e:
            logger.error(f"Attempt {attempt+1}: Gemini error: {e}")
            
    raise ValueError("Failed to process prescription text after retries.")
