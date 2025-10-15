import os, asyncio
from bot_setup import bot

async def main():
    url = os.environ["BASE_WEBHOOK_URL"] + "/webhook"
    await bot.set_webhook(url=url)
    info = await bot.get_webhook_info()
    print(f"Webhook установлен: {info.url}")

if __name__ == "__main__":
    asyncio.run(main())
