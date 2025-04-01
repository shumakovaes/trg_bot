from aiogram.types import CallbackQuery, ContentType, Message
from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.widgets.common import Whenable
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.text import Const, Format, Jinja, List
from aiogram_dialog.widgets.kbd import Button, Row, Column, Start, Select, Cancel, SwitchTo, Group, PrevPage, \
    CurrentPage, NextPage

from bot.db.current_requests import get_user_player, get_user_master
from bot.dialogs.games.games_tools import games_list, games_navigation, generate_check_game
from bot.states.games_states import AllGames, GameInspection

# Choosing games dialog
all_games_dialog = Dialog(
    Window(
        Const("Здесь вы можете просмотреть и отредактировать все созданные вами игры, а также отслеживать статус поданных заявок на игру"),
        Row(
            SwitchTo(Const("Созданные игры"), state=AllGames.checking_player_games, id="player_games"),
            SwitchTo(Const("Поданные заявки"), state=AllGames.checking_master_games, id="master_games"),
        ),
        Cancel(Const("Выйти")),
        state=AllGames.checking_games,
    ),
    Window(
        Const("Чтобы посмотреть про игру подробнее, введите текстом её номер."),
        games_list,

        MessageInput(func=generate_check_game("player"), content_types=[ContentType.TEXT]),

        games_navigation,
        SwitchTo(text=Const("Назад"), state=AllGames.checking_games, id="back_to_checking_games_from_player"),
        getter=get_user_player,
        state=AllGames.checking_player_games,
    ),
    Window(
        Const("Чтобы посмотреть про игру подробнее, введите текстом её номер."),
        games_list,

        MessageInput(func=generate_check_game("master"), content_types=[ContentType.TEXT]),

        games_navigation,
        SwitchTo(text=Const("Назад"), state=AllGames.checking_games, id="back_to_checking_games_from_master"),
        getter=get_user_master,
        state=AllGames.checking_master_games,
    ),
)
