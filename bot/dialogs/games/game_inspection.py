from aiogram.types import CallbackQuery, ContentType, Message
from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.widgets.common import Whenable
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.text import Const, Format, Jinja, List
from aiogram_dialog.widgets.kbd import Button, Row, Column, Start, Select, Cancel, SwitchTo, Group, PrevPage, \
    CurrentPage, NextPage

from bot.db.current_requests import get_user_player, get_user_master
from bot.dialogs.games.games_tools import games_list, games_navigation, generate_check_game, \
    generate_game_description_by_id, get_game_by_id
from bot.dialogs.general_tools import copy_start_data_to_dialog_data
from bot.states.games_states import AllGames, GameInspection

# Registration dialog
game_inspection_dialog = Dialog(
    Window(
        # generate_game_description_by_id(),
        Const("Игра."),
        Cancel(Const("Назад")),
        state=GameInspection.checking_game,
    ),
    # on_start=copy_start_data_to_dialog_data,
)
