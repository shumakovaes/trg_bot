from typing import Optional

from aiogram.types import CallbackQuery, ContentType, Message
from aiogram_dialog import Dialog, Window, DialogManager, ShowMode
from aiogram_dialog.widgets.common import Whenable
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.text import Const, Format, Multi, List, Jinja
from aiogram_dialog.widgets.kbd import Button, Row, Column, Back, SwitchTo, Select, Group, Cancel, Start

from bot.dialogs.general_tools import need_to_display_current_value, go_back_when_edit_mode, raise_keyboard_error, \
    switch_state
from bot.dialogs.registration.registration_tools import generate_save_user_experience, \
    generate_save_message_from_user_no_formatting_user
from bot.states.registration_states import Registration, Profile, PlayerForm, MasterForm

from bot.db.current_requests import user, get_user_master


# SELECTORS
def is_user_playing_online(data: Optional[dict], widget: Optional[Whenable], dialog_manager: Optional[DialogManager]):
    role = user["general"].get("format")
    return role == "Онлайн" or role == "Оффлайн и Онлайн"


def is_user_playing_offline(data: Optional[dict], widget: Optional[Whenable], dialog_manager: Optional[DialogManager]):
    role = user["general"].get("format")
    return role == "Оффлайн" or role == "Оффлайн и Онлайн"


# Saving player form settings (ONCLICK)
save_experience_master = generate_save_user_experience("master", MasterForm.choosing_cost)


async def save_cost(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    next_states = {"edit": None, "register": None}

    if button.widget_id == "cost_free":
        next_states = {"edit": None, "register": MasterForm.typing_place}
        user["master"]["cost"] = "Бесплатно"
    elif button.widget_id == "cost_paid":
        user["master"]["cost"] = "Платно"
        next_states = {"edit": MasterForm.typing_cost, "register": MasterForm.typing_cost}
    else:
        await raise_keyboard_error(callback, "цену")
        return

    await switch_state(dialog_manager, next_states)


async def save_cost_number(message: Message, message_input: MessageInput, dialog_manager: DialogManager):
    user["master"]["cost"] = user["master"]["cost"] + ". " + message.text

    if is_user_playing_offline(None, None, None):
        next_states = {"edit": None, "register": MasterForm.typing_place}
    else:
        next_states = {"edit": None, "register": MasterForm.typing_platform}
    await switch_state(dialog_manager, next_states)


async def save_place(message: Message, message_input: MessageInput, dialog_manager: DialogManager):
    user["master"]["place"] = message.text

    if is_user_playing_online(None, None, None):
        next_states = {"edit": None, "register": MasterForm.typing_platform}
    else:
        next_states = {"edit": None, "register": MasterForm.typing_requirements}
    await switch_state(dialog_manager, next_states)


save_platform = generate_save_message_from_user_no_formatting_user("master", "platform", {"edit": None, "register": MasterForm.typing_requirements})


save_requirements = generate_save_message_from_user_no_formatting_user("master", "requirements", {"edit": None, "register": None})


# TODO: add ability to skip some fields
# TODO: add time field
# TODO: add ability to clear some fields
# Master form
master_form_dialog = Dialog(
    # Checking form
    Window(
        Multi(
            Jinja(
                "Это ваша анкета мастера, заполнив её, вы установите значения по умолчанию для ваших игр. Вы сможете использовать их или выбрать другие параметры при создании заявки.\n\n" +
                "<b>Опыт</b>: {{experience}}\n" +
                "<b>Цена</b>: {{cost}}"
            ),
            Jinja(
                text="<b>Место проведения</b>: {{place}}",
                when=is_user_playing_offline
            ),
            Jinja(
                text="<b>Платформа</b>: {{platform}}",
                when=is_user_playing_online

            ),
            Jinja(
                # "<b>Время проведения</b>: {{time}}\n" +
                "<b>Требования к игрокам</b>: {{requirements}}"
            ),
            sep='\n'
        ),

        SwitchTo(Const("Редактировать анкету"), state=MasterForm.choosing_what_to_edit, id="edit_form_player",
                 show_mode=ShowMode.SEND),
        Cancel(Const("Выйти")),

        state=MasterForm.checking_info,
    ),
    # Editing form
    Window(
        Const("Выберите, что хотите отредактировать."),

        Start(Const("Опыт"), state=MasterForm.choosing_experience, id="edit_experience_master", data={"mode": "edit"}),
        Start(Const("Цена"), state=MasterForm.choosing_cost, id="edit_cost_master", data={"mode": "edit"}),
        Start(Const("Место проведения"), state=MasterForm.typing_place, id="edit_place_master", data={"mode": "edit"}, when=is_user_playing_offline),
        Start(Const("Платформа"), state=MasterForm.typing_platform, id="edit_place_master", data={"mode": "edit"}, when=is_user_playing_online),
        Start(Const("Требования у игрокам"), state=MasterForm.typing_requirements, id="edit_requirements_master",
              data={"mode": "edit"}),
        Start(Const("Заполнить анкету заново"), state=MasterForm.choosing_experience, id="register_again_master",
              data={"mode": "register"}),
        Back(Const("Назад"), id="back_to_checking_info_master"),

        state=MasterForm.choosing_what_to_edit,
    ),
    # Getting experience
    Window(
        Const("Каков ваш опыт в НРИ в качестве мастера?"),
        Jinja("\n<b>Текущее значение</b>: {{experience}}", when=need_to_display_current_value),

        Button(Const("Менее 3 месяцев"), id="experience_0_master", on_click=save_experience_master),
        Button(Const("От 3 месяцев до 1 года"), id="experience_1_master", on_click=save_experience_master),
        Button(Const("От 1 до 3 лет"), id="experience_2_master", on_click=save_experience_master),
        Button(Const("От 3 до 10 лет"), id="experience_3_master", on_click=save_experience_master),
        Button(Const("Более 10 лет"), id="experience_4_master", on_click=save_experience_master),

        go_back_when_edit_mode,
        state=MasterForm.choosing_experience,
    ),
    Window(
        Const("Какие игры вы планируете проводить?"),
        Jinja("\n<b>Текущее значение</b>: {{cost}}", when=need_to_display_current_value),

        Button(Const("Бесплатные"), id="cost_free", on_click=save_cost),
        Button(Const("Платные"), id="cost_paid", on_click=save_cost),

        go_back_when_edit_mode,
        state=MasterForm.choosing_cost,
    ),
    # Getting cost
    Window(
        Const("Сколько вы планируете брать за проведение сессии? Введите ответ в свободной форме"),
        Jinja("\n<b>Текущее значение</b>: {{cost}}", when=need_to_display_current_value),

        MessageInput(func=save_cost_number, content_types=[ContentType.TEXT]),

        go_back_when_edit_mode,
        state=MasterForm.typing_cost,
    ),
    # Getting place
    Window(
        Const("Где вы планируете проводить игры?\nПожалуйста, не приглашайте игроков к себе домой, это может быть опасно, сессии нужно проводить в публичных местах.\nТакже не стоит указывать точный адрес, эта информация будет доступна всем пользователям бота. Лучше всего указать район."),
        Jinja("\n<b>Текущее значение</b>: {{place}}", when=need_to_display_current_value),

        MessageInput(func=save_place, content_types=[ContentType.TEXT]),

        go_back_when_edit_mode,
        state=MasterForm.typing_place,
    ),
    # Getting platform
    # TODO: add choice of platform (like roll20 or foundry) and connection way (discord, telegram, etc)
    Window(
        Const("Какую платформу вы будете использовать для проведения игр? Укажите её и способ общения во время игры."),
        Jinja("\n<b>Текущее значение</b>: {{platform}}", when=need_to_display_current_value),

        MessageInput(func=save_platform, content_types=[ContentType.TEXT]),

        go_back_when_edit_mode,
        state=MasterForm.typing_platform,
    ),
    Window(
        Const("Каким требованиям должны удовлетворять игроки, которых вы ищите?"),
        Jinja("\n<b>Текущее значение</b>: {{requirements}}", when=need_to_display_current_value),

        MessageInput(func=save_requirements, content_types=[ContentType.TEXT]),

        go_back_when_edit_mode,
        state=MasterForm.typing_requirements,
    ),
    getter=get_user_master,
)
