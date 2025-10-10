# main.py
import asyncio
import logging
from app.config import Settings # Импортируем КЛАСС Settings
from app.core import main as core_main # Импортируем функцию main из app.core

async def main_async():
    # Создаем экземпляр настроек ТУТ, в начале выполнения main_async
    settings_instance = Settings()

    logger = logging.getLogger(__name__)
    logging.basicConfig(
        level=logging.DEBUG if settings_instance.is_debug else logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger.info("main.py started, settings loaded.")

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
