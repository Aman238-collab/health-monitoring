import os
import logging
import asyncio
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from telegram.error import TelegramError

logger = logging.getLogger(__name__)

# Default Telegram credentials from user snippet
DEFAULT_BOT_TOKEN = "8519348537:AAHDZDPJ5Iq54zkDrTBp4OJTRTZDtCVj6_0"
DEFAULT_CHAT_ID = "6854561915"

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", DEFAULT_BOT_TOKEN)

# Global application instance to be shared across the backend
application = None

async def hello(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for the /hello command."""
    await update.message.reply_text(f'Hello {update.effective_user.first_name}')

def setup_application():
    """Initializes the Telegram Application instance."""
    global application
    if application:
        return application
        
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set. Bot will not start.")
        return None

    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("hello", hello))
    
    return application

async def send_reminder(chat_id: str, message: str) -> bool:
    """
    Sends a message to the specified Telegram chat ID.
    Uses the active python-telegram-bot instance if available, 
    otherwise falls back to a direct HTTP request (user snippet style).
    """
    # 1. Try using the active Application/Bot instance (Efficient for sessions)
    if application and application.bot:
        try:
            formatted_message = f"💊 *Medication Reminder*\n\n{message}"
            logger.info(f"🚀 [Telegram LIVE] Attempting to send message to {chat_id}")
            await application.bot.send_message(chat_id=chat_id, text=formatted_message, parse_mode='Markdown')
            logger.info(f"Message sent successfully to {chat_id}")
            return True
        except TelegramError as e:
            logger.error(f"Failed to send Telegram message via bot instance to {chat_id}: {e}")
            # Fall through to HTTP fallback

    # 2. Fallback: Direct HTTP request (User Snippet Style)
    import httpx
    token = TELEGRAM_BOT_TOKEN
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": f"💊 Medication Reminder\n\n{message}"}
    
    logger.info(f"Using HTTP fallback to send message to {chat_id}")
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, data=payload)
            if resp.status_code == 200:
                logger.info(f"HTTP fallback successful for {chat_id}")
                return True
            else:
                logger.error(f"HTTP fallback failed: {resp.text}")
                return False
    except Exception as e:
        logger.error(f"HTTP fallback exception: {e}")
        return False
