# main.py
import asyncio
import logging
import os
import sys
from aiohttp import web
from app.config import Settings
from app.core import run_bot

# --- Logging Setup ---
# Setup logging before anything else
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Bot Task Management ---
async def start_bot_task(app: web.Application):
    """Starts the bot as a background task."""
    logger.info("Loading settings for the bot...")
    try:
        settings_instance = Settings()
        # Set logging level based on settings
        log_level = logging.DEBUG if settings_instance.is_debug else logging.INFO
        logging.getLogger().setLevel(log_level)
        logger.info("Settings loaded. Starting bot polling...")
        
        # Create and store the bot task
        app['bot_task'] = asyncio.create_task(run_bot(settings_instance))
        logger.info("Bot polling task created.")
        
    except Exception as e:
        logger.fatal(f"FATAL: Failed to initialize and start bot task: {e}", exc_info=True)
        # Stop the application if bot fails to start
        sys.exit(1)


async def stop_bot_task(app: web.Application):
    """Gracefully stops the bot task."""
    logger.info("Shutdown signal received. Stopping bot task...")
    if 'bot_task' in app and not app['bot_task'].done():
        app['bot_task'].cancel()
        try:
            await app['bot_task']
            logger.info("Bot task successfully cancelled.")
        except asyncio.CancelledError:
            logger.info("Bot task was already cancelled.")
        except Exception as e:
            logger.error(f"Error during bot task shutdown: {e}", exc_info=True)
    else:
        logger.info("No running bot task found to stop.")


# --- Web Server Setup ---
async def health_check(request: web.Request):
    """Health check endpoint for Render."""
    # Check if the bot task is running
    bot_task = request.app.get('bot_task')
    if bot_task and not bot_task.done():
        return web.Response(text="OK", status=200)
    
    # If the bot task has crashed, report unhealthy status
    logger.error("Health check failed: Bot task is not running.")
    return web.Response(text="Bot task is not running", status=503)


def main():
    """Main entry point for the application."""
    if 'BOT_TOKEN' not in os.environ or not os.environ['BOT_TOKEN']:
        logger.fatal("FATAL: BOT_TOKEN is not set in environment variables!")
        sys.exit(1)

    app = web.Application()
    
    # Register health check on both root and /health
    app.router.add_get("/", health_check)
    app.router.add_get("/health", health_check)

    # Register startup and shutdown signals
    app.on_startup.append(start_bot_task)
    app.on_shutdown.append(stop_bot_task)

    port = int(os.environ.get("PORT", 10000))
    
    logger.info(f"Starting web server on port {port}...")
    web.run_app(app, host="0.0.0.0", port=port, print=None)
    logger.info("Web server stopped.")


if __name__ == "__main__":
    main()
