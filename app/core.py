# app/core.py
import asyncio
import html
import logging
import functools
import re
from collections import defaultdict
from urllib.parse import urlparse, parse_qs

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.utils.markdown import hbold, hcode

from app.services.qr_decoder import decode_qr_locally
from app.services.security import is_rate_limited, check_url_safety

# Создаем логгер на уровне модуля
logger = logging.getLogger(__name__)

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
        return format_wifi_response(content)
    elif qr_type == "email":
        return format_email_response(content)
    elif qr_type == "phone":
        return format_phone_response(content)
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
    escaped_url = html.escape(url)
    short_url = escaped_url if len(escaped_url) <= 45 else escaped_url[:42] + '...'
    header = f"{hbold('Найдена ссылка:')}\n{short_url}\n"

    is_safe, threat_info = await check_url_safety(url, settings)
    threat_info_escaped = html.escape(threat_info) if threat_info else None

    if is_safe is None:
        safety_msg = f"{hbold('⚠️ Не удалось проверить безопасность')}\n{threat_info_escaped or 'Неизвестная ошибка.'}"
    elif is_safe:
        safety_msg = f"{hbold('🟢 Ссылка безопасна')}\nПроверено через Google Safe Browsing"
    else:
        safety_msg = f"{hbold('🚨 ОПАСНАЯ ССЫЛКА!')}\n\n{hbold('⚠️ Обнаружена угроза:')} {threat_info_escaped or 'Неизвестная угроза.'}\n\n{hbold('❌ НЕ ПЕРЕХОДИТЕ ПО ЭТОЙ ССЫЛКЕ!')}"

    text = f"{header}\n{safety_msg}"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🌐 Перейти по ссылке", url=url)]])
    return text, keyboard

def format_vcard_response(content: str) -> tuple[str, InlineKeyboardMarkup | None]:
    props = defaultdict(list)
    for line in content.splitlines():
        if ':' not in line:
            continue
        key, value = line.split(':', 1)
        key_parts = key.split(';')
        props[key_parts[0].upper()].append(value)

    name = props.get('FN', [''])[0]
    phones = props.get('TEL', [])
    emails = props.get('EMAIL', [])
    org = props.get('ORG', [''])[0]
    title = props.get('TITLE', [''])[0]

    text = f"{hbold('👤 Контакт (vCard):')}\n\n"
    if name: text += f"{hbold('📝 Имя:')} {html.escape(name)}\n"
    if phones: text += f"{hbold('📞 Телефон:')} {html.escape(phones[0])}\n"
    if emails: text += f"{hbold('📧 Email:')} {html.escape(emails[0])}\n"
    if org: text += f"{hbold('🏢 Организация:')} {html.escape(org)}\n"
    if title: text += f"{hbold('💼 Должность:')} {html.escape(title)}\n"

    return text, None # No button for vCard

def parse_semicolon_separated(text):
    escaped_marker = '__ESCAPED_SEMICOLON__'
    text = text.replace(r'\;', escaped_marker)
    parts = [part.replace(escaped_marker, ';') for part in text.split(';')]
    return parts

def format_mecard_response(content: str) -> tuple[str, InlineKeyboardMarkup | None]:
    mecard_data = {}
    params = parse_semicolon_separated(content.replace('MECARD:', '', 1))
    
    for param in params:
        if not param: continue
        parts = param.split(':', 1)
        if len(parts) == 2:
            key, value = parts
            value = value.replace(r'\,', ',').replace(r'\;', ';').replace(r'\:', ':')
            key_upper = key.upper()
            if key_upper == 'N':
                name_parts = value.split(',')
                mecard_data['last_name'] = name_parts[0]
                if len(name_parts) > 1:
                    mecard_data['first_name'] = name_parts[1]
            elif key_upper == 'TEL': mecard_data['phone'] = value
            elif key_upper == 'EMAIL': mecard_data['email'] = value
            elif key_upper == 'ORG': mecard_data['organization'] = value

    text = f"{hbold('👤 Контакт (MeCard):')}\n\n"
    full_name = []
    if 'first_name' in mecard_data: full_name.append(mecard_data['first_name'])
    if 'last_name' in mecard_data: full_name.append(mecard_data['last_name'])
    if full_name: text += f"{hbold('📝 Имя:')} {html.escape(' '.join(full_name))}\n"

    if 'phone' in mecard_data: text += f"{hbold('📞 Телефон:')} {html.escape(mecard_data['phone'])}\n"
    if 'email' in mecard_data: text += f"{hbold('📧 Email:')} {html.escape(mecard_data['email'])}\n"
    if 'organization' in mecard_data: text += f"{hbold('🏢 Организация:')} {html.escape(mecard_data['organization'])}\n"

    return text, None # No button for MeCard

def format_wifi_response(content: str) -> tuple[str, InlineKeyboardMarkup | None]:
    wifi_data = {}
    params = parse_semicolon_separated(content.replace('WIFI:', '', 1))

    for param in params:
        if not param: continue
        parts = param.split(':', 1)
        if len(parts) == 2:
            key, value = parts
            value = value.replace(r'\;', ';').replace(r'\:', ':')
            wifi_data[key.upper()] = value

    ssid = wifi_data.get('S', '')
    password = wifi_data.get('P', '')
    auth = wifi_data.get('T', 'No encryption')
    hidden = wifi_data.get('H', 'false').lower() == 'true'

    text = (
        f"{hbold('📶 Wi-Fi сеть:')}\n"
        f"{hbold('SSID:')} {hcode(ssid)}\n"
        f"{hbold('Пароль:')} {hcode(password) if password else 'Без пароля'}\n"
        f"{hbold('Тип защиты:')} {html.escape(auth)}\n"
        f"{hbold('Скрытая сеть:')} {'Да' if hidden else 'Нет'}"
    )
    return text, None

def format_email_response(content: str) -> tuple[str, InlineKeyboardMarkup | None]:
    try:
        parsed_url = urlparse(content)
        email_address = parsed_url.path
        query_params = parse_qs(parsed_url.query)
        subject = query_params.get("subject", [""])[0]
        body = query_params.get("body", [""])[0]

        text = f"{hbold('✉️ E-mail:')} {hcode(email_address)}"
        if subject: text += f"\n{hbold('Тема:')} {html.escape(subject)}"
        if body: text += f"\n{hbold('Текст:')} {html.escape(body)}"
        
    except Exception as e:
        logger.error(f"Error parsing Email QR content: {e}")
        text = f"{hbold('✉️ Не удалось распознать Email QR-код.')}\nСодержимое: {html.escape(content[:100])}..."

    return text, None # No button for email

def format_phone_response(content: str) -> tuple[str, InlineKeyboardMarkup | None]:
    phone_number = content.replace("tel:", "", 1)
    text = f"{hbold('📞 Телефон:')}\n{hcode(phone_number)}"
    return text, None # No button for phone

def format_sms_response(content: str) -> tuple[str, InlineKeyboardMarkup | None]:
    try:
        parts = content.replace("sms:", "", 1).split(':', 1)
        phone = parts[0]
        message = parts[1] if len(parts) > 1 else ""

        text = f"{hbold('💬 SMS на номер:')}\n{hcode(phone)}"
        if message: text += f"\n{hbold('Текст:')} {html.escape(message)}"

    except Exception as e:
        logger.error(f"Error parsing SMS QR content: {e}")
        text = f"{hbold('💬 Не удалось распознать SMS.')}\nСодержимое: {html.escape(content[:100])}..."

    return text, None # No button for SMS

def format_geo_response(content: str) -> tuple[str, InlineKeyboardMarkup | None]:
    try:
        coords_part = content.replace("geo:", "", 1)
        parts = coords_part.split(',')
        if len(parts) < 2: raise ValueError("Invalid geo coordinates")
        lat, lon = parts[0], parts[1]

        text = f"{hbold('📍 Геопозиция:')}\nШирота: {html.escape(lat)}\nДолгота: {html.escape(lon)}"
        maps_url = f"https://www.google.com/maps?q={lat},{lon}"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🗺️ Открыть на карте", url=maps_url)]])
    except Exception as e:
        logger.error(f"Error parsing Geo QR: {e}")
        text = f"{hbold('📍 Не удалось распознать геопозицию.')}\nСодержимое: {html.escape(content[:100])}..."
        keyboard = None
    return text, keyboard

def format_telegram_response(content: str) -> tuple[str, InlineKeyboardMarkup | None]:
    text = f"{hbold('📱 Ссылка Telegram:')}\n{hcode(content)}"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="➡️ Открыть в Telegram", url=content)]])
    return text, keyboard

def format_whatsapp_response(content: str) -> tuple[str, InlineKeyboardMarkup | None]:
    text = f"{hbold('💬 Ссылка WhatsApp:')}\n{hcode(content)}"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="➡️ Открыть в WhatsApp", url=content)]])
    return text, keyboard

def format_text_response(content: str) -> tuple[str, InlineKeyboardMarkup | None]:
    safe_content = hcode(content)
    text = f"{hbold('📝 Распознанный текст:')}\n\n{safe_content}"
    return text, None

# --- Определение типа QR ---
def detect_qr_type(content: str) -> str:
    content_lower = content.lower().strip()
    if content_lower.startswith("begin:vcard"): return "vcard"
    if content_lower.startswith("mecard:"): return "mecard"
    if content_lower.startswith("wifi:"): return "wifi"
    if content_lower.startswith("mailto:"): return "email"
    if content_lower.startswith("tel:"): return "phone"
    if content_lower.startswith("sms:"): return "sms"
    if content_lower.startswith("geo:"): return "geo"
    if "t.me/" in content_lower or "telegram.me" in content_lower: return "telegram"
    if "wa.me/" in content_lower or "whatsapp.com" in content_lower: return "whatsapp"
    if urlparse(content.strip()).scheme in ['http', 'https']: return "url"
    return "text"

# --- Handlers ---
async def start_handler(message: Message):
    await message.answer("👋 Отправьте мне изображение с QR-кодом, и я пришлю его содержимое!")

async def help_handler(message: Message):
    help_text = (
        f"{hbold('ℹ️ Помощь по боту')}\n\n"
        "Я сканирую QR-коды с изображений и присылаю их содержимое. "
        "Для безопасных ссылок я также показываю результат проверки Google Safe Browsing.\n\n"
        f"{hbold('Как использовать:')}\n"
        "1. Отправьте мне фотографию или скриншот с QR-кодом.\n"
        "2. Я автоматически распознаю его и пришлю результат.\n\n"
        "Просто, быстро и без рекламы!"
    )
    await message.answer(help_text)

async def tips_handler(message: Message):
    tips_keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="💸 Оставить чаевые", url="https://pay.cloudtips.ru/p/221ed8a2")]])
    tips_text = (
        f"{hbold('Поддержать автора')}\n\n"
        "Если вам нравится этот бот, вы можете поблагодарить автора чаевыми. "
        "Все средства пойдут на оплату серверов и дальнейшее развитие проекта.\n\n"
        "Спасибо за вашу поддержку! ❤️"
    )
    await message.answer(tips_text, reply_markup=tips_keyboard)

async def scan_qr(message: Message, bot: Bot, settings):
    logger.info(f"scan_qr called for user {message.from_user.id}")
    user_id = message.from_user.id

    if is_rate_limited(user_id, settings):
        await message.answer("⏰ Слишком много запросов! Попробуйте снова через минуту.")
        return

    try:
        photo = message.photo[-1]
        if photo.file_size and photo.file_size > settings.max_file_size:
            await message.answer(f"❌ Файл слишком большой. Максимальный размер: {settings.max_file_size // (1024*1024)}MB.")
            return

        file = await bot.get_file(photo.file_id)
        logger.info(f"Got file info: {file.file_path}")
        
        file_stream = await bot.download_file(file.file_path)
        file_bytes = file_stream.read()
        logger.info(f"Downloaded file, size: {len(file_bytes)} bytes")

        result = decode_qr_locally(file_bytes, settings)
        logger.info(f"Decoded QR result: {repr(result)}")

        if result:
            qr_type = detect_qr_type(result)
            logger.info(f"Detected QR type: {qr_type}")
            
            response_text, keyboard = await format_qr_response(result, qr_type, settings)
            logger.info(f"Formatted response text (first 100 chars): {repr(response_text[:100])}")

            if len(response_text) > 4096:
                response_text = response_text[:4092] + "..."

            await message.answer(response_text, reply_markup=keyboard)
        else:
            logger.info("No QR code found in image.")
            await message.answer("❌ QR-код не найден. Попробуйте другое изображение.")

    except Exception as e:
        logger.error(f"Error processing photo from user {user_id}: {e}", exc_info=True)
        try:
            await message.answer("❌ Произошла ошибка при обработке изображения. Пожалуйста, попробуйте еще раз.")
        except Exception as send_error:
            logger.error(f"Failed to send error message to user {user_id}: {send_error}")

# --- Основная функция ---
async def run_bot(settings_instance):
    """Main function to start the bot."""
    bot = Bot(token=settings_instance.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    scan_qr_handler = functools.partial(scan_qr, bot=bot, settings=settings_instance)

    dp.message.register(start_handler, Command("start"))
    dp.message.register(help_handler, Command("help"))
    dp.message.register(tips_handler, Command("tips"))
    dp.message.register(scan_qr_handler, F.photo)

    logger.info("Starting QR Scanner Bot polling...")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()
        logger.info("Bot session closed.")
