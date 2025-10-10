# app/core.py
import asyncio
import logging
from aiogram import Bot, Dispatcher
from app.config import settings
from app.bot import router

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.is_debug else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

bot = Bot(token=settings.bot_token)
dp = Dispatcher()

async def main():
    """Main function to start the bot."""
    logger.info("Starting QR Scanner Bot...")
    dp.include_router(router)
    await dp.start_polling(bot)
