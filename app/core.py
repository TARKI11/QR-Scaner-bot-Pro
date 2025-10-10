# app/core.py
import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.utils.markdown import hbold, hcode
# from app.config import settings # <-- УБРАТЬ этот импорт, если settings создается внутри main()
from app.config import Settings # <-- Импортируем КЛАСС Settings
from app.services.qr_decoder import decode_qr_locally
from app.services.security import is_rate_limited, check_url_safety
from app.utils.markdown import escape_markdown_v2
from urllib.parse import urlparse, parse_qs
import re
import time
from collections import defaultdict

# --- Форматирование ответов (все функции должны принимать settings как аргумент) ---
# ... (здесь должны быть все функции format_*, как они были в предыдущем примере, принимающие settings) ...

# --- Определение типа QR (вне зависимости от settings) ---
# ... (здесь должна быть функция detect_qr_type) ...

# --- Handlers (все должны принимать settings как аргумент) ---
# ... (здесь должны быть start_handler, help_handler, tips_handler, scan_qr) ...

# --- ОСНОВНАЯ ФУНКЦИЯ ---
async def main():
    """Main function to start the bot."""
    # Создаем экземпляр настроек ТУТ, когда переменные окружения уже должны быть доступны
    settings_instance = Settings() # <-- Вот где создается экземпляр, НЕ при импорте

    logger = logging.getLogger(__name__)
    logging.basicConfig(
        level=logging.DEBUG if settings_instance.is_debug else logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger.info("Starting QR Scanner Bot...")

    bot = Bot(token=settings_instance.bot_token)
    dp = Dispatcher()

    # Регистрируем handlers
    dp.message.register(start_handler, Command("start"))
    dp.message.register(help_handler, Command("help"))
    dp.message.register(tips_handler, Command("tips"))
    # Передаем settings_instance как аргумент в scan_qr через lambda или отдельную функцию-обертку
    # dp.message.register(scan_qr, F.photo) # <-- НЕПРАВИЛЬНО, если scan_qr ожидает settings
    # Правильный способ передать settings_instance:
    async def scan_qr_with_settings(message: Message):
        # Вызываем оригинальную scan_qr, передав ей settings_instance
        # Убедитесь, что оригинальная scan_qr определена выше и принимает settings
        return await scan_qr(message, settings_instance)

    dp.message.register(scan_qr_with_settings, F.photo)

    await dp.start_polling(bot)

# УБЕДИТЕСЬ, что строка 'settings = Settings()' ОТСУТСТВУЕТ НА УРОВНЕ МОДУЛЯ В ЭТОМ ФАЙЛЕ
# settings = Settings() # <-- УДАЛИТЕ ЭТУ СТРОКУ, ЕСЛИ ОНА ЕСТЬ ГДЕ-ТО ВНУТРИ app/core.py НА УРОВНЕ МОДУЛЯ!
