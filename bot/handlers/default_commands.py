from aiogram import Router
from aiogram.types import Message, CallbackQuery

from bot.keyboards.keyboards import make_newprofile_keyboard

router = Router()


@router.message(commands=["start"])
async def new_message(message: Message):
    await message.answer(
        "Привет! Я бот по подбору сессий для настольных игр.\n"
        "Чтобы продолжить работу, вам необходимо заполнить анкету.\n\n"
        "Выберите, какую анкету вы сейчас хотите заполнить",
        reply_markup=make_newprofile_keyboard()
    )
