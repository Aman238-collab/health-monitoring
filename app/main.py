import asyncio
from dotenv import load_dotenv
import os

load_dotenv()

from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.api import prescriptions
from app.db.database import engine, Base
from app.scheduler.notification_worker import start_scheduler
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create tables
Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Start scheduler
    logger.info("Application startup...")
    task = asyncio.create_task(start_scheduler())
    yield
    # Shutdown
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        logger.info("Scheduler task cancelled.")

from fastapi import Request
from fastapi.responses import JSONResponse

app = FastAPI(lifespan=lifespan)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Incoming request: {request.method} {request.url}")
    try:
        response = await call_next(request)
        logger.info(f"Request completed. Status: {response.status_code}")
        return response
    except Exception as e:
        logger.error(f"Unhandled exception during request processing: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"detail": "Internal Server Error", "error": str(e)})

app.include_router(prescriptions.router, prefix="/api")

@app.get("/")
def read_root():
    return {"message": "Prescription Reminder System API is running."}
