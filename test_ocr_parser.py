import asyncio
import os
import sys
import logging

# Add project root to path if needed (though running from root usually works)
sys.path.append(os.getcwd())

from app.ocr.tesseract_service import extract_text
from app.parser.medicine_parser import parse_prescription_text
import json

# Setup simple logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
# REPLACE THIS WITH YOUR PDF FILE PATH
FILE_PATH = r"C:\Users\HP\Documents\health_monitoring\sample_prescription.pdf" 
# ---------------------

def test_ocr_and_parser(file_path):
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        logger.info("Please edit 'test_ocr_parser.py' and set FILE_PATH to a valid PDF/Image.")
        return

    logger.info(f"Processing file: {file_path}")

    try:
        # 1. Read File
        with open(file_path, "rb") as f:
            file_bytes = f.read()
        
        # 2. Extract Text (OCR)
        logger.info("Running OCR...")
        raw_text = extract_text(file_bytes)
        
        print("\n" + "="*40)
        print("RAW OCR OUTPUT")
        print("="*40)
        print(raw_text)
        print("="*40 + "\n")

        # 3. Parse Text
        logger.info("Parsing text...")
        parsed_data = parse_prescription_text(raw_text)

        print("\n" + "="*40)
        print("PARSED DATA")
        print("="*40)
        print(json.dumps(parsed_data, indent=2))
        print("="*40 + "\n")

    except Exception as e:
        logger.error(f"An error occurred: {e}", exc_info=True)

if __name__ == "__main__":
    test_ocr_and_parser(FILE_PATH)
