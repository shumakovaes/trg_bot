from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram import F


from bot.keyboards.kb_start import make_new_form_keyboard

router = Router()

@router.message(F.text, Command("start"))
async def make_new_form(message: Message):
    await message.answer(
        "Привет! Я бот по подбору сессий для настольных игр.\n"
        "Чтобы продолжить работу, вам необходимо заполнить анкету.\n\n"
        "Выберите, какую анкету вы сейчас хотите заполнить",
        reply_markup=make_new_form_keyboard()
    )
