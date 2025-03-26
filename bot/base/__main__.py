import asyncio
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram_dialog import setup_dialogs
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from config_reader import config

from bot.handlers import default_commands
from bot.dialogs.registration import dialog as registration_dialog
from bot.dialogs.profile import dialog as profile_dialog
from bot.db import requests

async def main():
    logging.basicConfig(level=logging.INFO)

    # COMMENT THESE STRINGS TO TEST THE BOT
    engine = create_async_engine(
        str(config.postgres_dsn.get_secret_value()).replace('postgresql://', 'postgresql+asyncpg://'),
        future=True,
        echo=False
    )
    db_pool = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    # COMMENT THESE STRINGS TO TEST THE BOT

    storage = MemoryStorage()
    bot = Bot(token=config.bot_token.get_secret_value())
    dp = Dispatcher(storage=storage)

    dp.message.filter(F.chat.type == "private")

    dp.include_routers(default_commands.router)
    dp.include_routers(registration_dialog)
    dp.include_routers(profile_dialog)
    dp.include_routers(requests.router)  # Include the router from requests.py; COMMENT THIS STRING TO TEST THE BOT

    setup_dialogs(dp)

    async with db_pool() as session: # COMMENT THIS STRING TO TEST THE BOT
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())
