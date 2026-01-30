import re
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# --- Regex Constants ---
# Captures dosage like 500mg, 5 ml, 1 tablet, etc.
DOSAGE_REGEX = re.compile(r'(\d+(?:\.\d+)?)\s?(mg|ml|mcg|g|tablet|tab|capsule|cap|pills?|units?|iu)', re.IGNORECASE)

# Captures frequencies like 1-0-1, OD, BD, TDS, etc.
FREQ_REGEX_NUMERIC = re.compile(r'\b([0-1]-[0-1]-[0-1](?:-[0-1])?)\b')
FREQ_REGEX_TEXT = re.compile(r'\b(OD|BD|BID|TDS|TID|QID|Q4H|Q6H|SOS|HS|once daily|twice daily|thrice daily)\b', re.IGNORECASE)

# Captures instructions
INSTRUCTION_REGEX = re.compile(r'\b(after\s?food|before\s?food|empty\s?stomach|with\s?food|at\s?night)\b', re.IGNORECASE)

# Standardized Times Mapping
FREQUENCY_MAP = {
    "OD": ["08:00"],                   # Once Daily - Morning
    "ONCE DAILY": ["08:00"],
    "BD": ["08:00", "20:00"],          # Twice Daily - Morning, Night
    "BID": ["08:00", "20:00"],
    "TWICE DAILY": ["08:00", "20:00"],
    "TDS": ["08:00", "13:00", "20:00"],# Thrice Daily - Morning, Afternoon, Night
    "TID": ["08:00", "13:00", "20:00"],
    "THRICE DAILY": ["08:00", "13:00", "20:00"],
    "QID": ["08:00", "13:00", "18:00", "22:00"], # 4 times
    "HS": ["22:00"],                   # At bedtime
    "SOS": []                          # As needed - no fixed time
}

def parse_dosage(line: str):
    """Extracts dosage string from a line."""
    match = DOSAGE_REGEX.search(line)
    if match:
        return match.group(0)
    return None

def parse_frequency_and_times(line: str):
    """
    Extracts frequency (e.g. BD, 1-0-1) and maps it to standardized times.
    Returns (frequency_str, times_list)
    """
    # 1. Check Numeric patterns like 1-0-1
    num_match = FREQ_REGEX_NUMERIC.search(line)
    if num_match:
        freq = num_match.group(1)
        parts = freq.split('-')
        times = []
        # Standard mapping for 3 parts: Morning, Afternoon, Night
        # Standard mapping for 4 parts: Morning, Afternoon, Evening, Night
        
        if len(parts) == 3:
            if parts[0] != '0': times.append("08:00")
            if parts[1] != '0': times.append("13:00")
            if parts[2] != '0': times.append("20:00")
        elif len(parts) == 4: # generic fallback
             if parts[0] != '0': times.append("08:00")
             if parts[1] != '0': times.append("13:00")
             if parts[2] != '0': times.append("18:00")
             if parts[3] != '0': times.append("22:00")
        
        return freq, times

    # 2. Check Text patterns like OD, BD
    text_match = FREQ_REGEX_TEXT.search(line)
    if text_match:
        freq = text_match.group(1).upper()
        # Handle spaced variations key lookup
        if freq == "ONCE DAILY": freq = "OD"
        if freq == "TWICE DAILY": freq = "BD" 
        if freq == "THRICE DAILY": freq = "TDS"
        
        times = FREQUENCY_MAP.get(freq, [])
        return freq, times

    return None, []

def parse_instructions(line: str):
    """Extracts instructions like 'after food'."""
    match = INSTRUCTION_REGEX.search(line)
    if match:
        return match.group(1).lower()
    return None

def parse_prescription_text(text: str) -> list[dict]:
    """
    Parses raw OCR text into structured medication data using deterministic rules.
    """
    logger.info("Starting rule-based prescription parsing.")
    medicines = []
    
    lines = text.split('\n')
    logger.info(f"Total lines to process: {len(lines)}")
    
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        
        logger.info(f"Processing line {i+1}: '{line}'")
            
        # Heuristic 1: Medicine often starts with Capital letter and is not just a common keyword like 'Tablet'
        # This is a weak heuristic but fits the MVP requirement "One medicine per line"
        word_match = re.match(r'^[A-Z][a-zA-Z0-9\-]+', line)
        if not word_match:
             # Skip lines that don't look like medicine names or headers (naive check)
             continue
        
        # Stop-word check to avoid parsing headers as meds
        # Common headers in prescriptions
        if line.lower() in ["rx", "prescription", "dated", "patient", "dr.", "doctor", "diagnosis", "address"]:
            continue

        medicine_name = word_match.group(0) # Get the first Capitalized word as tentative name
        
        # Refine medicine name: sometimes it's multi-word e.g. "Vitamin C"
        # For MVP we stick to simple extraction or take everything before the dosage
        
        dosage = parse_dosage(line)
        frequency, times = parse_frequency_and_times(line)
        instructions = parse_instructions(line)
        
        # Core Requirement: A line must have at least a Name and (Dosage OR Frequency) to be confident it's a med
        # Otherwise it might be just "Patient Name: John"
        if not dosage and not frequency:
            continue
            
        # Clean up medicine name - remove dosage if attached
        if dosage and dosage in medicine_name:
            medicine_name = medicine_name.replace(dosage, "").strip()

        med_obj = {
            "medicine_name": medicine_name,
            "dosage": dosage,
            "frequency": frequency,
            "times": times, # list of "HH:MM"
            "instructions": instructions
        }
        
        medicines.append(med_obj)
        logger.info(f"Parsed medicine: {med_obj}")

    logger.info(f"Parsing complete. Found {len(medicines)} medicines.")
    return medicines
