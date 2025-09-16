# bot/base/config_reader.py
from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


def _resolve_env_file() -> Optional[str]:
    """
    Pick the first existing .env:
      1) bot/.env               (sibling of this file's parent)
      2) project root .env      (two levels up from this file)
    If none exist, return None (only process real environment variables).
    """
    here = Path(__file__).resolve()
    bot_dir = here.parent.parent           # .../bot
    root_dir = bot_dir.parent              # project root

    candidates = [
        bot_dir / ".env",                  # preferred: bot/.env (your current setup)
        root_dir / ".env",                 # fallback: project root .env
    ]
    for p in candidates:
        if p.is_file():
            return str(p)
    return None


_ENV_FILE = _resolve_env_file()


class TelegramConfig(BaseSettings):
    """
    Environment-driven configuration (Pydantic v2).
    - BOT_TOKEN is read from env or the chosen .env file.
    - POSTGRES_DSN likewise.
    """
    # Point pydantic-settings to the chosen .env (or None -> only OS env)
    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
    )

    # Use explicit aliases so names are stable regardless of field name/prefixes
    bot_token: SecretStr = Field(validation_alias="BOT_TOKEN")
    postgres_dsn: str = Field(default="", validation_alias="POSTGRES_DSN")


# Single, ready-to-use instance
config = TelegramConfig()

# --- Optional helpers (use if convenient) ---
def get_bot_token_str() -> str:
    """Return raw token string for libraries like aiogram."""
    return config.bot_token.get_secret_value()
