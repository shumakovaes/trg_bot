from typing import Any

from aiogram.types import CallbackQuery, ContentType, Message
from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.widgets.common import Whenable
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.text import Const, Format, Jinja, List
from aiogram_dialog.widgets.kbd import Button, Row, Column, Start, Select, Cancel, SwitchTo, Group, PrevPage, \
    CurrentPage, NextPage

from bot.db.current_requests import get_user_player, get_user_master, games, default_game
from bot.dialogs.games.games_tools import generate_game_description, generate_save_message_from_user_no_formatting_game
from bot.dialogs.general_tools import need_to_display_current_value, go_back_when_edit_mode, switch_state, \
    generate_random_id
from bot.states.games_states import AllGames, GameInspection, GameCreation


# Create new game (ONSTART)
async def create_new_game_if_needed(data: dict[str, Any], dialog_manager: DialogManager):
    if dialog_manager.start_data.get("mode") != "register":
        return

    # TODO: this can cause some bugs
    new_game_id = generate_random_id()
    while not games.get(new_game_id) is None:
        new_game_id = generate_random_id()

    games[new_game_id] = default_game


# Saving game settings (ONCLICK)
async def save_title(message: Message, message_input: MessageInput, dialog_manager: DialogManager):

    next_states = {"edit": None, "register": GameCreation.choosing_cost}
    await switch_state(dialog_manager, next_states)


async def delete_current_game(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    return


# Game registration dialog
game_creation_dialog = Dialog(
    # Window(
    #     Const(""),
    #     Button(Const("Использовать "), id="format_both", on_click=save_default_settings),
    #     state=GameCreation.choosing_default,
    # ),
    Window(
        Const("Введите название для вашей игры."),
        # Jinja("\n<b>Текущее значение</b>: {{title}}", when=need_to_display_current_value),

        # MessageInput(func=save_title, content_types=[ContentType.TEXT]),

        Cancel(Const("Назад"), on_click=delete_current_game),
        state=GameCreation.typing_title,
    ),
    Window(
        state=GameCreation.choosing_cost,
    ),
    Window(
        state=GameCreation.typing_cost,
    ),
    Window(
        state=GameCreation.choosing_format,
    ),
    Window(
        state=GameCreation.typing_place,
    ),
    Window(
        state=GameCreation.typing_platform,
    ),
    Window(
        state=GameCreation.typing_time,
    ),
    Window(
        state=GameCreation.choosing_type,
    ),
    Window(
        state=GameCreation.choosing_system,
    ),
    Window(
        state=GameCreation.choosing_edition,
    ),
    Window(
        state=GameCreation.choosing_number_of_players,
    ),
    Window(
        state=GameCreation.choosing_age,
    ),
    Window(
        state=GameCreation.typing_requirements,
    ),
    Window(
        state=GameCreation.typing_description,
    ),
    on_start=create_new_game_if_needed,
)