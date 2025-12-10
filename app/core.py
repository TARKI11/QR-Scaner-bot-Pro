# app/core.py
import html
import logging
from datetime import date
from urllib.parse import urlparse
from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.utils.markdown import hbold, hcode
from app.services.qr_decoder import decode_qr_locally
from app.services.security import is_rate_limited, check_url_safety

logger = logging.getLogger(__name__)

# === Статистика ===
total_scans = 0
daily_scans = 0
last_reset = date.today()
OWNER_ID = 7679979587

# === Типы QR и форматирование ===
def detect_qr_type(content: str) -> str:
    c = content.lower().strip()
    if c.startswith("begin:vcard"): return "vcard"
    if c.startswith("mecard:"): return "mecard"
    if c.startswith("wifi:"): return "wifi"
    if c.startswith("mailto:"): return "email"
    if c.startswith("tel:"): return "phone"
    if c.startswith("sms:"): return "sms"
    if c.startswith("geo:"): return "geo"
    if "t.me/" in c or "telegram.me" in c: return "telegram"
    if "wa.me/" in c or "whatsapp.com" in c: return "whatsapp"
    if urlparse(content.strip()).scheme in ('http', 'https'): return "url"
    return "text"

async def format_qr_response(content: str, qr_type: str, settings):
    if qr_type == "url":
        escaped = html.escape(content)
        short = escaped if len(escaped) <= 45 else escaped[:42] + "..."
        header = f"{hbold('Найдена ссылка:')}\n{short}\n"

        is_safe, info = await check_url_safety(content, settings)
        if is_safe is None:
            safety = "⚠️ Не удалось проверить безопасность"
        elif is_safe:
            safety = f"{hbold('✅ Ссылка безопасна')}\nПроверено через Google Safe Browsing"
            # Кнопка перехода, если безопасно
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Перейти ↗️", url=content)]
            ])
        else:
            safety = f"{hbold('⛔️ ОПАСНО!')} {html.escape(info or '')}\nСсылка заблокирована."
            # Кнопка на образовательную статью, если опасно
            edu_link = "https://www.kaspersky.ru/resource-center/definitions/what-is-quishing"
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🛡 Как защититься от фишинга!", url=edu_link)]
            ])

        text = f"{header}\n{safety}"
        return text, keyboard

    # Для остальных типов просто текст (можно потом допилить)
    return f"{hbold('Содержимое QR:')}\n{hcode(content)}", None


# === Хэндлеры ===
async def start_handler(message: Message):
    await message.answer("Кидай фотку с QR-кодом — я всё расшифрую!\n\nПросто, быстро и без рекламы!")

async def help_handler(message: Message):
    await message.answer("Просто отправь фото с QR-кодом — я сканирую коды с изображений и присылаю их содержимое.\n\nДля безопасности я проверяю ссылки в Google Safe Browsing.")

async def tips_handler(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Чаевые автору ☕", url="https://pay.cloudtips.ru/p/221ed8a2")]])
    await message.answer("Если вам нравится этот бот, вы можете поблагодарить автора чаевыми.\n\nВсе средства пойдут на оплату серверов и кофе ☕", reply_markup=kb)

# Главный обработчик фото
async def handle_photo(message: Message, bot: Bot, settings):
    global total_scans, daily_scans, last_reset

    # Сброс ежедневной статистики
    if date.today() > last_reset:
        daily_scans = 0
        last_reset = date.today()

    # Антифлуд
    if is_rate_limited(message.from_user.id, settings):
        await message.answer("Слишком быстро! Подожди минуту.")
        return

    # Скачивание файла
    try:
        file = await bot.get_file(message.photo[-1].file_id)
        # Скачиваем файл в память (объект BytesIO), чтобы не засорять диск
        from io import BytesIO
        io_obj = BytesIO()
        await bot.download_file(file.file_path, destination=io_obj)
        photo_bytes = io_obj.getvalue()
    except Exception as e:
        logger.error(f"Ошибка при скачивании фото: {e}")
        await message.answer("Не удалось скачать фото.")
        return

    content = decode_qr_locally(photo_bytes, settings)
    if content:
        qr_type = detect_qr_type(content)
        text, kb = await format_qr_response(content, qr_type, settings)
        await message.answer(text, reply_markup=kb, parse_mode=ParseMode.HTML)

        total_scans += 1
        daily_scans += 1
    else:
        await message.answer("QR-код не найден 😔 Попробуй другое фото.")

# Статистика только для тебя
async def stats_handler(message: Message):
    if message.from_user.id != OWNER_ID:
        return
    text = f"Всего сканов: {total_scans}\nСегодня: {daily_scans}\nЗа всё время ты — король QR-сканеров 👑"
    await message.answer(text)


# === Запуск бота ===
async def run_bot(settings):
    bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    dp.message.register(start_handler, Command("start"))
    dp.message.register(help_handler, Command("help"))
    dp.message.register(tips_handler, Command("tips"))
    dp.message.register(handle_photo, F.photo)
    dp.message.register(stats_handler, Command("stats"))

    # Эта строчка убирает конфликт инстансов
    await bot.delete_webhook(drop_pending_updates=True)
    
    # ВОТ ИСПРАВЛЕНИЕ: передаем settings в polling, чтобы хендлеры его видели
    await dp.start_polling(bot, settings=settings)
