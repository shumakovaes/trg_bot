import asyncio
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram_dialog import setup_dialogs

from bot.handlers.default_commands import set_main_menu
from config_reader import config

from bot.handlers import default_commands
from bot.dialogs.registration.registration import registration_dialog
from bot.dialogs.registration.profile import profile_dialog
from bot.dialogs.registration.player_form import player_form_dialog
from bot.dialogs.registration.master_form import master_form_dialog
from bot.dialogs.games.all_games import all_games_dialog


async def main():
    logging.basicConfig(level=logging.INFO)

    # COMMENT THESE STRINGS TO TEST THE BOT
    # engine = create_async_engine(
    #     str(config.postgres_dsn.get_secret_value()).replace('postgresql://', 'postgresql+asyncpg://'),
    #     future=True,
    #     echo=False
    # )
    # db_pool = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    # COMMENT THESE STRINGS TO TEST THE BOT

    storage = MemoryStorage()
    bot = Bot(
        token=config.bot_token.get_secret_value(),
        default = DefaultBotProperties(
            parse_mode=ParseMode.HTML,
            disable_notification=True,
            link_preview_is_disabled=True,
        )
    )
    await set_main_menu(bot)
    dp = Dispatcher(storage=storage)

    dp.message.filter(F.chat.type == "private")

    dp.include_routers(default_commands.router)
    dp.include_routers(registration_dialog)
    dp.include_routers(profile_dialog)
    dp.include_routers(player_form_dialog)
    dp.include_routers(master_form_dialog)
    dp.include_routers(all_games_dialog)
    # dp.include_routers(requests.router)  # Include the router from requests.py; COMMENT THIS STRING TO TEST THE BOT

    setup_dialogs(dp)

    # async with db_pool() as session:  # COMMENT THIS STRING TO TEST THE BOT
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, skip_updates=True)


if __name__ == "__main__":
    asyncio.run(main())
