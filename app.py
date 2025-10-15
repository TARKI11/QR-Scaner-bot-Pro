import os
from flask import Flask, request, abort
import asyncio
from aiogram.types import Update
from bot_setup import bot, dp

app = Flask(__name__)

WEBHOOK_PATH = "/webhook"
BASE_WEBHOOK_URL = os.environ.get("BASE_WEBHOOK_URL")  # Адрес вашего сайта на PythonAnywhere

@app.route("/health", methods=["GET"])
def health():
    return "OK", 200

@app.route(WEBHOOK_PATH, methods=["POST"])
def webhook():
    if request.method == "POST":
        try:
            data = request.get_data().decode("utf-8")
            update = Update.model_validate_json(data)
        except Exception:
            return abort(400)
        asyncio.run(dp.feed_update(bot, update))
        return "", 200
    return abort(405)
