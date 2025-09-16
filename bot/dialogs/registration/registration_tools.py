from __future__ import annotations
from typing import Optional

from aiogram.fsm.state import State
from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button

from bot.dialogs.general_tools import raise_keyboard_error, switch_state

# ONCLICK GENERATORS
# Generate ONCLICK function to save experience for master and player
def generate_save_user_experience(role: str, next_state: State):
    async def save_user_experience(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
        experience_by_id = {
            f"experience_0_{role}": "Менее 3 месяцев",
            f"experience_1_{role}": "От 3 месяцев до 1 года",
            f"experience_2_{role}": "От 1 до 3 лет",
            f"experience_3_{role}": "От 3 до 10 лет",
            f"experience_4_{role}": "Более 10 лет",
        }
        experience = experience_by_id.get(button.widget_id)

        if experience is None:
            await raise_keyboard_error(callback, "опыт")
            return

        dialog_manager.dialog_data.setdefault(role, {})
        dialog_manager.dialog_data[role]['experience'] = experience  # TODO: persist

        next_stages = {"edit": None, "register": next_state}
        await switch_state(dialog_manager, next_stages)

    return save_user_experience


def generate_save_message_from_user_no_formatting_user(field: str, parameter: str, next_states: dict[str, Optional[State]]):
    async def save_message_from_user_no_formatting(message: Message, message_input: MessageInput, dialog_manager: DialogManager):
        dialog_manager.dialog_data.setdefault(field, {})
        dialog_manager.dialog_data[field][parameter] = message.text  # TODO: persist

        await switch_state(dialog_manager, next_states)

    return save_message_from_user_no_formatting
