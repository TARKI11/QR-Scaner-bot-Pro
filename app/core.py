# app/core.py
import asyncio
import logging
from aiogram import Bot, Dispatcher
from app.config import Settings # Импортируем класс Settings
from app.bot import register_handlers # Импортируем функцию регистрации

# Создаем экземпляр настроек здесь, после того как все переменные окружения должны быть доступны
settings = Settings()

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
    # Регистрируем handlers, передавая экземпляр настроек
    register_handlers(dp, settings)
    await dp.start_polling(bot)
