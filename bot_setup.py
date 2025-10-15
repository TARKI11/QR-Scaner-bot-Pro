import os
from aiogram import Bot, Dispatcher, Router
from aiogram.filters import CommandStart
from aiogram.types import Message

BOT_TOKEN = os.environ["BOT_TOKEN"]  # Токен бота считывается из переменных окружения

bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher()
router = Router()

@router.message(CommandStart())
async def start_cmd(msg: Message):
    await msg.answer("Привет! Я работаю через вебхуки на PythonAnywhere.")

@router.message()
async def echo(msg: Message):
    await msg.answer(msg.text or "(без текста)")

dp.include_router(router)
