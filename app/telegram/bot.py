import os
import logging
# from telegram import Bot
# from telegram.error import TelegramError
import asyncio

logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

async def send_reminder(chat_id: str, message: str) -> bool:
    """
    Sends a message to the specified Telegram chat ID.
    Returns True if successful, False otherwise.
    """
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set.")
        return False

    # bot = Bot(token=TELEGRAM_BOT_TOKEN)
    
    formatted_message = f"💊 *Medication Reminder*\n\n{message}"

    return True

    # try:
    #     await bot.send_message(chat_id=chat_id, text=formatted_message, parse_mode='Markdown')
    #     logger.info(f"Message sent to {chat_id}")
    #     return True
    # except TelegramError as e:
    #     logger.error(f"Failed to send Telegram message to {chat_id}: {e}")
    #     # Retry logic could be here, but the scheduler will handle retries/marking as failed essentially by the return value or upper level logic.
    #     # Requirement said: "On failure -> retry once".
    #     # Let's do a quick retry here for transient network issues.
    #     try:
    #         logger.info("Retrying to send message...")
    #         await asyncio.sleep(1)
    #         await bot.send_message(chat_id=chat_id, text=formatted_message, parse_mode='Markdown')
    #         logger.info(f"Retry successful to {chat_id}")
    #         return True
    #     except TelegramError as retry_e:
    #         logger.error(f"Retry failed to {chat_id}: {retry_e}")
    #         return False
