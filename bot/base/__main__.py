import asyncio
import logging

from aiogram import Bot, Dispatcher, F
from aiogram_dialog import setup_dialogs

from config_reader import config

from bot.handlers import default_commands
from bot.dialogs import registration

async def main():
    logging.basicConfig(level=logging.INFO)

    bot = Bot(token=config.bot_token.get_secret_value())
    dp = Dispatcher()

    dp.message.filter(F.chat.type == "private")

    dp.include_routers(default_commands.router)
    dp.include_routers(registration.dialog)

    setup_dialogs(dp)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, skip_updates=True)


if __name__ == "__main__":
    asyncio.run(main())