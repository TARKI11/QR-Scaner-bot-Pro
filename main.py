# main.py
import asyncio
import logging

async def main_async():
    from app.core import main
    try:
        await main()
    except KeyboardInterrupt:
        logger = logging.getLogger(__name__)
        logger.info("Bot stopped by user")
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to start bot: {e}")
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main_async())
    except Exception as e:
        # Логирование на случай ошибки в asyncio.run
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)
        logger.error(f"Error running asyncio loop: {e}")
        raise
