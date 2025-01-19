from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

# from bot.base.cbdata import NewProfileRoleCallbackFactory
#
# def make_new_form_keyboard() -> InlineKeyboardMarkup:
#     keyboard = InlineKeyboardBuilder()
#
#     keyboard.row(
#         InlineKeyboardButton(text="Мастер", callback_data=NewProfileRoleCallbackFactory(role="master").pack()),
#         InlineKeyboardButton(text="Игрок", callback_data=NewProfileRoleCallbackFactory(role="player").pack())
#     )
#
#     return keyboard.as_markup(resize_keyboard=True)