# main.py
import asyncio
import logging
import os
import sys
from aiohttp import web
from app.config import Settings
from app.core import run_bot # Импортируем переименованную функцию

logger = logging.getLogger(__name__)

# --- Функция для HTTP-сервера ---
async def health_check(request):
    # Простой эндпоинт для проверки работоспособности
    return web.Response(text="OK", status=200)

async def init_http_server(port):
    app = web.Application()
    app.router.add_get('/health', health_check)
    # Добавьте другие эндпоинты, если нужно
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info(f"HTTP Health Check Server started on port {port}")
    return runner

# --- Основная асинхронная функция ---
async def main_async():
    # Проверяем переменные окружения (как и раньше)
    if 'BOT_TOKEN' not in os.environ or not os.environ['BOT_TOKEN']:
        logger.error("FATAL: BOT_TOKEN is not set in environment variables!")
        sys.exit(1) # Завершаем процесс, если токен не установлен

    logger.info("main.py started, attempting to load settings.")

    try:
        settings_instance = Settings()
        logger.info("Settings loaded successfully.")
    except Exception as e:
        logger.error(f"FATAL: Failed to load settings: {e}")
        sys.exit(1)

    logging.basicConfig(
        level=logging.DEBUG if settings_instance.is_debug else logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    port = int(os.environ.get('PORT', 10000)) # Используем PORT от Render
    logger.info(f"Starting HTTP server on port {port}...")

    # Инициализируем HTTP-сервер
    http_runner = await init_http_server(port)

    # Запускаем aiogram бота в фоне
    logger.info("Starting bot logic in background...")
    bot_task = asyncio.create_task(run_bot(settings_instance))

    # Ждём завершения задачи бота (например, при KeyboardInterrupt)
    try:
        await bot_task
    except asyncio.CancelledError:
        logger.info("Bot task was cancelled.")
    finally:
        # Останавливаем HTTP-сервер при завершении
        logger.info("Shutting down HTTP server...")
        await http_runner.cleanup()
        logger.info("HTTP server shut down.")

if __name__ == "__main__":
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        logger.info("Application stopped by user")
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to run main application loop: {e}")
        sys.exit(1)
