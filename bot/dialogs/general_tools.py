import logging
from typing import Optional

from aiogram.fsm.state import State
from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.common import Whenable
from aiogram_dialog.widgets.kbd import Cancel, Button
from aiogram_dialog.widgets.text import Const

from bot.db.current_requests import user


# RAISING ERRORS
# Raise error, when unexpected or duplicated id detected
async def raise_keyboard_error(callback: CallbackQuery | Message, item_type: str):
    logging.critical("unexpected or duplicated id {}".format(item_type))
    await callback.answer(text="Что-то пошло не так, попробуйте выбрать {} снова.\n"
                               "Если это не поможет, обратитесь в поддержку.".format(item_type),
                          show_alert=True)


# Raise error, when parameter is missing in dialog data
async def raise_dialog_data_error(manager: DialogManager, parameter: str, cause: Message | CallbackQuery):
    logging.critical("missing {} in dialog data".format(parameter))

    await cause.answer(text="Что-то пошло не так, обратитесь в поддержку.")

    await manager.done()


# HELPER FUNCTIONS
# Changes state differently in register and edit mode
async def switch_state(manager: DialogManager, next_state: dict[str, Optional[State]]):
    allowed_modes = ["edit", "register"]
    register_mode = manager.start_data.get("mode")

    if register_mode not in allowed_modes:
        logging.critical("unexpected register mode: {}".format(register_mode))
        await manager.done()
        return

    if not next_state.get(register_mode) is None:
        await manager.switch_to(next_state.get(register_mode))
        return
    await manager.done()
    return


# Finds item with given value in data from getter
async def get_item_by_key(getter, items_key: str, key: str, value: str, event: CallbackQuery | Message, error_message: str, allowed_zero_items: bool = False, find_lower: bool = False):
    data = await getter()
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
# TODO: display current value, in some cases, when mode = "register"
def need_to_display_current_value(data: dict, widget: Whenable, manager: DialogManager):
    return manager.start_data.get("mode") == "edit"


def is_edit_mode(data: dict, widget: Whenable, manager: DialogManager):
    return manager.start_data.get("mode") == "edit"


def is_register_mode(data: dict, widget: Whenable, manager: DialogManager):
    return manager.start_data.get("mode") == "register"


# WIDGETS
go_back_when_edit_mode = Cancel(Const("Назад"), when=is_edit_mode)


# ONCLICK GENERATOR
def generate_save_user_experience(role: str, next_state: State):
    async def save_user_experience(callback: CallbackQuery, button: Button, manager: DialogManager):
        experience_by_id = {
            "experience_0_{}".format(role): "Менее 3 месяцев",
            "experience_1_{}".format(role): "От 3 месяцев до 1 года",
            "experience_2_{}".format(role): "От 1 до 3 лет",
            "experience_3_{}".format(role): "От 3 до 10 лет",
            "experience_4_{}".format(role): "Более 10 лет",
        }
        experience = experience_by_id.get(button.widget_id)

        if experience is None:
            await raise_keyboard_error(callback, "опыт")
            return
        user[role]["experience"] = experience

        next_stages = {"edit": None, "register": next_state}
        await switch_state(manager, next_stages)

    return save_user_experience
