from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder

from bot.base.cbdata import NewProfileCallbackFactory

def make_new_profile_keyboard() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardBuilder()

    keyboard.row(
        KeyboardButton(text="Мастер", callback_data=NewProfileCallbackFactory(role="master").pack()),
        KeyboardButton(text="Игрок", callback_data=NewProfileCallbackFactory(role="player").pack())
    )

    return keyboard.as_markup(resize_keyboard=True)