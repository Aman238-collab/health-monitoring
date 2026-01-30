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
    
    # Initialize and start Telegram bot
    from app.telegram.bot import setup_application
    from telegram.error import InvalidToken, Conflict
    
    # Wait for previous processes to clear connections (longer for Windows/Reload)
    logger.info("Waiting for old bot instances to clear...")
    await asyncio.sleep(5)
    
    tg_app = setup_application()
    
    if tg_app:
        max_retries = 3
        retry_delay = 5
        for attempt in range(max_retries):
            try:
                await tg_app.initialize()
                
                # Agressive "Takeover" strategy:
                # 1. Clear webhooks
                await tg_app.bot.delete_webhook(drop_pending_updates=True)
                
                # 2. Force a conflict on any other instance by calling get_updates once
                # This "steals" the connection and makes the old instance stop.
                logger.info("Attempting to take over Telegram bot connection...")
                try:
                    await tg_app.bot.get_updates(offset=-1, timeout=1)
                except Exception:
                    # Ignore errors here, we just want to signal our presence
                    pass
                
                await asyncio.sleep(1) # Short breath
                
                await tg_app.start()
                # Start polling (non-blocking)
                await tg_app.updater.start_polling(drop_pending_updates=True)
                logger.info("Telegram bot polling started successfully.")
                break
            except InvalidToken:
                logger.error("Failed to start Telegram bot: The token provided in .env is invalid.")
                break
            except Conflict:
                logger.warning(f"Telegram bot conflict detected (attempt {attempt + 1}/{max_retries}). Another instance suggests it's still running. Retrying in {retry_delay}s...")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error("Failed to start Telegram bot after multiple retries due to conflict.")
            except Exception as e:
                logger.error(f"An unexpected error occurred while starting the Telegram bot: {e}")
                break

    scheduler_task = asyncio.create_task(start_scheduler())
    
    yield
    
    # Shutdown
    logger.info("Application shutdown...")
    if tg_app and tg_app.updater.running:
        await tg_app.updater.stop()
        await tg_app.stop()
        await tg_app.shutdown()
        logger.info("Telegram bot stopped.")
        
    scheduler_task.cancel()
    try:
        await scheduler_task
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

from fastapi.staticfiles import StaticFiles

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.get("/")
def read_root():
    from fastapi.responses import FileResponse
    return FileResponse('app/static/index.html')
