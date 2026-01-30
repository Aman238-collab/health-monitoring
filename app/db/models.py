from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class Patient(Base):
    __tablename__ = "patients"

    id = Column(String, primary_key=True, index=True) # Could be a UUID or phone number
    telegram_chat_id = Column(String, unique=True, index=True)

    prescriptions = relationship("Prescription", back_populates="patient")


class Prescription(Base):
    __tablename__ = "prescriptions"

    id = Column(String, primary_key=True, index=True) # UUID
    patient_id = Column(String, ForeignKey("patients.id"))
    doctor_note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    patient = relationship("Patient", back_populates="prescriptions")
    medications = relationship("Medication", back_populates="prescription")
    notifications = relationship("Notification", back_populates="prescription")


class Medication(Base):
    __tablename__ = "medications"

    id = Column(Integer, primary_key=True, index=True)
    prescription_id = Column(String, ForeignKey("prescriptions.id"))
    name = Column(String)
    dose = Column(String)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)

    prescription = relationship("Prescription", back_populates="medications")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    prescription_id = Column(String, ForeignKey("prescriptions.id"))
    message = Column(String)
    send_at = Column(DateTime)
    status = Column(String, default="PENDING") # PENDING, SENT, FAILED

    prescription = relationship("Prescription", back_populates="notifications")
