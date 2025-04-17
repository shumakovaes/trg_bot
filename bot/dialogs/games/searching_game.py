import logging
from typing import Optional
from magic_filter import F

from aiogram.fsm.state import State
from aiogram.types import CallbackQuery, ContentType, Message
from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.widgets.common import Whenable
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.text import Const, Format, Jinja, List, Multi
from aiogram_dialog.widgets.kbd import Button, Row, Column, Start, Select, Cancel, SwitchTo, Group, PrevPage, \
    CurrentPage, NextPage

from bot.db.current_requests import get_user_player, get_user_master, get_player_games, get_master_games, \
    get_player_archive, get_master_archive, user, games, users
from bot.dialogs.games.games_tools import generate_games_list_title_status, generate_games_navigation, \
    generate_check_game, generate_games_list_title, generate_game_description, get_game_by_id_in_dialog_data
from bot.dialogs.general_tools import start_game_creation
from bot.states.games_states import AllGames, GameInspection, GameCreation, SearchingGame


# ONCLICK
# async def check_game_by_id(message: Message, message_input: MessageInput, dialog_manager: DialogManager):
#     str_index = message.text.strip(" .;'\"")
#     if str_index is None or not str_index.isdigit():
#         await message.answer("Вам необходимо ввести число.")
#         return
#
#     index = int(str_index)
#     games_number = len()
#     if index > games_number or index < 0:
#         await message.answer("Введите число, соответствующее индексу игры (от 1 до {}).".format(games_number))
#
#     dialog_manager.dialog_data["game_id"] = game_id
#     await dialog_manager.switch_to(SearchingGame.checking_specific_game)


async def send_request(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    user_id = "id_000000"
    game_id = await get_game_by_id_in_dialog_data(dialog_manager)

    try:
        current_players = games[game_id]["players"]
        current_master = games[game_id]["master"]
    except KeyError:
        logging.critical("cannot get players for game id {}".format(game_id))
        await callback.answer("Что-то пошло не так, обратитесь в поддержку.")
        await dialog_manager.done()
        return

    if user_id in current_players:
        await callback.answer("Ваша заявка в эту игру уже была принята.")
        return
    if user_id == current_master:
        await callback.answer("Вы являетесь мастером этой игры.")
        return

    try:
        games[game_id]["requests"].add(user_id)
    except KeyError:
        logging.critical("cannot get requests for game by id {}".format(game_id))
        await callback.answer("Что-то пошло не так, обратитесь в поддержку.")
        await dialog_manager.done()
        return

    try:
        user["player"]["games"].add(game_id)
    except KeyError:
        logging.critical("cannot get games for user by id {}".format(user_id))
        await callback.answer("Что-то пошло не так, обратитесь в поддержку.")
        await dialog_manager.done()
        return

    # TODO: send notifications to master


# GETTERS
async def get_master_by_game_id_in_dialog_data(dialog_manager: DialogManager, **kwargs):
    game_id = get_game_by_id_in_dialog_data(dialog_manager)

    try:
        master_id = games[game_id]["master"]
    except KeyError:
        logging.critical("cannot get master_if for game by id {}".format(game_id))
        await dialog_manager.done()
        return

    master = users.get(master_id)
    if master is None:
        logging.critical("cannot get user by id {}".format(master_id))
        await dialog_manager.done()

    master_form = {}
    try:
        master_form = {
            "name": master["general"]["name"],
            "age": master["general"]["age"],
            "city": master["general"]["city"],
            "time_zone": master["general"]["time_zone"],
            "role": master["general"]["role"],
            "format": master["general"]["format"],
            "about_info": master["general"]["about_info"],
            "experience": master["master"]["experience"],
            "experience_provided": master["master"]["experience"] != "",
        }
    except KeyError:
        logging.critical("cannot get master fields for user by id {}".format(master_id))

    return {"master_form": master_form}


# Choosing game dialog
searching_game_dialog = Dialog(
    Window(
        Const("Чтобы посмотреть про игру подробнее, введите текстом её номер."),
        # generate_games_list_title("available_games"),

        # MessageInput(func=check_game_by_id, content_types=[ContentType.TEXT]),

        # generate_games_navigation("available_games"),
        Cancel(text=Const("Выйти")),
        # getter=get_available_games,
        state=SearchingGame.checking_open_games,
    ),
    Window(
        generate_game_description(False),

        SwitchTo(Const("Анкета мастера"), id="master_form", state=SearchingGame.checking_master_form),
        Button(Const("Подать заявку"), id="send_request", on_click=send_request),

        SwitchTo(Const("Назад"), id="back_to_all_games_from_specific_game", state=SearchingGame.checking_open_games),
        getter=get_game_by_id_in_dialog_data,
        state=SearchingGame.checking_specific_game,
    ),
    Window(
        Multi(
            Jinja(
                "<b>Имя</b>: {{name}}\n" +
                "<b>Возраст</b>: {{age}}\n" +
                "<b>Город</b>: {{city}}\n" +
                "<b>Часовой пояс</b>: {{time_zone}}\n" +
                "<b>Роль</b>: {{role}}\n" +
                "<b>Формат игры</b>: {{format}}\n" +
                "<b>Формат игры</b>: {{format}}\n" +
                "<b>О себе</b>: {{about_info}}\n"
            ),
            Jinja(
                "<b>Опыт ведения игр</b>: {{experience}}\n",
                when=F["experience_provided"],
            ),
            sep='\n',
        ),

        SwitchTo(Const("Описание игры"), id="game_description", state=SearchingGame.checking_specific_game),
        Button(Const("Подать заявку"), id="send_request", on_click=send_request),

        SwitchTo(Const("Назад"), id="back_to_all_games_from_master_form", state=SearchingGame.checking_open_games),
        getter=get_master_by_game_id_in_dialog_data,
        state=SearchingGame.checking_master_form,
    ),
)
