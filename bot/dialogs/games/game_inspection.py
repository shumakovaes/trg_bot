import logging

from aiogram.types import CallbackQuery, ContentType, Message
from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.widgets.common import Whenable
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.text import Const, Format, Jinja, List, Multi
from aiogram_dialog.widgets.kbd import Button, Row, Column, Start, Select, Cancel, SwitchTo, Group, PrevPage, \
    CurrentPage, NextPage

from bot.db.current_requests import get_user_player, get_user_master, games
from bot.dialogs.games.games_tools import generate_game_description, get_game_by_id_in_start_data
from bot.states.games_states import AllGames, GameInspection


# Game inspection dialog
game_inspection_dialog = Dialog(
    Window(
        generate_game_description(),

        Cancel(Const("Назад")),

        getter=get_game_by_id_in_start_data,
        state=GameInspection.checking_game,
    ),
)
