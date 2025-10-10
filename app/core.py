# app/core.py
import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.utils.markdown import hbold, hcode
# from app.config import Settings # <-- УБРАТЬ, если не используется для создания экземпляра здесь
# from app.config import settings # <-- ТОЧНО УБРАТЬ!
from app.services.qr_decoder import decode_qr_locally
from app.services.security import is_rate_limited, check_url_safety
from app.utils.markdown import escape_markdown_v2
from urllib.parse import urlparse, parse_qs
import re
import time
from collections import defaultdict

# --- Форматирование ответов (теперь принимает settings как аргумент) ---
# ... (все функции format_*, например format_url_response(settings, url)) ...
# ПРИМЕР:
async def format_url_response(url: str, settings) -> tuple[str, InlineKeyboardMarkup | None]:
    escaped_url = escape_markdown_v2(url)
    short_url = escaped_url if len(escaped_url) <= 45 else escaped_url[:42] + '...'
    header = f"{hbold('Найдена ссылка:')}\n{short_url}\n"

    is_safe, threat_info = await check_url_safety(url, settings)

    if is_safe is None:
        safety_msg = f"{hbold('⚠️ Не удалось проверить безопасность')}\n{escape_markdown_v2(threat_info) if threat_info else 'Неизвестная ошибка.'}"
    elif is_safe:
        safety_msg = f"{hbold('🟢 Ссылка безопасна')}\nПроверено через Google Safe Browsing"
    else:
        safety_msg = f"{hbold('🚨 ОПАСНАЯ ССЫЛКА!')}\n\n{hbold('⚠️ Обнаружена угроза:')} {escape_markdown_v2(threat_info) if threat_info else 'Неизвестная угроза.'}\n\n{hbold('❌ НЕ ПЕРЕХОДИТЕ ПО ЭТОЙ ССЫЛКЕ!')}"

    text = f"{header}\n{safety_msg}"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🌐 Перейти по ссылке", url=url)]])
    return text, keyboard

# --- Определение типа QR (не зависит от settings) ---
# ... (detect_qr_type(content)) ...

# --- Handlers (теперь принимает settings как аргумент) ---
# ... (start_handler, help_handler, tips_handler) ...
# ПРИМЕР scan_qr:
async def scan_qr(message: Message, settings):
    user_id = message.from_user.id

    if is_rate_limited(user_id, settings):
        await message.answer("⏰ Слишком много запросов! Подождите минуту перед следующим запросом.")
        return

    try:
        photo = message.photo[-1]

        if photo.file_size and photo.file_size > settings.max_file_size:
            await message.answer(f"❌ Файл слишком большой! Максимальный размер: {settings.max_file_size // (1024*1024)}MB")
            return

        file = await message.bot.get_file(photo.file_id)
        file_bytes = await message.bot.download_file(file.file_path)

        result = decode_qr_locally(file_bytes, settings)

        if result:
            qr_type = detect_qr_type(result)
            # Передаем settings в format_qr_response
            response_text, keyboard = await format_qr_response(result, qr_type, settings)

            if len(response_text) > 4000:
                response_text = response_text[:4000] + "..."

            if keyboard:
                await message.answer(response_text, reply_markup=keyboard, parse_mode="MarkdownV2")
            else:
                await message.answer(response_text, parse_mode="MarkdownV2")
        else:
            await message.answer("❌ Не удалось распознать QR-код. Проверь картинку!")

    except Exception as e:
        logger.error(f"Error processing photo from user {user_id}: {e}")
        try:
            await message.answer("❌ Произошла ошибка при обработке изображения. Попробуйте еще раз.")
        except Exception as send_error:
            logger.error(f"Failed to send error message to user {user_id}: {send_error}")

# --- ОСНОВНАЯ ФУНКЦИЯ (не создает Settings!) ---
async def main(settings_instance): # <-- Принимает settings как аргумент!
    """Main function to start the bot."""
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

    # Передаем settings_instance как аргумент в scan_qr через lambda
    dp.message.register(lambda msg: scan_qr(msg, settings_instance), F.photo)

    await dp.start_polling(bot)
