import asyncio
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.db.models import Notification
# from app.telegram.bot import send_reminder

logger = logging.getLogger(__name__)

async def process_notifications():
    """
    Fetch pending notifications and send them.
    """
    db: Session = SessionLocal()
    try:
        now = datetime.utcnow() # match DB utcnow
        # Fetch notifications that are PENDING and due
        pending_notifications = db.query(Notification).filter(
            Notification.status == "PENDING",
            Notification.send_at <= now
        ).all()

        if not pending_notifications:
            return

        logger.info(f"Found {len(pending_notifications)} pending notifications.")

        for notification in pending_notifications:
            # We need the chat_id. It's on the patient.
            # Notification -> Prescription -> Patient
            if not notification.prescription or not notification.prescription.patient:
                logger.error(f"Notification {notification.id} has no linked patient.")
                notification.status = "FAILED"
                continue

            chat_id = notification.prescription.patient.telegram_chat_id
            if not chat_id:
                 logger.error(f"Notification {notification.id}: Patient has no chat_id.")
                 notification.status = "FAILED"
                 continue

            # success = await send_reminder(chat_id, notification.message)
            logger.info(f"Simulating sending Telegram message to {chat_id}: {notification.message}")
            success = True
            
            if success:
                notification.status = "SENT"
            else:
                notification.status = "FAILED"
            
            # Commit after each or batch? Batch is better but individual ensures progress if crash.
            # Let's commit each to be safe and simple.
            db.commit()
            
    except Exception as e:
        logger.error(f"Error in notification worker: {e}")
        db.rollback()
    finally:
        db.close()

async def start_scheduler():
    """
    Simple polling loop.
    APScheduler could also be used, but a loop is lightweight and sufficient as requested.
    """
    logger.info("Starting notification scheduler...")
    while True:
        await process_notifications()
        await asyncio.sleep(60)
