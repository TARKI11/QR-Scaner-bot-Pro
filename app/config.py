# app/config.py
import os
import logging
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding='utf-8',
        case_sensitive=False, # Pydantic будет искать переменные окружения в любом регистре
    )

    # Указываем точное имя переменной окружения в верхнем регистре
    bot_token: str = Field(..., env="BOT_TOKEN")
    gsb_api_key: str | None = Field(default=None, env="GSB_API_KEY")

    environment: str = Field(default="production", env="ENVIRONMENT")
    debug_mode: bool = Field(default=False)

    max_file_size: int = Field(default=10 * 1024 * 1024, env="MAX_FILE_SIZE")  # 10MB
    max_qr_content_length: int = Field(default=2048, env="MAX_QR_CONTENT_LENGTH")  # 2KB
    request_timeout: int = Field(default=30, env="REQUEST_TIMEOUT")  # 30 seconds
    rate_limit_requests: int = Field(default=10, env="RATE_LIMIT_REQUESTS")  # requests per minute
    rate_limit_window: int = Field(default=60, env="RATE_LIMIT_WINDOW")  # seconds

    @property
    def is_debug(self) -> bool:
        return self.environment.lower() == "development"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.debug_mode = self.is_debug

# settings = Settings() <-- УБРАНО!
