from __future__ import annotations
from aiogram.types import CallbackQuery, ContentType, Message
from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.text import Const, Format, Jinja
from aiogram_dialog.widgets.kbd import Button, Row, Column, Back, SwitchTo, Select, Group, Cancel, Start

from bot.dialogs.general_tools import generate_user_description
from bot.states.registration_states import Registration, Profile, PlayerForm, MasterForm

from bot.db.current_requests import get_user_general

# Profile dialog
profile_dialog = Dialog(
    # Checking profile
    Window(
        Jinja(
            "<b>Имя</b>: {{name}}\n"
            "<b>Возраст</b>: {{age}}\n"
            "<b>Город</b>: {{city}}\n"
            "<b>Часовой пояс</b>: {{time_zone}}\n"
            "<b>Роль</b>: {{role}}\n"
            "<b>Формат игры</b>: {{format}}\n"
            "<b>О себе</b>: {{about_info}}\n"
        ),
        Column(
            Row(
                # Ранее было state=Profile.check_player / Profile.check_master (их нет)
                Start(Const("Профиль игрока"), state=PlayerForm.checking_info, id="check_player_profile", data={"mode": "edit"}),
                Start(Const("Профиль мастера"), state=MasterForm.checking_info, id="check_master_profile", data={"mode": "edit"}),
            ),
            Row(
                Start(Const("Редактировать"), state=Profile.choosing_what_to_edit, id="edit_general", data={"mode": "edit"}),
            ),
            Back(Const("Назад"), id="back_to_start_general"),
        ),
        getter=get_user_general,
        state=Profile.checking_info,
    ),

    # Choosing what to edit
    Window(
        Const("Выбери, что изменить"),
        Column(
            Start(Const("Имя"), state=Registration.typing_nickname, id="edit_nickname_general", data={"mode": "edit"}),
            Start(Const("Возраст"), state=Registration.typing_age, id="edit_age_general", data={"mode": "edit"}),
            Start(Const("Город"), state=Registration.choosing_city, id="edit_city_general", data={"mode": "edit"}),
            # TODO: ? forbid changing time zone when city is default
            Start(Const("Часовой пояс"), state=Registration.choosing_time_zone, id="edit_time_zone_general", data={"mode": "edit"}),
            Start(Const("Роль"), state=Registration.choosing_role, id="edit_role_general", data={"mode": "edit"}),
            Start(Const("Формат игры"), state=Registration.choosing_format, id="edit_format_general", data={"mode": "edit"}),
            Start(Const("О себе"), state=Registration.typing_about_information, id="edit_about_info_general", data={"mode": "edit"}),
            Start(Const("Пройти регистрацию заново"), state=Registration.typing_nickname, id="register_again_general", data={"mode": "register"}),
            Back(Const("Назад"), id="back_to_checking_info_general"),
        ),
        state=Profile.choosing_what_to_edit,
    ),
)
