from aiogram.fsm.state import State
from aiogram.types import CallbackQuery, ContentType, Message
from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.widgets.common import Whenable
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.text import Const, Format, Jinja, List
from aiogram_dialog.widgets.kbd import Button, Row, Column, Start, Select, Cancel, SwitchTo, Group, PrevPage, \
    CurrentPage, NextPage

from bot.db.current_requests import get_user_player, get_user_master, get_player_games, get_master_games, \
    get_player_archive, get_master_archive
from bot.dialogs.games.games_tools import generate_games_list, generate_games_navigation, generate_check_game
from bot.states.games_states import AllGames, GameInspection, GameCreation


def generate_folder_inspection(rights: str, folder: str, getter, state: State, back_state: State, can_create_new_games: bool) -> Window:
    if can_create_new_games:
        folder_inspection = Window(
            Const("Чтобы посмотреть про игру подробнее, введите текстом её номер."),
            generate_games_list(f"{rights}_{folder}"),

            MessageInput(func=generate_check_game(rights, folder), content_types=[ContentType.TEXT]),

            generate_games_navigation(f"{rights}_{folder}"),
            SwitchTo(text=Const("Назад"), state=back_state, id=f"back_to_checking_games_from_{rights}_{folder}"),
            getter=getter,
            state=state,
        )
    else:
        folder_inspection = Window(
            Const("Чтобы посмотреть про игру подробнее, введите текстом её номер."),
            generate_games_list(f"{rights}_{folder}"),

            MessageInput(func=generate_check_game(rights, folder), content_types=[ContentType.TEXT]),
            Start(text=Const("Создать новую игру"), state=GameCreation.typing_title, id="create_game_from_all_games", data={"mode": "register"}),

            generate_games_navigation(f"{rights}_{folder}"),
            SwitchTo(text=Const("Назад"), state=back_state, id=f"back_to_checking_games_from_{rights}_{folder}"),
            getter=getter,
            state=state,
        )


    return folder_inspection


# Choosing game dialog
all_games_dialog = Dialog(
    Window(
        Const("Здесь вы можете просмотреть и отредактировать все созданные вами игры, а также отслеживать статус поданных заявок на игру"),
        Row(
            SwitchTo(Const("Созданные игры"), state=AllGames.checking_master_games, id="player_games"),
            SwitchTo(Const("Поданные заявки"), state=AllGames.checking_player_games, id="master_games"),
        ),
        SwitchTo(Const("Архив"), state=AllGames.checking_archive, id="archive"),
        Cancel(Const("Выйти")),
        state=AllGames.checking_games,
    ),
    Window(
        Const("Здесь хранятся игры, перенесённые в архив."),
        Row(
            SwitchTo(Const("Созданные игры"), state=AllGames.checking_master_archive, id="player_archive"),
            SwitchTo(Const("Поданные заявки"), state=AllGames.checking_player_archive, id="master_archive"),
        ),
        SwitchTo(Const("Назад"), state=AllGames.checking_games, id="back_to_checking_games_from_archive"),
        state=AllGames.checking_archive,
    ),
    generate_folder_inspection("player", "games", get_player_games, AllGames.checking_player_games, AllGames.checking_games, False),
    generate_folder_inspection("master", "games", get_master_games, AllGames.checking_master_games, AllGames.checking_games, True),
    generate_folder_inspection("player", "archive", get_player_archive, AllGames.checking_player_archive, AllGames.checking_archive, False),
    generate_folder_inspection("master", "archive", get_master_archive, AllGames.checking_master_archive, AllGames.checking_archive, False),

)
