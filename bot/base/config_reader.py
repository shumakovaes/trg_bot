from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr


class BaseConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file="../.env", env_file_encoding="utf-8", extra="ignore")


class TelegramConfig(BaseConfig):
    model_config = SettingsConfigDict(env_prefix="tg_")

    bot_token: SecretStr
    # postgres_dsn: SecretStr


config = TelegramConfig()
