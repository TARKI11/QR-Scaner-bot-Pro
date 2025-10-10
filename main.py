# main.py
import asyncio
import logging
import os # Импортируем os для проверки переменных окружения
from app.config import Settings # Импортируем КЛАСС Settings
from app.core import main as core_main # Импортируем функцию main из app.core

async def main_async():
    logger = logging.getLogger(__name__)
    # --- ОТЛАДКА: Проверяем переменные окружения ---
    print("--- DEBUG: Environment Variables ---")
    print(f"BOT_TOKEN present: {'BOT_TOKEN' in os.environ}")
    print(f"GSB_API_KEY present: {'GSB_API_KEY' in os.environ}")
    print(f"ENVIRONMENT: {os.environ.get('ENVIRONMENT', 'NOT_SET')}")
    print(f"MAX_FILE_SIZE: {os.environ.get('MAX_FILE_SIZE', 'NOT_SET')}")
    # ВАЖНО: НЕ выводим сам токен в логи для безопасности!
    # print(f"BOT_TOKEN value: {os.environ.get('BOT_TOKEN', 'NOT_SET')}")
    print("------------------------------------")

    # Проверяем, есть ли BOT_TOKEN
    if 'BOT_TOKEN' not in os.environ or not os.environ['BOT_TOKEN']:
        logger.error("FATAL: BOT_TOKEN is not set in environment variables!")
        return # Выходим, если токен не установлен

    logger.info("main.py started, attempting to load settings.")

    try:
        # Создаем экземпляр настроек ТУТ, в надежде, что переменные теперь видны
        settings_instance = Settings()
        logger.info("Settings loaded successfully.")
    except Exception as e:
        logger.error(f"FATAL: Failed to load settings: {e}")
        raise # Пробрасываем ошибку, чтобы увидеть её в логах

    logging.basicConfig(
        level=logging.DEBUG if settings_instance.is_debug else logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger.info("Starting bot logic...")

    # Передаем экземпляр настроек в основную логику бота
    await core_main(settings_instance)

if __name__ == "__main__":
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        logger = logging.getLogger(__name__)
        logger.info("Bot stopped by user")
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to start bot: {e}")
        raise
