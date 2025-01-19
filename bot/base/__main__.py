import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram import F

from config_reader import config
from bot.handlers import default_commands

async def main():
    logging.basicConfig(level=logging.INFO)

    bot = Bot(token=config.bot_token.get_secret_value())
    dp = Dispatcher()

    dp.message.filter(F.chat.type == "private")

    dp.include_routers(default_commands.router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())