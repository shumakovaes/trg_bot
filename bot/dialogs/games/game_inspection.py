import logging
from typing import Any

from aiogram.types import CallbackQuery, ContentType, Message
from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.widgets.common import Whenable
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.text import Const, Format, Jinja, List, Multi
from aiogram_dialog.widgets.kbd import Button, Row, Column, Start, Select, Cancel, SwitchTo, Group, PrevPage, \
    CurrentPage, NextPage

from bot.db.current_requests import get_user_player, get_user_master, games
from bot.dialogs.games.games_tools import generate_game_description, get_game_by_id_in_start_data, \
    get_game_by_id_in_dialog_data
from bot.states.games_states import AllGames, GameInspection


# ON START
async def copy_game_id_and_rights_to_dialog_data(data: dict[str, Any], dialog_manager: DialogManager):
    game_id = dialog_manager.start_data.get("game_id")
    rights = dialog_manager.start_data.get("rights")

    if game_id is None:
        logging.critical("game_id is missing")
        return
    if rights is None:
        logging.critical("rights are missing")
        return

    dialog_manager.dialog_data["game_id"] = game_id
    dialog_manager.dialog_data["rights"] = rights


# Game inspection dialog
game_inspection_dialog = Dialog(
    Window(
        generate_game_description(),

        Cancel(Const("Назад")),

        getter=get_game_by_id_in_dialog_data,
        state=GameInspection.checking_game,
    ),
    on_start=copy_game_id_and_rights_to_dialog_data,
)
