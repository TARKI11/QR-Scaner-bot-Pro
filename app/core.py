# app/core.py
import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.utils.markdown import hbold, hcode
# from app.config import settings # <-- УБРАНО! settings передаётся как аргумент
from aiogram.types import Message
# from app.config import Settings # <-- Не нужно здесь
from app.services.qr_decoder import decode_qr_locally
from app.services.security import is_rate_limited, check_url_safety
from app.utils.markdown import escape_markdown_v2
from urllib.parse import urlparse, parse_qs
import re
import time
from collections import defaultdict

# --- Форматирование ответов ---
async def format_qr_response(content: str, qr_type: str, settings) -> tuple[str, InlineKeyboardMarkup | None]:
    """Format QR code response based on its type."""
    if qr_type == "url":
        return await format_url_response(content, settings)
    elif qr_type == "vcard":
        return format_vcard_response(content)
    elif qr_type == "mecard":
        return format_mecard_response(content)
    elif qr_type == "wifi":
        text, keyboard = format_wifi_response(content)
        return text, keyboard
    elif qr_type == "email":
        return format_email_response(content)
    elif qr_type == "phone":
        text, keyboard = format_phone_response(content)
        return text, keyboard
    elif qr_type == "sms":
        return format_sms_response(content)
    elif qr_type == "geo":
        return format_geo_response(content)
    elif qr_type == "telegram":
        return format_telegram_response(content)
    elif qr_type == "whatsapp":
        return format_whatsapp_response(content)
    else: # text
        return format_text_response(content)

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

def format_vcard_response(content: str) -> tuple[str, InlineKeyboardMarkup | None]:
    lines = content.split('\n')
    vcard_data = {}
    for line in lines:
        if line.upper().startswith('FN:'):
            vcard_data['name'] = line[3:]
        elif line.upper().startswith('TEL:'):
            vcard_data['phone'] = line[4:]
        elif line.upper().startswith('EMAIL:'):
            vcard_data['email'] = line[6:]
        elif line.upper().startswith('ORG:'):
            vcard_data['organization'] = line[4:]
        elif line.upper().startswith('TITLE:'):
            vcard_data['title'] = line[6:]

    text = f"{hbold('👤 Контакт (vCard):')}\n\n"
    if 'name' in vcard_data:
        text += f"{hbold('📝 Имя:')} {escape_markdown_v2(vcard_data['name'])}\n"
    if 'phone' in vcard_data:
        text += f"{hbold('📞 Телефон:')} {escape_markdown_v2(vcard_data['phone'])}\n"
    if 'email' in vcard_data:
        text += f"{hbold('📧 Email:')} {escape_markdown_v2(vcard_data['email'])}\n"
    if 'organization' in vcard_data:
        text += f"{hbold('🏢 Организация:')} {escape_markdown_v2(vcard_data['organization'])}\n"
    if 'title' in vcard_data:
        text += f"{hbold('💼 Должность:')} {escape_markdown_v2(vcard_data['title'])}\n"

    keyboard = None
    if 'phone' in vcard_data and re.match(r'^[\d\+\-\(\)\s]+$', vcard_data['phone']):
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📱 Позвонить", url=f"tel:{vcard_data['phone']}")]])
    return text, keyboard

def format_mecard_response(content: str) -> tuple[str, InlineKeyboardMarkup | None]:
    content_after_prefix = content[7:]
    mecard_data = {}
    params = content_after_prefix.split(';')
    for param in params:
        if ':' in param:
            key, value = param.split(':', 1)
            if key.upper() == 'N':
                name_parts = value.split(',')
                if len(name_parts) >= 2: mecard_data['first_name'], mecard_data['last_name'] = name_parts[1], name_parts[0]
                else: mecard_data['name'] = value
            elif key.upper() == 'TEL': mecard_data['phone'] = value
            elif key.upper() == 'EMAIL': mecard_data['email'] = value
            elif key.upper() == 'ORG': mecard_data['organization'] = value

    text = f"{hbold('👤 Контакт (MeCard):')}\n\n"
    name_parts = []
    if 'name' in mecard_data:
        name_parts.append(escape_markdown_v2(mecard_data['name']))
    elif 'first_name' in mecard_data and 'last_name' in mecard_data:
        name_parts.extend([escape_markdown_v2(mecard_data['first_name']), escape_markdown_v2(mecard_data['last_name'])])
    if name_parts:
        text += f"{hbold('📝 Имя:')} {' '.join(name_parts)}\n"
    if 'phone' in mecard_data:
        text += f"{hbold('📞 Телефон:')} {escape_markdown_v2(mecard_data['phone'])}\n"
    if 'email' in mecard_data:
        text += f"{hbold('📧 Email:')} {escape_markdown_v2(mecard_data['email'])}\n"
    if 'organization' in mecard_data:
        text += f"{hbold('🏢 Организация:')} {escape_markdown_v2(mecard_data['organization'])}\n"

    keyboard = None
    if 'phone' in mecard_data and re.match(r'^[\d\+\-\(\)\s]+$', mecard_data['phone']):
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📱 Позвонить", url=f"tel:{mecard_data['phone']}")]])
    return text, keyboard

def format_wifi_response(content: str) -> tuple[str, InlineKeyboardMarkup | None]:
    try:
        wifi_data = {}
        content_after_prefix = content[5:]
        params = content_after_prefix.split(';')
        for param in params:
            if ':' in param:
                key, value = param.split(':', 1)
                wifi_data[key] = value

        ssid = wifi_data.get('S', 'Неизвестно')
        password = wifi_data.get('P', 'Неизвестно')
        auth = wifi_data.get('T', 'Неизвестно')
        hidden = wifi_data.get('H', 'false').lower() == 'true'

        text = (
            f"{hbold('📶 Wi-Fi сеть обнаружена!')}\n"
            f"{hbold('• SSID:')} {hcode(ssid)}\n"
            f"{hbold('• Пароль:')} {hcode(password)}\n"
            f"{hbold('• Тип защиты:')} {escape_markdown_v2(auth)}\n"
            f"{hbold('• Скрытая сеть:')} {'Да' if hidden else 'Нет'}"
        )
    except Exception as e:
        logger.error(f"Error parsing Wi-Fi QR content: {e}")
        text = f"{hbold('📶 Не удалось распознать Wi-Fi QR-код.')}\nСодержимое: {escape_markdown_v2(content[:100])}..."
    return text, None # No keyboard for Wi-Fi

def format_email_response(content: str) -> tuple[str, InlineKeyboardMarkup | None]:
    try:
        email_address = content[7:] # Remove mailto:
        parsed_url = urlparse(content)
        email_address = parsed_url.path
        query_params = parse_qs(parsed_url.query)
        subject = query_params.get("subject", [""])[0]
        body = query_params.get("body", [""])[0]

        text = f"{hbold('✉️ E-mail:')} {hcode(email_address)}"
        if subject: text += f"\n{hbold('Тема:')} {escape_markdown_v2(subject)}"
        if body: text += f"\n{hbold('Текст:')} {escape_markdown_v2(body)}"
    except Exception as e:
        logger.error(f"Error parsing Email QR content: {e}")
        text = f"{hbold('✉️ Не удалось распознать Email QR-код.')}\nСодержимое: {escape_markdown_v2(content[:100])}..."
    return text, None # No keyboard for email

def format_phone_response(content: str) -> tuple[str, InlineKeyboardMarkup | None]:
    try:
        phone_number = content[4:] # Remove tel:
        if not re.match(r'^[\d\+\-\(\)\s]+$', phone_number):
             logger.warning(f"Invalid phone number format in QR: {phone_number}")
             text = f"{hbold('📞 Неверный формат номера телефона в QR-коде.')}\nСодержимое: {escape_markdown_v2(content)}"
             return text, None
        text = f"{hbold('📞 Телефон:')}\n{hcode(phone_number)}"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📱 Позвонить", url=content)]])
    except Exception as e:
        logger.error(f"Error parsing Phone QR content: {e}")
        text = f"{hbold('📞 Не удалось распознать номер телефона в QR-коде.')}\nСодержимое: {escape_markdown_v2(content[:100])}..."
        keyboard = None
    return text, keyboard

def format_sms_response(content: str) -> tuple[str, InlineKeyboardMarkup | None]:
    try:
        content_after_prefix = content[4:] # Remove sms:
        parts = content_after_prefix.split(':', 1)
        phone = parts[0]
        message = parts[1] if len(parts) > 1 else ""

        if not re.match(r'^[\d\+\-\(\)\s]+$', phone):
             logger.warning(f"Invalid phone number format in SMS QR: {phone}")
             text = f"{hbold('💬 Неверный формат номера телефона в SMS QR-коде.')}\nСодержимое: {escape_markdown_v2(content)}"
             return text, None

        text = f"{hbold('💬 SMS сообщение:')}\n\n{hbold('📞 Номер:')} {hcode(phone)}"
        if message: text += f"\n{hbold('💭 Текст:')} {escape_markdown_v2(message)}"

        keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="💬 Отправить SMS", url=content)]])
    except Exception as e:
        logger.error(f"Error parsing SMS QR content: {e}")
        text = f"{hbold('💬 Не удалось распознать SMS QR-код.')}\nСодержимое: {escape_markdown_v2(content[:100])}..."
        keyboard = None
    return text, keyboard

def format_geo_response(content: str) -> tuple[str, InlineKeyboardMarkup | None]:
    try:
        coords = content[4:] # Remove geo:
        parts = coords.split(',')
        if len(parts) < 2: raise ValueError("Not enough coordinates")
        lat, lon = parts[0], parts[1]
        float(lat); float(lon) # Validate as numbers

        text = f"{hbold('📍 Геопозиция:')}\n\n{hbold('🌍 Координаты:')}\nШирота: {escape_markdown_v2(lat)}\nДолгота: {escape_markdown_v2(lon)}"
        if len(parts) >= 3:
            alt = parts[2]
            try: float(alt); text += f"\n{hbold('Высота:')} {escape_markdown_v2(alt)} м"
            except ValueError: logger.warning(f"Invalid geo altitude in QR: {alt}")

        maps_url = f"https://www.google.com/maps?q={lat},{lon}"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🗺️ Открыть на карте", url=maps_url)]])
        return text, keyboard
    except (ValueError, IndexError) as e:
        logger.error(f"Error parsing Geo QR content: {e}")
        text = f"{hbold('📍 Не удалось распознать геопозицию из QR-кода.')}\nСодержимое: {escape_markdown_v2(content[:100])}..."
    except Exception as e:
        logger.error(f"Unexpected error parsing Geo QR content: {e}")
        text = f"{hbold('📍 Не удалось распознать геопозицию из QR-кода.')}\nСодержимое: {escape_markdown_v2(content[:100])}..."
    return text, None

def format_telegram_response(content: str) -> tuple[str, InlineKeyboardMarkup | None]:
    if not (content.startswith("tg://") or content.startswith("https://t.me/")):
        logger.warning(f"Invalid Telegram link format: {content}")
        text = f"{hbold('📱 Неверный формат Telegram-ссылки в QR-коде.')}\nСодержимое: {escape_markdown_v2(content)}"
        return text, None

    text = f"{hbold('📱 Telegram ссылка:')}\n\n"
    if content.startswith("tg://"):
        text += f"{hbold('🔗 Ссылка:')} {hcode(content)}\n\n{hbold('💡 Это может быть ссылка на бота, канал или группу')}"
    else:
        text += f"{hbold('🔗 Ссылка:')} {hcode(content)}\n\n{hbold('💡 Это может быть ссылка на канал, группу или пользователя')}"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📱 Открыть в Telegram", url=content)]])
    return text, keyboard

def format_whatsapp_response(content: str) -> tuple[str, InlineKeyboardMarkup | None]:
    text = f"{hbold('💬 WhatsApp ссылка:')}\n\n"
    if content.startswith("https://wa.me/"):
        phone = content[14:]  # Remove https://wa.me/
        text += f"{hbold('📞 Номер:')} {hcode(phone)}\n\n{hbold('💡 Это ссылка для быстрого сообщения в WhatsApp')}"
        if not re.match(r'^[\d\+]+$', phone):
            logger.warning(f"Invalid phone number in WhatsApp link: {phone}")
            text = f"{hbold('💬 Неверный формат номера телефона в WhatsApp-ссылке.')}\nСодержимое: {escape_markdown_v2(content)}"
            return text, None
    elif content.startswith("whatsapp://"):
        text += f"{hbold('🔗 Ссылка:')} {hcode(content)}\n\n{hbold('💡 Это WhatsApp-ссылка')}"
    else:
        logger.warning(f"Invalid WhatsApp link format: {content}")
        text = f"{hbold('💬 Неверный формат WhatsApp-ссылки в QR-коде.')}\nСодержимое: {escape_markdown_v2(content)}"
        return text, None

    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="💬 Открыть в WhatsApp", url=content)]])
    return text, keyboard

def format_text_response(content: str) -> tuple[str, InlineKeyboardMarkup | None]:
    safe_content = hcode(content)
    text = f"{hbold('📝 Текст:')}\n\n{safe_content}"
    return text, None

# --- Определение типа QR ---
def detect_qr_type(content: str) -> str:
    content = content.strip()
    if content.lower().startswith("mailto:"): return "email"
    if content.lower().startswith("tel:"): return "phone"
    if content.lower().startswith("sms:"): return "sms"
    if content.lower().startswith("geo:"): return "geo"
    if content.startswith("tg://") or content.startswith("https://t.me/"): return "telegram"
    if content.startswith("https://wa.me/") or content.startswith("whatsapp://"): return "whatsapp"
    if content.upper().startswith("WIFI:"): return "wifi"
    if content.upper().startswith("BEGIN:VCARD") and "\nEND:VCARD\n" in content.upper(): return "vcard"
    if content.upper().startswith("MECARD:"): return "mecard"
    if urlparse(content).scheme in ['http', 'https']: return "url"
    return "text"

# --- Handlers ---
async def start_handler(message: Message):
    await message.answer("👋 Отправь мне изображение с QR-кодом, и я пришлю содержимое!")

async def help_handler(message: Message):
    help_text = (
    f"{hbold('ℹ️ QRScanerPro — помощь')}\n\n"
    )
    await message.answer(tips_text, reply_markup=tips_keyboard)

# Обработчик для фотографий с QR-кодом
async def handle_photo(message: Message):
    await message.reply("Я получил вашу фотографию! Сейчас попробую найти QR-код...")


    try:
        # Берём последнее фото (самое большое качество)
        photo = message.photo[-1]
        file_id = photo.file_id

        # Скачиваем фото с серверов Telegram
        file = await message.bot.get_file(file_id)
        photo_bytes = await message.bot.download_file(file.file_path)

        # Здесь должна быть функция, которая ищет QR-код
        # Например: decoded = decode_qr_locally(photo_bytes.read(), settings)
        # Если нет такой функции — просто отправим заглушку

        # Пока просто отправим сообщение что обработка происходит
        await message.reply("Я получил фото! Если QR-код не найдён — это пока пробная версия обработчика.")
    except Exception as e:
        await message.reply(f"Ошибка при обработке фото: {e}")


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

# --- ОСНОВНАЯ ФУНКЦИЯ ---
async def run_bot(settings_instance):
    """Main function to start the bot."""
    logger = logging.getLogger(__name__)
    logging.basicConfig(
        level=logging.DEBUG if settings_instance.is_debug else logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger.info("Starting QR Scanner Bot...")

    bot = Bot(token=settings_instance.bot_token)
    dp = Dispatcher()

dp.message.register(start_handler, Command("start"))
dp.message.register(help_handler, Command("help"))
dp.message.register(tips_handler, Command("tips"))
dp.message.register(handle_photo, F.photo)
