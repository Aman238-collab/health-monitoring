import os
import json
import logging
import google.generativeai as genai
# from dotenv import load_dotenv

# load_dotenv() # handled in main usually, but good for standalone testing

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    logger.warning("GEMINI_API_KEY not found in environment variables.")

# Validation schemas could be Pydantic, but for now we'll do manual JSON check or simple Pydantic model usage if needed.
# The user asked for STRICT JSON.

from .prompts import get_system_prompt

def process_prescription_text(raw_text: str, patient_id: str, timezone: str = "UTC") -> dict:
    """
    Sends text to Gemini and returns structured data.
    """
    model = genai.GenerativeModel("gemini-1.5-flash") # or gemini-pro
    
    prompt = f"""
    Context:
    Patient ID: {patient_id}
    Timezone: {timezone}

    Raw OCR Text:
    {raw_text}

    Extract the data as per the system instructions.
    """
    
    system_instruction = get_system_prompt()
    
    # Retry logic (simple loop)
    max_retries = 2
    for attempt in range(max_retries):
        try:
            # Gemini Python SDK doesn't always support system_instruction directly in all versions/models identically, 
            # but usually we can prepend it or use the system_instruction arg if available.
            # For safety with 1.5-flash/pro, we can put it in the prompt or use the config.
            # We'll prepend it to the prompt here for wide compatibility or use generation_config.
            
            
            logger.info(f"Calling Gemini API. Attempt {attempt+1}/{max_retries}")
            response = model.generate_content(
                f"{system_instruction}\n\n{prompt}",
                generation_config={"response_mime_type": "application/json"}
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
