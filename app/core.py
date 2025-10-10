async def help_handler(message: Message):
    help_text = (
    f"{hbold('ℹ️ QRScanerPro — помощь')}\n\n"
    f"• Сканирует QR коды любой сложности\n"
    f"• Мгновенно выдаёт результат\n"
    f"• Проверяет на безопасность\n"
    f"• Без рекламы и ограничений\n\n"
    f"{hbold('Как использовать:')}\n"
    f"1. Отправь фото с QR\n"
    f"2. Получи ответ\n\n"
    f"{hbold('Советы:')} хорошее освещение, чёткий код, до 10MB\n"
    f"{hbold('Лимиты:')} 10 запросов/мин\n\n"
    f"Команды: /start, /help, /tips\n\n"
    f"Отправь фото прямо сейчас!"
    )
    await message.answer(help_text)

async def tips_handler(message: Message):
    tips_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💸 Оставить чаевые через CloudTips", url="https://pay.cloudtips.ru/p/221ed8a2")]
        ]
    )
    tips_text = (
        f"{hbold('💸 Оставить чаевые')}\n\n"
        f"По СБП или картой Мир — просто и быстро.\n"
        f"Все донаты идут на развитие бота!\n\n"
        f"👇 Нажмите кнопку для перевода:"
    )
    await message.answer(tips_text, reply_markup=tips_keyboard)



async def handle_photo(message: Message):
    await message.reply("Я получил вашу фотографию! Сейчас попробую найти QR-код...")

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
            # Здесь твоя логика отправки ответа с QR
        # else, если результата нет — тоже ответ пользователю
    except Exception as e:
        await message.answer(f"Ошибка при обработке: {e}")


dp.message.register(start_handler, Command("start"))
dp.message.register(help_handler, Command("help"))
dp.message.register(tips_handler, Command("tips"))
dp.message.register(handle_photo, F.photo)
