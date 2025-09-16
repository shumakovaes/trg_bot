from __future__ import annotations

from aiogram.types import CallbackQuery, ContentType, Message
from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.widgets.common import Whenable
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.text import Const, Format, Jinja, Multi
from aiogram_dialog.widgets.kbd import Button, Row, Column, Start, Select, Cancel

from bot.dialogs.general_tools import need_to_display_current_value, go_back_when_edit_mode, switch_state, \
    raise_keyboard_error, get_item_by_key
from bot.db.current_requests import get_user_general
from bot.dialogs.registration.registration_tools import generate_save_message_from_user_no_formatting_user
from bot.states.registration_states import Registration, PlayerForm, MasterForm, Profile


def text_input_handler_factory(field: str, parameter: str, next_states: dict[str, Whenable]):
    async def handle(message: Message, message_input: MessageInput, dialog_manager: DialogManager):
        dialog_manager.dialog_data.setdefault(field, {})
        dialog_manager.dialog_data[field][parameter] = message.text  # TODO: persist
        await switch_state(dialog_manager, next_states)
    return handle


def html_input_handler_factory(field: str, parameter: str, next_states: dict[str, Whenable]):
    async def handle(message: Message, message_input: MessageInput, dialog_manager: DialogManager):
        dialog_manager.dialog_data.setdefault(field, {})
        dialog_manager.dialog_data[field][parameter] = message.html_text  # TODO: persist
        await switch_state(dialog_manager, next_states)
    return handle


registration_dialog = Dialog(
    # typing nickname
    Window(
        Multi(
            Const("Введите имя:"),
            Jinja("\n<b>Текущее значение</b>: {{name}}", when=need_to_display_current_value),
        ),
        MessageInput(
            html_input_handler_factory("general", "name", {"edit": Profile.choosing_what_to_edit,
                                                           "register": Registration.typing_age})
        ),
        go_back_when_edit_mode,
        Cancel(Const("Отмена")),
        getter=get_user_general,
        state=Registration.typing_nickname,
    ),

    # typing age
    Window(
        Multi(
            Const("Введите возраст (число):"),
            Jinja("\n<b>Текущее значение</b>: {{age}}", when=need_to_display_current_value),
        ),
        MessageInput(
            text_input_handler_factory("general", "age", {"edit": Profile.choosing_what_to_edit,
                                                          "register": Registration.choosing_city})
        ),
        go_back_when_edit_mode,
        Cancel(Const("Отмена")),
        getter=get_user_general,
        state=Registration.typing_age,
    ),

    # choosing city
    Window(
        Multi(
            Const("Выберите город:"),
            Jinja("\n<b>Текущее значение</b>: {{city}}", when=need_to_display_current_value),
        ),
        Select(
            Format("{item[city]}"),
            id="city_select",
            item_id_getter=lambda x: x["id"],
            items="cities",
            on_click=lambda c, b, m, d: None,
        ),
        go_back_when_edit_mode,
        Cancel(Const("Отмена")),
        getter=get_user_general,
        state=Registration.choosing_city,
    ),

    # choosing time zone
    Window(
        Multi(
            Const("Выберите часовой пояс:"),
            Jinja("\n<b>Текущее значение</b>: {{time_zone}}", when=need_to_display_current_value),
        ),
        Select(
            Format("{item[time_zone]}"),
            id="tz_select",
            item_id_getter=lambda x: x["id"],
            items="time_zones",
            on_click=lambda c, b, m, d: None,
        ),
        go_back_when_edit_mode,
        Cancel(Const("Отмена")),
        getter=get_user_general,
        state=Registration.choosing_time_zone,
    ),

    # choosing role
    Window(
        Multi(
            Const("Выберите роль:"),
            Jinja("\n<b>Текущее значение</b>: {{role}}", when=need_to_display_current_value),
        ),
        Row(
            Button(Const("Игрок"), id="choose_role_player",
                   on_click=lambda c, b, m: m.dialog_data.setdefault("general", {}) or m.dialog_data["general"].update({"role": "player"})),
            Button(Const("Мастер"), id="choose_role_master",
                   on_click=lambda c, b, m: m.dialog_data.setdefault("general", {}) or m.dialog_data["general"].update({"role": "master"})),
        ),
        go_back_when_edit_mode,
        Cancel(Const("Отмена")),
        getter=get_user_general,
        state=Registration.choosing_role,
    ),

    # choosing format
    Window(
        Multi(
            Const("Выберите формат игры:"),
            Jinja("\n<b>Текущее значение</b>: {{format}}", when=need_to_display_current_value),
        ),
        Row(
            Button(Const("Онлайн"), id="choose_format_online",
                   on_click=lambda c, b, m: m.dialog_data.setdefault("general", {}) or m.dialog_data["general"].update({"format": "online"})),
            Button(Const("Оффлайн"), id="choose_format_offline",
                   on_click=lambda c, b, m: m.dialog_data.setdefault("general", {}) or m.dialog_data["general"].update({"format": "offline"})),
            Button(Const("Гибрид"), id="choose_format_hybrid",
                   on_click=lambda c, b, m: m.dialog_data.setdefault("general", {}) or m.dialog_data["general"].update({"format": "hybrid"})),
        ),
        go_back_when_edit_mode,
        Cancel(Const("Отмена")),
        getter=get_user_general,
        state=Registration.choosing_format,
    ),

    # typing about info
    Window(
        Multi(
            Const("Напишите пару слов о себе:"),
            Jinja("\n<b>Текущее значение</b>: {{about_info}}", when=need_to_display_current_value),
        ),
        MessageInput(
            html_input_handler_factory("general", "about_info", {"edit": Profile.choosing_what_to_edit,
                                                                 "register": Profile.checking_info})
        ),
        go_back_when_edit_mode,
        Cancel(Const("Отмена")),
        getter=get_user_general,
        state=Registration.typing_about_information,
    ),
)
