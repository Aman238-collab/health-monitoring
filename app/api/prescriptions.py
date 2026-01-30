from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import Patient, Prescription, Medication, Notification
from app.ocr.tesseract_service import extract_text
from app.llm.gemini_agent import process_prescription_text
import uuid
from datetime import datetime
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/prescriptions/")
async def upload_prescription(
    file: UploadFile = File(...),
    patient_id: str = Form(...),
    telegram_chat_id: str = Form(None), # Optional if patient exists
    db: Session = Depends(get_db)
):
    logger.info(f"Received prescription upload. File: {file.filename}, Patient: {patient_id}")

    # 1. Handle Patient
    logger.info(f"Processing prescription upload for patient_id: {patient_id}")
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    
    if not patient and telegram_chat_id:
        # Check if telegram_chat_id is already in use
        patient_by_chat = db.query(Patient).filter(Patient.telegram_chat_id == telegram_chat_id).first()
        if patient_by_chat:
            logger.info(f"Found existing patient {patient_by_chat.id} with telegram_chat_id {telegram_chat_id}. Using existing record.")
            patient = patient_by_chat
        else:
             # Create new
             patient = Patient(id=patient_id, telegram_chat_id=telegram_chat_id)
             db.add(patient)
             db.commit()
             db.refresh(patient)
             logger.info(f"Created new patient record for {patient_id}")
    elif not patient:
        # No patient found and no telegram_chat_id supplied (or patient_id supplied but doesn't exist)
        raise HTTPException(status_code=400, detail="New patient requires telegram_chat_id")
    # If patient exists, we just use it.
    
    # 2. OCR
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

    # 3. LLM Processing
    try:
        logger.info(f"OCR completed. extracted {len(text)} characters. Sending to LLM...")
        extracted_data = process_prescription_text(text, patient_id)
        logger.info("LLM processing completed successfully.")
    except Exception as e:
        logger.error(f"LLM failed: {e}")
        raise HTTPException(status_code=500, detail=f"LLM processing failed: {str(e)}")

    # 4. Save to DB
    try:
        # Create Prescription
        prescription_id = str(uuid.uuid4())
        prescription = Prescription(
            id=prescription_id,
            patient_id=patient.id,
            doctor_note=extracted_data.get("doctor_note_generalized", "")
        )
        db.add(prescription)
        
        # Create Medications
        for med in extracted_data.get("medications", []):
            medication = Medication(
                prescription_id=prescription_id,
                name=med.get("name"),
                dose=med.get("dose"),
                # Handle dates carefully - minimal validation for now
                start_date=datetime.strptime(med.get("start_date"), "%Y-%m-%d") if med.get("start_date") else None,
                end_date=datetime.strptime(med.get("end_date"), "%Y-%m-%d") if med.get("end_date") else None
            )
            db.add(medication)

        # Create Notifications
        for notif in extracted_data.get("notifications", []):
            # Parse ISO date
            send_at_str = notif.get("send_at")
            if send_at_str:
                # Handle possible 'Z' or offset if Gemini returns it, though instructions asked for simplified
                # For robustness, try/except parsing
                try:
                    send_at = datetime.fromisoformat(send_at_str)
                except ValueError:
                    # Fallback or skip
                    logger.warning(f"Invalid date format: {send_at_str}")
                    continue

                notification = Notification(
                    prescription_id=prescription_id,
                    message=notif.get("message"),
                    send_at=send_at,
                    status="PENDING"
                )
                db.add(notification)

        db.commit()
        
        logger.info(f"Prescription {prescription_id} processed and saved successfully.")
        return {
            "status": "success",
            "prescription_id": prescription_id,
            "extracted_data": extracted_data
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Database save failed: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
