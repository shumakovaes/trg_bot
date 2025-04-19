import logging
import random
from typing import Optional

from magic_filter import F

from aiogram.fsm.state import State
from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.common import Whenable
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Cancel, Button
from aiogram_dialog.widgets.text import Const, Jinja, Multi, List
from typing_extensions import Any

from bot.db.current_requests import user
from bot.states.games_states import GameCreation


# RAISING ERRORS
# Raise error, when unexpected or duplicated id detected
async def raise_keyboard_error(event: Optional[CallbackQuery | Message], item_type: str):
    logging.critical("unexpected or duplicated id {}".format(item_type))
    if event is None:
        return

    if type(event) == Message:
        await event.answer(
            text="Что-то пошло не так, попробуйте выбрать {} снова.\n"
                 "Если это не поможет, обратитесь в поддержку.".format(item_type))
    else:
        await event.answer(
            text="Что-то пошло не так, попробуйте выбрать {} снова.\n"
                 "Если это не поможет, обратитесь в поддержку.".format(item_type), show_alert=True)


# Raise error, when parameter is missing in dialog data
async def raise_dialog_data_error(dialog_manager: DialogManager, parameter: str, event: Message | CallbackQuery):
    logging.critical("missing {} in dialog data".format(parameter))

    if type(event) == Message:
        await event.answer(text="Что-то пошло не так, обратитесь в поддержку.")
    else:
        await event.answer(text="Что-то пошло не так, обратитесь в поддержку.", show_alert=True)

    await dialog_manager.done()


# HELPER FUNCTIONS
# Changes state differently in register and edit mode
async def switch_state(dialog_manager: DialogManager, next_state: dict[str, Optional[State]]):
    allowed_modes = ["edit", "register"]
    register_mode = dialog_manager.start_data.get("mode")

    if register_mode not in allowed_modes:
        logging.critical("unexpected register mode: {}".format(register_mode))
        await dialog_manager.done()
        return

    if not next_state.get(register_mode) is None:
        await dialog_manager.switch_to(next_state.get(register_mode))
        return
    await dialog_manager.done()
    return


async def generate_random_id():
    max_id = 1000000
    random_id = str(random.randint(0, max_id - 1))

    return "id_" + '0' * (6 - len(random_id)) + random_id


async def start_game_creation(dialog_manager: DialogManager):
    try:
        is_defaults_filled = user["master"]["is_filled"]
    except KeyError:
        logging.critical("missing is_filled field")
        await dialog_manager.done()
        return

    if is_defaults_filled:
        await dialog_manager.start(state=GameCreation.choosing_default, data={"mode": "register"})
    else:
        await dialog_manager.start(GameCreation.typing_title, data={"mode": "register"})


# Finds item with given value in data from getter
async def get_item_by_key(data: dict[str, Any], items_key: str, key: str, value: str, event: Optional[CallbackQuery | Message],
                          error_message: str, allowed_zero_items: bool = False, find_lower: bool = False):
    items = data[items_key]
    if find_lower:
        item = [item for item in items if item.get(key).lower() == value.lower()]
    else:
        item = [item for item in items if item.get(key) == value]
    if len(item) > 1 or (not allowed_zero_items and len(item) == 0):
        await raise_keyboard_error(event, error_message)
        return

    if len(item) == 1:
        return item[0]
    return None


# SELECTORS
# TODO: display current value, in some cases, when mode = "register" (add mode "re-register")
def need_to_display_current_value(data: dict, widget: Whenable, dialog_manager: DialogManager):
    return dialog_manager.start_data.get("mode") == "edit"


def is_edit_mode(data: dict, widget: Whenable, dialog_manager: DialogManager):
    return dialog_manager.start_data.get("mode") == "edit"


def is_register_mode(data: dict, widget: Whenable, dialog_manager: DialogManager):
    return dialog_manager.start_data.get("mode") == "register"


# WIDGETS
go_back_when_edit_mode = Cancel(Const("Назад"), when=is_edit_mode)

def generate_user_description():
    user_description = Jinja(
        "<b>Имя</b>: {{name}}\n" +
        "<b>Возраст</b>: {{age}}\n" +
        "<b>Город</b>: {{city}}\n" +
        "<b>Часовой пояс</b>: {{time_zone}}\n" +
        "<b>Роль</b>: {{role}}\n" +
        "<b>Формат игры</b>: {{format}}\n" +
        "<b>О себе</b>: {{about_info}}\n"
    )

    return user_description


def generate_player_description():
    player_description = Multi(
    generate_user_description(),

        Jinja(
            "<b>Опыт</b>: {{experience}}",
            when=F["experience_provided"],
        ),
        Jinja(
            "<b>Оплата</b>: {{payment}}",
            when = F["payment_provided"],
        ),
        Multi(
            Jinja(
            "<b>Системы</b>: "
            ),
            List(
                Jinja("{{item}}"),
                items="systems",
                sep=", "
            ),
            sep="",
            when=F["systems_provided"],
        ),
        Jinja(
            "<b>Рейтинг</b>: {{rating}}",
            when=F["has_rating"],
        ),
        sep='\n'
    )

    return player_description


def generate_master_description():
    master_description = Multi(
        generate_user_description(),
        Jinja(
            "<b>Опыт ведения игр</b>: {{experience}}\n",
            when=F["experience_provided"],
        ),
        Jinja(
            "<b>Рейтинг</b>: {{rating}}",
            when=F["has_rating"],
        ),
        sep='\n',
    )

    return master_description


# ONCLICK GENERATORS
# TODO: ? add symbols limit


def generate_save_message_from_user_formatting(field: str, parameter: str, next_states: dict[str, Optional[State]]):
    async def save_message_from_user_formatting(message: Message, message_input: MessageInput, dialog_manager: DialogManager):
        user[field][parameter] = message.html_text

        await switch_state(dialog_manager, next_states)

    return save_message_from_user_formatting


# ON START FUNCTIONS
async def copy_start_data_to_dialog_data(data: dict[str, Any], dialog_manager: DialogManager):
    for key, value in data.items():
        dialog_manager.dialog_data[key] = value
