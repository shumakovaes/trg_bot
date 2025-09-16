from __future__ import annotations
import logging
import random
from typing import Optional

from magic_filter import F
from typing import Any, Dict, Optional, Union

from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager

from aiogram.fsm.state import State
from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.common import Whenable
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Cancel, Button
from aiogram_dialog.widgets.text import Const, Jinja, Multi, List
from typing_extensions import Any
from bot.db.current_requests import get_user_master
from bot.states.games_states import GameCreation, SearchingGame

# SWITCHES
async def switch_state(dialog_manager: DialogManager, next_state: dict[str, Optional[State]]):
    register_mode = dialog_manager.start_data.get("mode")
    if register_mode not in next_state.keys():
        logging.critical("invalid switch_state keys")
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
        master = await get_user_master(dialog_manager)
        is_defaults_filled = bool(master.get("is_filled", False))
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
                          error_message: str, allowed_zero_items=True):
    item = list(filter(lambda d: str(d.get(key)) == value, data.get(items_key, [])))

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


# NOTIFICATIONS
async def raise_keyboard_error(event: Optional[CallbackQuery | Message], item_type: str):
    error_message = f"Ошибка выбора: {item_type.lower()}.\nПожалуйста, сделай выбор из предложенных вариантов, используя кнопки."
    if event is not None:
        if isinstance(event, Message):
            await event.answer(text=error_message)
        else:
            await event.message.answer(text=error_message)


# TEXTS
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
            "<b>Опыт игр</b>: {{experience}}\n",
            when=F["experience_provided"],
        ),
        Jinja(
            "<b>Рейтинг</b>: {{rating}}",
            when=F["has_rating"],
        ),
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
    )

    return master_description


def generate_save_message_from_user_formatting(field: str, parameter: str, next_states: dict[str, Optional[State]]):
    async def save_message_from_user_formatting(message: Message, message_input: MessageInput, dialog_manager: DialogManager):
        dialog_manager.dialog_data.setdefault(field, {})
        dialog_manager.dialog_data[field][parameter] = message.html_text  # TODO: persist via DB setter

        await switch_state(dialog_manager, next_states)

    return save_message_from_user_formatting


# ON START FUNCTIONS
async def copy_start_data_to_dialog_data(data: dict[str, Any], dialog_manager: DialogManager):
    for key, value in data.items():
        dialog_manager.dialog_data[key] = value

async def raise_dialog_data_error(dialog_manager: DialogManager, key: str, event: Optional[CallbackQuery | Message] = None):
    import logging
    logging.critical("Dialog data missing required key '%s'. dialog_data=%s", key, dict(dialog_manager.dialog_data or {}))
    text = (
        "⚠️ Внутренняя ошибка состояния.\n"
        f"Не найдены данные: {key}.\n"
        "Попробуйте начать шаг заново или вернитесь назад."
    )
    if event is not None:
        if isinstance(event, Message):
            await event.answer(text=text)
        else:
            await event.message.answer(text=text)
    # Мягко выходим из текущего шага
    await dialog_manager.done()


Event = Union[CallbackQuery, Message]


# ---------- internal helpers ----------

def _get_mode(dm: DialogManager) -> str:
    """
    Safely determine current dialog mode ("edit" or "register").
    aiogram-dialog can have start_data == None, so we must guard it.
    """
    # try start_data if present
    sd = getattr(dm, "start_data", None)
    if isinstance(sd, dict) and sd.get("mode"):
        return str(sd.get("mode"))

    # fallback to dialog_data
    dd = getattr(dm, "dialog_data", None) or {}
    mode = dd.get("mode")
    if isinstance(mode, str) and mode:
        return mode

    # default
    return "register"


async def _answer(event: Optional[Event], text: str) -> None:
    if event is None:
        return
    if isinstance(event, CallbackQuery):
        # Prefer answering callback to avoid "loading..." spinner
        try:
            await event.answer(text, show_alert=False)
            return
        except Exception:
            pass
        try:
            await event.message.answer(text)
        except Exception:
            pass
    else:
        try:
            await event.answer(text)
        except Exception:
            pass


# ---------- API used by dialogs ----------

async def raise_keyboard_error(event: Optional[Event], item_type: str) -> None:
    """
    Inform user they should use the keyboard buttons for a particular field.
    """
    await _answer(event, f"Пожалуйста, используйте кнопки для поля: {item_type}.")


async def need_to_display_current_value(
    dialog_manager: DialogManager,
    item_type: str,
    current_value: Any,
) -> bool:
    """
    Some flows show current value in edit mode. Keep it tolerant to different call sites.
    Returns True if something was shown, False otherwise.
    """
    # Just a safe no-op for now; UI already renders current value in window text.
    # We keep this function to maintain compatibility with older code.
    _ = (item_type, current_value)  # keep signature
    _ = _get_mode(dialog_manager)
    return False


async def switch_state(dm: DialogManager, next_states: Dict[str, Optional[Any]]) -> None:
    """
    Switch to the next state depending on mode.
    next_states example: {"edit": None, "register": SomeState}
    If chosen state is None -> just dm.show()
    """
    mode = _get_mode(dm)
    state = next_states.get(mode)

    if state is None:
        # no state change, just re-render
        await dm.show()
        return

    # Normal state switch
    await dm.switch_to(state)


async def go_back_when_edit_mode(dm: DialogManager) -> None:
    """
    Some older flows used this helper to immediately go back in edit mode.
    """
    if _get_mode(dm) == "edit":
        await dm.back()
    else:
        await dm.show()


# Optional helper used by some entry points
async def start_game_creation(dm: DialogManager) -> None:
    """
    Older code may call this to route the user to game creation depending on role.
    Leave it as a harmless no-op that just shows current window, so callers don't crash.
    Real routing logic should happen in the dialog that calls this.
    """
    await dm.show()


# Backward-compat aliases (if older modules import these names)
start_dialog = start_game_creation