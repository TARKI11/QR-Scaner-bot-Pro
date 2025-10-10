# app/config.py
import os
import logging
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

# Настройка логирования для модуля конфигурации
logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    # Указываем, что источником являются переменные окружения
    model_config = SettingsConfigDict(
        env_file=".env",  # Используем .env файл, если он есть (необязательно на Render)
        env_file_encoding='utf-8',
        case_sensitive=True,
        # Добавляем, чтобы Pydantic не пытался читать из других источников по умолчанию
        # strict=False, # Оставим по умолчанию
    )

    bot_token: str = Field(..., env="BOT_TOKEN") # Обязательное поле
    gsb_api_key: str | None = Field(default=None, env="GSB_API_KEY") # Необязательное поле

    environment: str = Field(default="production", env="ENVIRONMENT")
    debug_mode: bool = Field(default=False) # Будет установлено вручную

    max_file_size: int = Field(default=10 * 1024 * 1024, env="MAX_FILE_SIZE")  # 10MB
    max_qr_content_length: int = Field(default=2048, env="MAX_QR_CONTENT_LENGTH")  # 2KB
    request_timeout: int = Field(default=30, env="REQUEST_TIMEOUT")  # 30 seconds
    rate_limit_requests: int = Field(default=10, env="RATE_LIMIT_REQUESTS")  # requests per minute
    rate_limit_window: int = Field(default=60, env="RATE_LIMIT_WINDOW")  # seconds

    @property
    def is_debug(self) -> bool:
        return self.environment.lower() == "development"

    def __init__(self, **kwargs):
        # Логируем переменные окружения перед инициализацией Pydantic (для отладки)
        # Убедитесь, что удалили эти строки перед продакшеном, если они выводят чувствительные данные
        # logger.debug(f"ENV BOT_TOKEN set: {'BOT_TOKEN' in os.environ}")
        # logger.debug(f"ENV GSB_API_KEY set: {'GSB_API_KEY' in os.environ}")
        # logger.debug(f"ENVIRONMENT: {os.getenv('ENVIRONMENT', 'NOT_SET')}")
        super().__init__(**kwargs)
        # Устанавливаем debug_mode на основе environment после инициализации
        self.debug_mode = self.is_debug

# Создаем экземпляр настроек
settings = Settings()
