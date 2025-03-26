from aiogram.types import CallbackQuery, ContentType, Message
from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.widgets.kbd import Button, Row, Column, Back, SwitchTo, Select, Group, Cancel, Start

from bot.states.general_states import Registration, Profile, PlayerForm, MasterForm

# TODO: change to database query
from bot.dialogs.registration import  user

# Passing arguments to dialog (GETTERS)
async def get_user(**kwargs):
    return user

# Profile dialog
dialog = Dialog(
    # Checking profile
    Window(
        # TODO: access to database
        Format(
            "Ваш профиль:\n" +
            "Имя: {name}\n" +
            "Возраст: {age}\n" +
            "Город: {city}\n" +
            "Часовой пояс: {time_zone}\n" +
            "Роль: {role}\n" +
            "Формат игры: {format}\n" +
            "О себе: {about_info}.\n",
        ),
        SwitchTo(Const("Редактировать анкету"), state=Profile.choosing_what_to_edit, id="edit_form"),
        Row(Start(Const("Анкета игрока"), state=PlayerForm.player_form, id="player_form_from_profile"),
            Start(Const("Анкета мастера"), state=MasterForm.master_form, id="master_form_from_profile"),),
        Cancel(Const("Выйти")),
        getter=get_user,
        state=Profile.checking_info,
    ),
    # Editing profile
    Window(
        Const("Выберите, что хотите отредактировать."),

        Start(Const("Имя"), state=Registration.typing_nickname, id="edit_nickname", data={"type": "edit"}),
        Start(Const("Возраст"), state=Registration.typing_age, id="edit_age", data={"type": "edit"}),
        Start(Const("Город"), state=Registration.choosing_city, id="edit_city", data={"type": "edit"}),
        Start(Const("Часовой пояс"), state=Registration.choosing_time_zone, id="edit_time_zone", data={"type": "edit"}),
        Start(Const("Роль"), state=Registration.choosing_role, id="edit_role", data={"type": "edit"}),
        Start(Const("Формат игры"), state=Registration.choosing_format, id="edit_format", data={"type": "edit"}),
        Start(Const("О себе"), state=Registration.typing_about_information, id="edit_about_info", data={"type": "edit"}),

        Start(Const("Пройти регистрацию заново"), state=Registration.typing_nickname, id="register_again", data={"type": "register"}),
        Back(Const("Назад"), id="back_to_checking_info"),
        state=Profile.choosing_what_to_edit,
    )
)