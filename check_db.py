
from app.db.database import SessionLocal
from app.db.models import Notification
from datetime import datetime

db = SessionLocal()
try:
    print(f"Current UTC time: {datetime.utcnow()}")
    notifications = db.query(Notification).all()
    print(f"Total notifications: {len(notifications)}")
    for n in notifications:
        print(f"ID: {n.id}, Send At: {n.send_at}, Status: {n.status}, Msg: {n.message[:30]}...")
finally:
    db.close()
