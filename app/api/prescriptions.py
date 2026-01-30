from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import Patient, Prescription, Medication, Notification
from app.ocr.tesseract_service import extract_text
from app.parser.medicine_parser import parse_prescription_text
from app.telegram.bot import send_reminder
# from app.llm.gemini_agent import process_prescription_text
import uuid
from datetime import datetime, timedelta
import logging
import os
import json
import os
router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/prescriptions/")
async def upload_prescription(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # Auto-generate Patient or use Default
    # For a personal app, we use a single default patient or lookup from env
    target_chat_id = os.getenv("TARGET_CHAT_ID")
    
    # If no chat ID in env, we might warn or use a placeholder
    if not target_chat_id:
        logger.warning("TARGET_CHAT_ID not found in .env. Telegram alerts will not work for this patient.")
        # Fallback for creating a record even if no chat ID
        target_chat_id = "1538644238" 

    # Deterministic ID based on chat ID to reuse the same record
    patient_id = f"PAT-{target_chat_id}" # Simple mapping
    
    logger.info(f"Received prescription upload. File: {file.filename}, Auto-Patient: {patient_id}")

    # 1. Handle Patient (Get or Create)
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    
    if not patient:
        patient = Patient(id=patient_id, telegram_chat_id=target_chat_id)
        db.add(patient)
        db.commit()
        db.refresh(patient)
        logger.info(f"Created new auto-patient record: {patient_id}")
    else:
        # Update chat ID if it changed in env (optional, but good for sync)
        if patient.telegram_chat_id != target_chat_id:
            patient.telegram_chat_id = target_chat_id
            db.commit()
            logger.info(f"Updated existing patient {patient_id} with new chat ID.")
    
    # If patient exists, we just use it.
    
    # 2. Check for Disease Lookup (Filename based)
    
    extracted_medications = []
    # Extract filename without extension, e.g. "Malaria" from "Malaria.pdf"
    disease_name = os.path.splitext(file.filename)[0]
    
    # Capitalize first letter to match JSON keys just in case
    disease_key = disease_name.capitalize()
    
    DISEASES_FILE = "app/data/diseases.json"
    disease_match_found = False
    
    if os.path.exists(DISEASES_FILE):
        try:
            with open(DISEASES_FILE, 'r') as f:
                diseases_data = json.load(f)
            
            if disease_key in diseases_data:
                logger.info(f"Filename '{file.filename}' matches known disease '{disease_key}'. Loading usage from registry.")
                extracted_medications = diseases_data[disease_key]
                disease_match_found = True
        except Exception as e:
            logger.error(f"Failed to load disease data: {e}")
            
    if disease_match_found:
        # Skip OCR and Parser
        text = f"[Lookup] Prescription for {disease_key}"
        logger.info("Skipping OCR/Parsing due to disease lookup match.")

    else:
        # Fallback to OCR + Rule-Based Parser
        # 3. OCR (re-labeled as part of else block logic flow)
        try:
            logger.info("Starting OCR processing...")
            content = await file.read()
            logger.info(f"File read. Size: {len(content)} bytes. Starting OCR...")
            text = extract_text(content)
            if not text:
                logger.warning("OCR extracted empty text.")
                raise HTTPException(status_code=400, detail="Could not extract text from image.")
            logger.info(f"OCR successful. Extracted {len(text)} characters.")
        except Exception as e:
            logger.error(f"OCR failed: {e}")
            raise HTTPException(status_code=500, detail="OCR processing failed")


        # 4. Parsing (Rule-Based)
        try:
            logger.info(f"OCR completed. extracted {len(text)} characters. Starting rule-based parsing...")
            extracted_medications = parse_prescription_text(text)
            import json
            logger.info(f"Parsing result:\n{json.dumps(extracted_medications, indent=2)}")
            logger.info(f"Parsing completed. Found {len(extracted_medications)} medications.")
        except Exception as e:
            logger.error(f"Parsing failed: {e}")
            # Dont fail the whole request, just log and continue with empty list or fallback
            extracted_medications = []

    # 4. Save to DB
    try:
        # Create Prescription
        prescription_id = str(uuid.uuid4())
        prescription = Prescription(
            id=prescription_id,
            patient_id=patient.id,
            doctor_note=text # Save raw text as well
        )
        db.add(prescription)
        
        # Create Medications and Notifications
        for med_data in extracted_medications:
            # 1. Save Medication
            medication = Medication(
                prescription_id=prescription_id,
                name=med_data.get("medicine_name"),
                dose=med_data.get("dosage"),
                # frequency=med_data.get("frequency"), # If your model has this field. If not, skip or add to doctor_note
                # For MVP we might not have start/end date in regex parser yet, so leave None or default
                start_date=datetime.utcnow(), 
                end_date=datetime.utcnow() + timedelta(days=5) # Default 5 days course
            )
            db.add(medication)
            
            # 2. Create Notifications based on times
            times = med_data.get("times", [])
            for time_str in times:
                # Convert "HH:MM" to full datetime for the *first* notification (or schedule recurring)
                # MVP: Schedule for today/tomorrow at that time
                try:
                    hour, minute = map(int, time_str.split(':'))
                    now = datetime.utcnow()
                    send_at = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    
                    if send_at < now:
                        # If time has passed today, schedule for tomorrow
                        send_at += timedelta(days=1)
                        
                    notification = Notification(
                        prescription_id=prescription_id,
                        message=f"Time to take your medicine: {med_data.get('medicine_name')} ({med_data.get('dosage')}) - {med_data.get('instructions') or ''}",
                        send_at=send_at,
                        status="PENDING"
                    )
                    db.add(notification)
                except Exception as ex:
                    logger.warning(f"Failed to schedule time {time_str}: {ex}")

        db.commit()
        
        # Immediate Telegram Update
        if patient.telegram_chat_id:
            msg = f"Prescription processed successfully.\nFound {len(extracted_medications)} medications."
            await send_reminder(patient.telegram_chat_id, msg)
        
        logger.info(f"Prescription {prescription_id} processed and saved successfully.")
        return {
            "status": "success",
            "prescription_id": prescription_id,
            "extracted_data": extracted_medications
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Database save failed: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
