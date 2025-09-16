# bot/base/__main__.py
from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram_dialog import setup_dialogs

from bot.base.config_reader import config, get_bot_token_str
from bot.base.db_middleware import build_session_maker, DbSessionMiddleware

# --- handlers / routers ---
try:
    from bot.handlers.default_commands import router as default_commands_router  # type: ignore
except Exception:
    default_commands_router = None
from bot.handlers.default_commands import set_main_menu

# --- dialogs (каждый Dialog — это Router) ---
from bot.dialogs.registration.registration import registration_dialog
from bot.dialogs.registration.profile import profile_dialog
from bot.dialogs.registration.player_form import player_form_dialog
from bot.dialogs.registration.master_form import master_form_dialog

from bot.dialogs.games.all_games import all_games_dialog
from bot.dialogs.games.game_creation import game_creation_dialog
from bot.dialogs.games.game_inspection import game_inspection_dialog
from bot.dialogs.games.searching_game import searching_game_dialog


async def main() -> None:
    logging.basicConfig(level=logging.INFO)

    # Бот и диспетчер
    bot = Bot(
        token=get_bot_token_str(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    # БД: engine + sessionmaker + middleware (кладёт AsyncSession в data['db_session'])
    engine, session_maker = build_session_maker(config.postgres_dsn, echo=False)
    dp.update.middleware(DbSessionMiddleware(session_maker))

    # Роутеры с командами/хэндлерами
    if default_commands_router is not None:
        dp.include_router(default_commands_router)

    # Диалоги (каждый Dialog — это Router)
    dp.include_router(registration_dialog)
    dp.include_router(profile_dialog)
    dp.include_router(player_form_dialog)
    dp.include_router(master_form_dialog)

    dp.include_router(all_games_dialog)
    dp.include_router(game_creation_dialog)
    dp.include_router(game_inspection_dialog)
    dp.include_router(searching_game_dialog)

    # Инициализация aiogram-dialog
    setup_dialogs(dp)

    # Меню команд
    try:
        await set_main_menu(bot)
    except Exception as e:
        logging.warning("Failed to set main menu: %s", e)

    # Старт
    try:
        await dp.start_polling(bot)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
